//! Metadata + thumbnail worker pool for VoxPlayer.
//!
//! Python queues jobs via ctypes; workers run ffprobe / ffmpeg off the UI thread
//! and invoke a C callback with the result (JSON tags or JPEG cache path).

use crossbeam_channel::{unbounded, Receiver, Sender};
use sha2::{Digest, Sha256};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_int, c_void};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::Duration;

/// Job kinds (must match Python).
pub const VOX_META_KIND_TAGS: c_int = 0;
pub const VOX_META_KIND_THUMB: c_int = 1;

/// `extern "C" fn(user_data, job_id, kind, path, result, status)`
/// `status == 0` means success; `result` is JSON (tags) or a JPEG path (thumb).
pub type VoxMetaCallback = Option<
    extern "C" fn(
        user_data: *mut c_void,
        job_id: u64,
        kind: c_int,
        path: *const c_char,
        result: *const c_char,
        status: c_int,
    ),
>;

struct Job {
    id: u64,
    kind: c_int,
    path: String,
    cache_dir: String,
    seek: f64,
    callback: VoxMetaCallback,
    user_data: usize,
}

struct PoolInner {
    tx: Sender<Job>,
    stop: Arc<AtomicBool>,
    handles: Vec<JoinHandle<()>>,
    next_id: AtomicU64,
}

/// Opaque pool handle for the C ABI.
pub struct VoxMetaPool {
    inner: PoolInner,
}

fn cache_key(path: &str) -> String {
    let mut hasher = Sha256::new();
    match std::fs::metadata(path) {
        Ok(meta) => {
            let mtime = meta
                .modified()
                .ok()
                .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            hasher.update(format!("{path}|{mtime}|{}", meta.len()).as_bytes());
        }
        Err(_) => hasher.update(path.as_bytes()),
    }
    hex::encode(&hasher.finalize()[..20])
}

fn run_ffprobe_tags(path: &str) -> Result<String, String> {
    let output = Command::new("ffprobe")
        .args([
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            path,
        ])
        .output()
        .map_err(|e| format!("ffprobe spawn: {e}"))?;
    if !output.status.success() {
        return Err(format!("ffprobe exit {}", output.status));
    }
    let data: serde_json::Value =
        serde_json::from_slice(&output.stdout).map_err(|e| format!("ffprobe json: {e}"))?;

    let mut title = String::new();
    let mut artist = String::new();
    let mut album = String::new();
    let mut year = String::new();
    let mut genre = String::new();
    let mut duration = 0.0_f64;

    if let Some(fmt) = data.get("format") {
        if let Some(d) = fmt.get("duration").and_then(|v| v.as_str()) {
            duration = d.parse().unwrap_or(0.0);
        } else if let Some(d) = fmt.get("duration").and_then(|v| v.as_f64()) {
            duration = d;
        }
        if let Some(tags) = fmt.get("tags").and_then(|t| t.as_object()) {
            for (k, v) in tags {
                let key = k.to_ascii_lowercase();
                let val = v.as_str().unwrap_or("").to_string();
                if val.is_empty() {
                    continue;
                }
                match key.as_str() {
                    "title" | "track" if title.is_empty() => title = val,
                    "artist" | "album_artist" | "albumartist" if artist.is_empty() => artist = val,
                    "album" if album.is_empty() => album = val,
                    "date" | "year" if year.is_empty() => {
                        year = val.chars().take(4).collect();
                    }
                    "genre" if genre.is_empty() => genre = val,
                    _ => {}
                }
            }
        }
    }

    if let Some(streams) = data.get("streams").and_then(|s| s.as_array()) {
        for stream in streams {
            if let Some(tags) = stream.get("tags").and_then(|t| t.as_object()) {
                for (k, v) in tags {
                    let key = k.to_ascii_lowercase();
                    let val = v.as_str().unwrap_or("").to_string();
                    if val.is_empty() {
                        continue;
                    }
                    match key.as_str() {
                        "title" if title.is_empty() => title = val,
                        "artist" if artist.is_empty() => artist = val,
                        "album" if album.is_empty() => album = val,
                        "date" | "year" if year.is_empty() => {
                            year = val.chars().take(4).collect();
                        }
                        "genre" if genre.is_empty() => genre = val,
                        _ => {}
                    }
                }
            }
        }
    }

    let payload = serde_json::json!({
        "title": title,
        "artist": artist,
        "album": album,
        "year": year,
        "genre": genre,
        "duration": duration,
        "path": path,
        "source": if title.is_empty() && artist.is_empty() { "probe" } else { "tags" },
    });
    Ok(payload.to_string())
}

