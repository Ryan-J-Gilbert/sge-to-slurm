from __future__ import annotations

from pathlib import Path

from sge_to_slurm.io_util import default_output_path


def test_default_output_path():
    p = Path("/tmp/foo/bar.sh")
    assert default_output_path(p) == Path("/tmp/foo/bar_slurm.sh")
