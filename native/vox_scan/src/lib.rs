//! Parallel directory scanner for VoxPlayer library indexing.
//!
//! C ABI for Python ctypes:
//! - [`vox_scan_dir`] — newline-separated absolute paths (legacy)
//! - [`vox_scan_dir_meta`] — TSV lines ``path\\tsize\\tmtime_ns`` (Phase 6)
//! - [`vox_scan_quick_ids`] — parallel blake3 quick ids for a path list
//! - [`vox_scan_free`] / [`vox_scan_version`]

use blake3::Hasher;
use rayon::prelude::*;
use std::ffi::{CStr, CString};
use std::fs::File;
use std::io::Read;
use std::os::raw::c_char;
use std::path::Path;
use std::sync::Mutex;
use walkdir::WalkDir;

const QUICK_HASH_BYTES: usize = 65536;

fn empty_string() -> *mut c_char {
    CString::new("").unwrap().into_raw()
}

fn parse_exts(exts_csv: *const c_char) -> Vec<String> {
    if exts_csv.is_null() {
        return Vec::new();
    }
    unsafe { CStr::from_ptr(exts_csv) }
        .to_string_lossy()
        .split(',')
        .map(|s| s.trim().to_ascii_lowercase())
        .filter(|s| !s.is_empty())
        .collect()
}

fn ext_ok(path: &Path, exts: &[String]) -> bool {
    if exts.is_empty() {
        return true;
    }
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .map(|e| format!(".{}", e.to_ascii_lowercase()))
        .unwrap_or_default();
    exts.iter().any(|x| x == &ext)
}

fn collect_files(root_path: &Path, exts: &[String]) -> Vec<std::path::PathBuf> {
    let entries: Vec<_> = WalkDir::new(root_path)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .map(|e| e.into_path())
        .collect();
    entries
        .into_par_iter()
        .filter(|path| ext_ok(path, exts))
        .collect()
}

/// Scan `root` recursively for files whose extension is in `exts_csv`.
/// Returns a newly allocated C string of newline-separated absolute paths.
/// Caller must free with [`vox_scan_free`].
#[no_mangle]
pub extern "C" fn vox_scan_dir(root: *const c_char, exts_csv: *const c_char) -> *mut c_char {
    if root.is_null() {
        return empty_string();
    }
    let root_str = unsafe { CStr::from_ptr(root) }.to_string_lossy();
    let root_path = Path::new(root_str.as_ref());
    if !root_path.is_dir() {
        return empty_string();
    }
    let exts = parse_exts(exts_csv);
    let mut paths: Vec<String> = collect_files(root_path, &exts)
        .into_iter()
        .filter_map(|p| p.to_str().map(|s| s.to_string()))
        .collect();
    paths.sort();
    match CString::new(paths.join("\n")) {
        Ok(c) => c.into_raw(),
        Err(_) => empty_string(),
    }
}

/// Like [`vox_scan_dir`], but each line is ``path\\tsize\\tmtime_ns``.
/// Stats run in parallel so the Python shell can skip per-file ``os.stat``.
#[no_mangle]
pub extern "C" fn vox_scan_dir_meta(root: *const c_char, exts_csv: *const c_char) -> *mut c_char {
    if root.is_null() {
        return empty_string();
    }
    let root_str = unsafe { CStr::from_ptr(root) }.to_string_lossy();
    let root_path = Path::new(root_str.as_ref());
    if !root_path.is_dir() {
        return empty_string();
    }
    let exts = parse_exts(exts_csv);
    let files = collect_files(root_path, &exts);
    let lines: Mutex<Vec<String>> = Mutex::new(Vec::with_capacity(files.len()));

    files.par_iter().for_each(|path| {
        let meta = match std::fs::metadata(path) {
            Ok(m) => m,
            Err(_) => return,
        };
        let size = meta.len();
        let mtime_ns = meta
            .modified()
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_nanos() as u64)
            .unwrap_or(0);
        let Some(s) = path.to_str() else {
            return;
        };
        if let Ok(mut guard) = lines.lock() {
            guard.push(format!("{s}\t{size}\t{mtime_ns}"));
        }
    });

    let mut out = lines.into_inner().unwrap_or_default();
    out.sort();
    match CString::new(out.join("\n")) {
        Ok(c) => c.into_raw(),
        Err(_) => empty_string(),
    }
}

fn quick_id_for(path: &Path) -> Option<String> {
    let meta = std::fs::metadata(path).ok()?;
    let size = meta.len();
    let mtime_ns = meta
        .modified()
        .ok()
        .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
        .map(|d| d.as_nanos() as u64)
        .unwrap_or(0);
    let mut hasher = Hasher::new();
    hasher.update(&size.to_le_bytes());
    hasher.update(&mtime_ns.to_le_bytes());
    if let Ok(mut f) = File::open(path) {
        let mut buf = vec![0u8; QUICK_HASH_BYTES];
        if let Ok(n) = f.read(&mut buf) {
            hasher.update(&buf[..n]);
        }
    }
    let hex = hasher.finalize().to_hex();
    let s = path.to_str()?;
    Some(format!("{s}\t{hex}"))
}

/// Parallel quick content ids for newline-separated absolute paths.
/// Each output line: ``path\\tblake3_hex`` (size+mtime+first 64KiB).
/// Caller frees with [`vox_scan_free`].
#[no_mangle]
pub extern "C" fn vox_scan_quick_ids(paths_nl: *const c_char) -> *mut c_char {
    if paths_nl.is_null() {
        return empty_string();
    }
    let raw = unsafe { CStr::from_ptr(paths_nl) }.to_string_lossy();
    let paths: Vec<&str> = raw
        .split('\n')
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect();
    let lines: Mutex<Vec<String>> = Mutex::new(Vec::with_capacity(paths.len()));
    paths.par_iter().for_each(|p| {
        if let Some(line) = quick_id_for(Path::new(p)) {
            if let Ok(mut guard) = lines.lock() {
                guard.push(line);
            }
        }
    });
    let mut out = lines.into_inner().unwrap_or_default();
    out.sort();
    match CString::new(out.join("\n")) {
        Ok(c) => c.into_raw(),
        Err(_) => empty_string(),
    }
}

/// Free a string returned by scan helpers.
#[no_mangle]
pub extern "C" fn vox_scan_free(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

/// NUL-terminated version string (static; do not free).
#[no_mangle]
pub extern "C" fn vox_scan_version() -> *const c_char {
    concat!(env!("CARGO_PKG_VERSION"), "\0").as_ptr() as *const c_char
}
