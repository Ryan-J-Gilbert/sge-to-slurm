from __future__ import annotations

from pathlib import Path

import pytest

from sge_to_slurm.config import load_config
from sge_to_slurm.converter import convert_file, convert_script
from sge_to_slurm.models import LineKind, LineStatus


FIXTURES = Path(__file__).parent / "fixtures" / "sge"


def test_convert_basic_golden(sample_config_path, tmp_path):
    cfg = load_config(sample_config_path)
    src = FIXTURES / "basic.sh"
    res = convert_file(src, cfg)
    shebang_reports = [r for r in res.lines if r.kind == LineKind.SHEBANG]
    assert len(shebang_reports) == 1
    assert shebang_reports[0].status == LineStatus.WARNING  # bash -l
    text = res.output_text
    assert "#SBATCH --job-name=example" in text
    assert "#SBATCH --account=slurm_acct" in text
    assert "#SBATCH --time=12:00:00" in text
    assert "#SBATCH --output=out.log" in text
    assert "#SBATCH --error=out.log" in text
    assert "#SBATCH --mail-type=" in text
    assert "#SBATCH --mail-user=user@example.com" in text
    assert "${SLURM_JOB_ID}" in text
    assert "${SLURM_ARRAY_TASK_ID}" in text
    assert "#$ -N" not in text


def test_convert_mpi_pe(sample_config_path):
    cfg = load_config(sample_config_path)
    src = FIXTURES / "with_mpi.sh"
    res = convert_file(src, cfg)
    assert "#SBATCH --partition=shortp" in res.output_text
    assert "#SBATCH --ntasks=224" in res.output_text
    assert "#SBATCH --ntasks-per-node=28" in res.output_text
    assert "SLURM_CPUS_PER_TASK" in res.output_text or "${SLURM_CPUS_PER_TASK}" in res.output_text


def test_unmapped_project_warning(sample_config_path):
    cfg = load_config(sample_config_path)
    script = """#!/bin/bash
#$ -P other_project
"""
    res = convert_script(script, cfg)
    assert "TODO: map SGE -P other_project" in res.output_text
    warns = [r for r in res.lines if r.status == LineStatus.WARNING]
    assert any("account mapping" in (r.message or "") for r in warns)


def test_inline_qsub_marked_error():
    cfg = load_config(None)
    script = """#!/bin/bash
qsub other.sh
"""
    res = convert_script(script, cfg)
    body_reports = [r for r in res.lines if r.kind == LineKind.BODY]
    assert any(r.status == LineStatus.ERROR for r in body_reports)


def test_heredoc_warning():
    cfg = load_config(None)
    script = """#!/bin/bash
cat <<EOF
$JOB_ID
EOF
"""
    res = convert_script(script, cfg)
    br = [r for r in res.lines if r.kind == LineKind.BODY]
    assert any("heredoc" in (r.message or "").lower() for r in br)


def test_load_toml_config(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        """
[account]
foo = "bar"
""".strip(),
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.account_map["foo"] == "bar"
