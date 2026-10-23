//! Parallel directory scanner for VoxPlayer library indexing.
//!
//! Exposes a C ABI so Python can call it via ctypes. Extension allow-list is a
//! comma-separated list (e.g. ".mp3,.m4a,.mp4"). Matching paths are returned as
//! a single newline-separated C string. Caller must free with [`vox_scan_free`].

use rayon::prelude::*;
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::path::Path;
use std::sync::Mutex;
use walkdir::WalkDir;

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

    let exts: Vec<String> = if exts_csv.is_null() {
        Vec::new()
    } else {
        unsafe { CStr::from_ptr(exts_csv) }
            .to_string_lossy()
            .split(',')
            .map(|s| s.trim().to_ascii_lowercase())
            .filter(|s| !s.is_empty())
            .collect()
    };

    let found: Mutex<Vec<String>> = Mutex::new(Vec::new());

    let entries: Vec<_> = WalkDir::new(root_path)
        .follow_links(false)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .collect();

    entries.par_iter().for_each(|entry| {
        let path = entry.path();
        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| format!(".{}", e.to_ascii_lowercase()))
            .unwrap_or_default();
        if exts.is_empty() || exts.iter().any(|x| x == &ext) {
            if let Some(s) = path.to_str() {
                if let Ok(mut guard) = found.lock() {
                    guard.push(s.to_string());
                }
            }
        }
    });

    let mut paths = found.into_inner().unwrap_or_default();
    paths.sort();
    match CString::new(paths.join("\n")) {
        Ok(c) => c.into_raw(),
        Err(_) => empty_string(),
    }
}

/// Free a string returned by [`vox_scan_dir`].
#[no_mangle]
pub extern "C" fn vox_scan_free(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        drop(CString::from_raw(ptr));
    }
}

fn empty_string() -> *mut c_char {
    CString::new("").unwrap().into_raw()
}
