"""Resolve immutable source digests against current bytes or Git history."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final

_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^(?:sha256:)?([0-9a-f]{64})$")


@dataclass(frozen=True)
class SealedSourceResolution:
    """Provenance for one immutable manifest row."""

    recoverable: bool
    provenance: str
    commit: str | None = None


def resolve_sealed_source_digest(
    repo_root: Path,
    relative_path: str,
    expected_digest: object,
) -> SealedSourceResolution:
    """Accept current bytes or the exact historical blob sealed originally."""

    relative = Path(relative_path)
    digest_match = _SHA256_RE.fullmatch(str(expected_digest))
    if relative.is_absolute() or ".." in relative.parts or digest_match is None:
        return SealedSourceResolution(False, "invalid_manifest_row")
    expected = digest_match.group(1)
    current = repo_root / relative
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == expected:
        return SealedSourceResolution(True, "current_worktree")
    history = subprocess.run(
        ["git", "log", "--all", "--format=%H", "--", relative.as_posix()],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        return SealedSourceResolution(False, "git_history_unavailable")
    for commit in history.stdout.splitlines():
        blob = subprocess.run(
            ["git", "show", f"{commit}:{relative.as_posix()}"],
            cwd=repo_root,
            check=False,
            capture_output=True,
        )
        if blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == expected:
            return SealedSourceResolution(True, "git_history", commit)
    return SealedSourceResolution(False, "sealed_blob_not_found")


__all__ = ["SealedSourceResolution", "resolve_sealed_source_digest"]
