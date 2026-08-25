# Apply and Rollback Safety

Apply is unavailable until a candidate is validated for exact workspace bytes. Preparation verifies the canonical project root, complete source snapshot identity, per-path hashes, directory safety, permissions, symlink boundaries, candidate state, and absence of another active transaction.

Immediately before writing, MellowYak creates and pins a fresh Safety Snapshot. A durable journal precedes all operations. Additions and modifications use same-filesystem temporary files, content fsync where supported, atomic replacement, supported mode preservation, and directory fsync where supported. Deletions run last. Each path is verified after writing.

Fresh live-project checks follow Apply. Failure begins automatic transaction rollback from that exact Safety Snapshot. Rollback restores affected paths only and verifies byte identity. It is not a general historical restore.

Platform filesystems differ. A locked file or unsupported path stops the operation. If MellowYak cannot prove restoration, it stops writes, marks recovery required, raises a critical local alert, and creates a redacted Recovery Bundle.
