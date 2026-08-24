from __future__ import annotations


class SnapshotStoreError(RuntimeError):
    """A stable, non-sensitive failure raised by the local snapshot store."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        self.code = code
        self.detail = detail
        super().__init__(code if detail is None else f"{code}: {detail}")
