from __future__ import annotations

import pytest


@pytest.fixture
def sample_config_path(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        """
account:
  my_project: slurm_acct
partitions:
  short: shortp
parallel_environments:
  mpi_28_tasks_per_node:
    type: mpi_slots
    tasks_per_node: 28
""".strip(),
        encoding="utf-8",
    )
    return p
