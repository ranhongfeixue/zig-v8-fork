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

test "PartitionAlloc memory reclaimer bridge reports allocator shim support" {
    const enabled = c.v8__PartitionAlloc__EnableMemoryReclaimer();
    if (!@import("default_exports").use_allocator_shim) {
        try std.testing.expect(!enabled);
    }
    c.v8__PartitionAlloc__ReclaimFast();
    c.v8__PartitionAlloc__ReclaimAll();
}
