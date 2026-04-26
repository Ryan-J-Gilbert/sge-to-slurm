from __future__ import annotations

import os
import tempfile
from pathlib import Path


def default_output_path(input_path: Path) -> Path:
    """``run.sh`` -> ``run_slurm.sh``."""
    return input_path.with_name(f"{input_path.stem}_slurm{input_path.suffix}")


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def ensure_output_writable(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite existing file: {path}. Use --force to overwrite."
        )
