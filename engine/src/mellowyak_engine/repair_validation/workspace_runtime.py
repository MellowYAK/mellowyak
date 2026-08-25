from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceProcessResult:
    result: str
    return_code: int | None
    output: str
    error_code: str | None


class WorkspaceRuntime:
    """Bounded no-shell runtime for explicitly approved executable/argv pairs."""

    MAX_OUTPUT = 256 * 1024

    @staticmethod
    def sanitized_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
        allowed = {"PATH", "LANG", "LC_ALL", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT"}
        environment = {key: value for key, value in os.environ.items() if key in allowed}
        environment.update(
            {
                "MELLOWYAK_WORKSPACE_RUNTIME": "1",
                "MELLOWYAK_NETWORK_POLICY": "NO_EXTERNAL_EGRESS",
            }
        )
        if extra:
            environment.update({str(key): str(value) for key, value in extra.items()})
        return environment

    def run(
        self,
        executable: str,
        argv: list[str],
        cwd: Path,
        *,
        timeout_seconds: int = 900,
    ) -> WorkspaceProcessResult:
        command = [executable, *argv]
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=self.sanitized_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=False,
            shell=False,
            start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=max(1, min(timeout_seconds, 900)))
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            return WorkspaceProcessResult(
                "ERROR",
                process.returncode,
                output[: self.MAX_OUTPUT].decode(errors="replace"),
                "VALIDATION_TIMEOUT",
            )
        return WorkspaceProcessResult(
            "PASS" if process.returncode == 0 else "FAIL",
            process.returncode,
            output[: self.MAX_OUTPUT].decode(errors="replace"),
            None,
        )