fn probe_duration(path: &str) -> f64 {
    let output = Command::new("ffprobe")
        .args([
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ])
        .output();
    match output {
        Ok(o) if o.status.success() => {
            String::from_utf8_lossy(&o.stdout).trim().parse().unwrap_or(0.0)
        }
        _ => 0.0,
    }
}

fn is_video_ext(path: &str) -> bool {
    matches!(
        Path::new(path)
            .extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_ascii_lowercase()
            .as_str(),
        "mp4" | "mkv" | "avi" | "mov" | "wmv" | "flv" | "webm" | "m4v" | "mpg" | "mpeg" | "ts"
            | "m2ts"
    )
}

fn ffmpeg_frame(path: &str, out: &Path, seek: f64) -> bool {
    let status = Command::new("ffmpeg")
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            &format!("{:.3}", seek.max(0.0)),
            "-i",
            path,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            "scale=480:-2",
            "-y",
            out.to_str().unwrap_or(""),
        ])
        .status();
    matches!(status, Ok(s) if s.success())
        && out.is_file()
        && std::fs::metadata(out).map(|m| m.len() > 0).unwrap_or(false)
}

fn ffmpeg_cover(path: &str, out: &Path) -> bool {
    let status = Command::new("ffmpeg")
        .args([
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            path,
            "-an",
            "-vcodec",
            "mjpeg",
            "-frames:v",
            "1",
            "-y",
            out.to_str().unwrap_or(""),
        ])
        .status();
    matches!(status, Ok(s) if s.success())
        && out.is_file()
        && std::fs::metadata(out).map(|m| m.len() > 0).unwrap_or(false)
}

fn run_thumbnail(path: &str, cache_dir: &str, preferred_seek: f64) -> Result<String, String> {
    let dir = PathBuf::from(cache_dir);
    std::fs::create_dir_all(&dir).map_err(|e| format!("cache dir: {e}"))?;
    let out = dir.join(format!("{}.jpg", cache_key(path)));
    if out.is_file() && std::fs::metadata(&out).map(|m| m.len() > 1200).unwrap_or(false) {
        return Ok(out.to_string_lossy().into_owned());
    }

    let duration = probe_duration(path);
    let mut seeks = vec![preferred_seek, 1.0, 0.5, 0.0];
    if duration > 5.0 {
        seeks.extend([
            duration * 0.10,
            duration * 0.25,
            duration * 0.40,
            duration * 0.55,
        ]);
    }

    if is_video_ext(path) {
        for mut s in seeks {
            if duration > 0.0 {
                s = s.clamp(0.0, (duration - 0.25).max(0.0));
            }
            if ffmpeg_frame(path, &out, s) {
                return Ok(out.to_string_lossy().into_owned());
            }
            let _ = std::fs::remove_file(&out);
        }
        return Err("ffmpeg frame failed".into());
    }

    if ffmpeg_cover(path, &out) || ffmpeg_frame(path, &out, preferred_seek.max(0.0)) {
        return Ok(out.to_string_lossy().into_owned());
    }
    Err("cover extract failed".into())
}

