const std = @import("std");

/// Alternate Phase-3 scanner: same C ABI as Rust ``vox_scan``, smaller shared object.
pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    const mod = b.createModule(.{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
        .link_libc = true,
    });

    const lib = b.addLibrary(.{
        .name = "vox_scan_zig",
        .root_module = mod,
        .linkage = .dynamic,
    });

    b.installArtifact(lib);
}
