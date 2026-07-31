const std = @import("std");

pub const c = @import("binding");

/// Enables C to allocate using the given Zig allocator.
pub export fn zigAlloc(self: *anyopaque, bytes: usize) callconv(.c) ?[*]u8 {
    const allocator: *std.mem.Allocator = @ptrCast(@alignCast(self));
    const allocated_bytes = allocator.alloc(u8, bytes) catch return null;
    return allocated_bytes.ptr;
}

comptime {
    if (@import("default_exports").inspector_subtype) {
        _ = @import("inspector_subtypes.zig");
    }
}