fn invoke(job: &Job, result: Result<String, String>) {
    let Some(cb) = job.callback else {
        return;
    };
    let path_c = CString::new(job.path.as_str()).unwrap_or_default();
    match result {
        Ok(s) => {
            let res_c = CString::new(s).unwrap_or_default();
            cb(
                job.user_data as *mut c_void,
                job.id,
                job.kind,
                path_c.as_ptr(),
                res_c.as_ptr(),
                0,
            );
        }
        Err(e) => {
            let res_c = CString::new(e).unwrap_or_default();
            cb(
                job.user_data as *mut c_void,
                job.id,
                job.kind,
                path_c.as_ptr(),
                res_c.as_ptr(),
                1,
            );
        }
    }
}

fn worker_loop(rx: Receiver<Job>, stop: Arc<AtomicBool>) {
    while !stop.load(Ordering::Relaxed) {
        match rx.recv_timeout(Duration::from_millis(200)) {
            Ok(job) => {
                if stop.load(Ordering::Relaxed) {
                    break;
                }
                let result = match job.kind {
                    VOX_META_KIND_TAGS => run_ffprobe_tags(&job.path),
                    VOX_META_KIND_THUMB => run_thumbnail(&job.path, &job.cache_dir, job.seek),
                    _ => Err(format!("unknown kind {}", job.kind)),
                };
                invoke(&job, result);
            }
            Err(crossbeam_channel::RecvTimeoutError::Timeout) => continue,
            Err(crossbeam_channel::RecvTimeoutError::Disconnected) => break,
        }
    }
}

/// Create a worker pool with `n_workers` threads (clamped 1..=32; 0 → CPU count).
#[no_mangle]
pub extern "C" fn vox_meta_pool_create(n_workers: u32) -> *mut VoxMetaPool {
    let n = if n_workers == 0 {
        thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(4)
            .clamp(1, 32)
    } else {
        (n_workers as usize).clamp(1, 32)
    };

    let (tx, rx) = unbounded::<Job>();
    let stop = Arc::new(AtomicBool::new(false));
    let mut handles = Vec::with_capacity(n);
    for _ in 0..n {
        let rx_i = rx.clone();
        let stop_i = Arc::clone(&stop);
        handles.push(thread::spawn(move || worker_loop(rx_i, stop_i)));
    }

    let pool = VoxMetaPool {
        inner: PoolInner {
            tx,
            stop,
            handles,
            next_id: AtomicU64::new(1),
        },
    };
    Box::into_raw(Box::new(pool))
}

/// Shut down workers and free the pool.
#[no_mangle]
pub extern "C" fn vox_meta_pool_destroy(pool: *mut VoxMetaPool) {
    if pool.is_null() {
        return;
    }
    let pool = unsafe { Box::from_raw(pool) };
    pool.inner.stop.store(true, Ordering::SeqCst);
    drop(pool.inner.tx);
    for h in pool.inner.handles {
        let _ = h.join();
    }
}

/// Queue a tags (0) or thumbnail (1) job. Returns the assigned job id, or 0 on failure.
#[no_mangle]
pub extern "C" fn vox_meta_submit(
    pool: *mut VoxMetaPool,
    kind: c_int,
    path: *const c_char,
    cache_dir: *const c_char,
    seek: c_double,
    callback: VoxMetaCallback,
    user_data: *mut c_void,
) -> u64 {
    if pool.is_null() || path.is_null() {
        return 0;
    }
    let pool = unsafe { &*pool };
    let path_str = unsafe { CStr::from_ptr(path) }.to_string_lossy().into_owned();
    if path_str.is_empty() {
        return 0;
    }
    let cache = if cache_dir.is_null() {
        String::new()
    } else {
        unsafe { CStr::from_ptr(cache_dir) }
            .to_string_lossy()
            .into_owned()
    };
    let id = pool.inner.next_id.fetch_add(1, Ordering::Relaxed);
    let job = Job {
        id,
        kind,
        path: path_str,
        cache_dir: cache,
        seek,
        callback,
        user_data: user_data as usize,
    };
    match pool.inner.tx.send(job) {
        Ok(()) => id,
        Err(_) => 0,
    }
}

/// Library version string (static).
#[no_mangle]
pub extern "C" fn vox_meta_version() -> *const c_char {
    static VER: &[u8] = b"0.1.0\0";
    VER.as_ptr() as *const c_char
}
