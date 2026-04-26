from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from sge_to_slurm.cli import app

FIXTURES = Path(__file__).parent / "fixtures" / "sge"


@pytest.fixture
def cfg_file(tmp_path):
    p = tmp_path / "c.yaml"
    p.write_text("account:\n  my_project: acct\n", encoding="utf-8")
    return p


def test_cli_convert_writes_default_path(tmp_path, cfg_file):
    runner = CliRunner()
    src = FIXTURES / "basic.sh"
    dst = tmp_path / "basic_slurm.sh"
    assert not dst.exists()
    inp = tmp_path / "basic.sh"
    inp.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "convert",
            str(inp),
            "--config",
            str(cfg_file),
        ],
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    out = tmp_path / "basic_slurm.sh"
    assert out.exists()
    t = out.read_text(encoding="utf-8")
    assert "#SBATCH --job-name=example" in t


def test_cli_refuse_overwrite(tmp_path, cfg_file):
    runner = CliRunner()
    inp = tmp_path / "job.sh"
    inp.write_text(FIXTURES.joinpath("basic.sh").read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "job_slurm.sh"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(app, ["convert", str(inp), "--config", str(cfg_file)])
    assert result.exit_code == 2
    assert "Refusing" in result.stdout or "Refusing" in result.stderr or "overwrite" in result.stderr.lower()


def test_cli_force_overwrite(tmp_path, cfg_file):
    runner = CliRunner()
    inp = tmp_path / "job.sh"
    inp.write_text(FIXTURES.joinpath("basic.sh").read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "job_slurm.sh"
    out.write_text("existing\n", encoding="utf-8")
    result = runner.invoke(app, ["convert", str(inp), "--config", str(cfg_file), "--force"])
    assert result.exit_code == 0
    assert "#SBATCH" in out.read_text(encoding="utf-8")


def test_cli_no_write(tmp_path, cfg_file):
    runner = CliRunner()
    inp = tmp_path / "job.sh"
    inp.write_text(FIXTURES.joinpath("basic.sh").read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "job_slurm.sh"
    result = runner.invoke(app, ["convert", str(inp), "--config", str(cfg_file), "--no-write"])
    assert result.exit_code == 0
    assert not out.exists()
    assert "Dry run" in result.stdout or "dry run" in result.stdout.lower()


def test_main_prepends_convert(tmp_path, cfg_file, monkeypatch):
    """Console entry ``main()`` turns ``sge-to-slurm job.sh`` into ``... convert job.sh``."""
    import sys

    from sge_to_slurm.cli import main

    inp = tmp_path / "job.sh"
    inp.write_text(FIXTURES.joinpath("basic.sh").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["sge-to-slurm", str(inp), "--config", str(cfg_file), "--no-write", "--quiet"],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0


def test_cli_explicit_convert(tmp_path, cfg_file):
    runner = CliRunner()
    inp = tmp_path / "job.sh"
    inp.write_text(FIXTURES.joinpath("basic.sh").read_text(encoding="utf-8"), encoding="utf-8")
    result = runner.invoke(
        app,
        ["convert", str(inp), "--config", str(cfg_file), "--quiet", "--no-write"],
    )
    assert result.exit_code == 0
