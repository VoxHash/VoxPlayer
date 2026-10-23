//! Lightweight media-folder scanner (Zig) for VoxPlayer.
//! Same C ABI as Rust ``vox_scan`` so Python ctypes can swap implementations.
//! Uses libc/POSIX so the shared object stays small (no Zig Io runtime).

const std = @import("std");
const c = std.c;

const DIR = c.DIR;

fn emptyString() ?[*:0]u8 {
    const buf = c.malloc(1) orelse return null;
    const p: [*]u8 = @ptrCast(buf);
    p[0] = 0;
    return @ptrCast(p);
}

fn toLowerInPlace(buf: []u8) void {
    for (buf) |*ch| ch.* = std.ascii.toLower(ch.*);
}

fn parseExts(csv: ?[*:0]const u8, allocator: std.mem.Allocator) ![][]const u8 {
    if (csv == null) return &[_][]const u8{};
    const raw = std.mem.span(csv.?);
    if (raw.len == 0) return &[_][]const u8{};

    var list: std.ArrayListUnmanaged([]const u8) = .empty;
    errdefer {
        for (list.items) |e| allocator.free(e);
        list.deinit(allocator);
    }

    var it = std.mem.splitScalar(u8, raw, ',');
    while (it.next()) |part| {
        const s = std.mem.trim(u8, part, " \t");
        if (s.len == 0) continue;
        const owned = try allocator.dupe(u8, s);
        toLowerInPlace(owned);
        try list.append(allocator, owned);
    }
    return try list.toOwnedSlice(allocator);
}

fn extMatches(path: []const u8, exts: []const []const u8) bool {
    if (exts.len == 0) return true;
    const dot = std.mem.lastIndexOfScalar(u8, path, '.') orelse return false;
    var buf: [64]u8 = undefined;
    const ext_raw = path[dot..];
    if (ext_raw.len == 0 or ext_raw.len >= buf.len) return false;
    @memcpy(buf[0..ext_raw.len], ext_raw);
    toLowerInPlace(buf[0..ext_raw.len]);
    const ext = buf[0..ext_raw.len];
    for (exts) |e| {
        if (std.mem.eql(u8, ext, e)) return true;
    }
    return false;
}

fn isDotOrDotDot(name: []const u8) bool {
    return std.mem.eql(u8, name, ".") or std.mem.eql(u8, name, "..");
}

fn dupeZ(allocator: std.mem.Allocator, s: []const u8) ![:0]u8 {
    const buf = try allocator.alloc(u8, s.len + 1);
    @memcpy(buf[0..s.len], s);
    buf[s.len] = 0;
    return buf[0..s.len :0];
}

fn joinPath(allocator: std.mem.Allocator, a: []const u8, b: []const u8) ![]u8 {
    if (a.len == 0) return allocator.dupe(u8, b);
    if (a[a.len - 1] == '/') {
        const out = try allocator.alloc(u8, a.len + b.len);
        @memcpy(out[0..a.len], a);
        @memcpy(out[a.len..], b);
        return out;
    }
    const out = try allocator.alloc(u8, a.len + 1 + b.len);
    @memcpy(out[0..a.len], a);
    out[a.len] = '/';
    @memcpy(out[a.len + 1 ..], b);
    return out;
}

fn walkCollect(
    allocator: std.mem.Allocator,
    abs_dir: []const u8,
    exts: []const []const u8,
    out: *std.ArrayListUnmanaged([]const u8),
) !void {
    const dir_z = try dupeZ(allocator, abs_dir);
    defer allocator.free(dir_z);

    const dp: *DIR = c.opendir(dir_z.ptr) orelse return;
    defer _ = c.closedir(dp);

    while (true) {
        const ent = c.readdir(dp) orelse break;
        const name = std.mem.sliceTo(&ent.*.name, 0);
        if (name.len == 0 or isDotOrDotDot(name) or name[0] == '.') continue;

        const child = try joinPath(allocator, abs_dir, name);
        const dtype = ent.*.type;

        // Prefer d_type when the filesystem provides it; otherwise fall back to stat.
        // Prefer d_type; on DT_UNKNOWN probe with opendir (no libc Stat binding needed).
        const kind: enum { dir, file, other } = blk: {
            if (dtype == c.DT.DIR) break :blk .dir;
            if (dtype == c.DT.REG) break :blk .file;
            if (dtype != c.DT.UNKNOWN and dtype != 0) break :blk .other;
            const child_z = try dupeZ(allocator, child);
            defer allocator.free(child_z);
            if (c.opendir(child_z.ptr)) |probe| {
                _ = c.closedir(probe);
                break :blk .dir;
            }
            break :blk .file;
        };

        switch (kind) {
            .dir => {
                defer allocator.free(child);
                try walkCollect(allocator, child, exts, out);
            },
            .file => {
                if (extMatches(child, exts)) {
                    try out.append(allocator, child);
                } else {
                    allocator.free(child);
                }
            },
            .other => allocator.free(child),
        }
    }
}

/// Scan ``root`` recursively for files whose extension is in ``exts_csv``.
export fn vox_scan_dir(root: ?[*:0]const u8, exts_csv: ?[*:0]const u8) callconv(.c) ?[*:0]u8 {
    if (root == null) return emptyString();
    const root_slice = std.mem.span(root.?);
    if (root_slice.len == 0) return emptyString();

    var arena = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer arena.deinit();
    const allocator = arena.allocator();

    const exts = parseExts(exts_csv, allocator) catch return emptyString();

    // Resolve to absolute path via libc realpath when possible.
    var resolved_buf: [4096]u8 = undefined;
    const abs_root: []const u8 = blk: {
        const rp = c.realpath(root.?, &resolved_buf);
        if (rp) |p| break :blk std.mem.span(p);
        break :blk root_slice;
    };

    var paths: std.ArrayListUnmanaged([]const u8) = .empty;
    walkCollect(allocator, abs_root, exts, &paths) catch return emptyString();

    std.mem.sort([]const u8, paths.items, {}, struct {
        fn less(_: void, a: []const u8, b: []const u8) bool {
            return std.mem.order(u8, a, b) == .lt;
        }
    }.less);

    if (paths.items.len == 0) return emptyString();

    var total: usize = 0;
    for (paths.items) |p| total += p.len + 1;

    const buf = c.malloc(total) orelse return emptyString();
    const out: [*]u8 = @ptrCast(buf);
    var off: usize = 0;
    for (paths.items, 0..) |p, i| {
        @memcpy(out[off .. off + p.len], p);
        off += p.len;
        if (i + 1 < paths.items.len) {
            out[off] = '\n';
            off += 1;
        }
    }
    out[off] = 0;
    return @ptrCast(out);
}

export fn vox_scan_free(ptr: ?[*:0]u8) callconv(.c) void {
    if (ptr) |p| c.free(p);
}

export fn vox_scan_zig_version() callconv(.c) [*:0]const u8 {
    return "0.1.0-zig";
}
