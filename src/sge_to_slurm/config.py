from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib
import yaml


@dataclass
class PeRule:
    """How to map ``-pe <name> <slots>`` to Slurm directives."""

    type: str = "openmp"  # openmp | mpi_slots
    tasks_per_node: int | None = None  # for mpi_slots: slots // tasks_per_node -> nodes

    def __post_init__(self) -> None:
        if self.type not in ("openmp", "mpi_slots"):
            raise ValueError(f"Unknown PE type: {self.type}")


@dataclass
class ResourceComplexRule:
    """Map an SGE ``-l`` complex to a Slurm #SBATCH flag."""

    slurm_flag: str  # e.g. time, mem-per-cpu, mem
    transform: str = "identity"  # identity | strip_suffix_G


@dataclass
class UserConfig:
    """Loaded from optional YAML/TOML."""

    account_map: dict[str, str] = field(default_factory=dict)
    partition_map: dict[str, str] = field(default_factory=dict)
    parallel_environments: dict[str, PeRule] = field(default_factory=dict)
    resource_complexes: dict[str, ResourceComplexRule] = field(default_factory=dict)
    defaults_before_body: list[str] = field(default_factory=list)
    defaults_after_sbatch: list[str] = field(default_factory=list)


def _parse_pe_rule(data: Any) -> PeRule:
    if isinstance(data, str):
        return PeRule(type=data)
    if not isinstance(data, dict):
        return PeRule()
    return PeRule(
        type=str(data.get("type", "openmp")),
        tasks_per_node=int(data["tasks_per_node"]) if data.get("tasks_per_node") else None,
    )


def _parse_resource_rule(data: Any) -> ResourceComplexRule:
    if isinstance(data, str):
        return ResourceComplexRule(slurm_flag=data)
    if not isinstance(data, dict):
        return ResourceComplexRule(slurm_flag="mem")
    return ResourceComplexRule(
        slurm_flag=str(data.get("slurm_flag", "mem")),
        transform=str(data.get("transform", "identity")),
    )


def load_config(path: Path | None) -> UserConfig:
    if path is None:
        return UserConfig()
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        raw = yaml.safe_load(text) or {}
    elif suffix == ".toml":
        raw = tomllib.loads(text)
    else:
        raise ValueError(f"Unsupported config format: {path.suffix} (use .yaml, .yml, or .toml)")

    if not isinstance(raw, dict):
        raise ValueError("Config root must be a mapping")

    cfg = UserConfig()
    if "account" in raw and isinstance(raw["account"], dict):
        cfg.account_map = {str(k): str(v) for k, v in raw["account"].items()}
    if "partitions" in raw and isinstance(raw["partitions"], dict):
        cfg.partition_map = {str(k): str(v) for k, v in raw["partitions"].items()}
    if "parallel_environments" in raw and isinstance(raw["parallel_environments"], dict):
        for name, spec in raw["parallel_environments"].items():
            cfg.parallel_environments[str(name)] = _parse_pe_rule(spec)
    if "resource_complexes" in raw and isinstance(raw["resource_complexes"], dict):
        for name, spec in raw["resource_complexes"].items():
            cfg.resource_complexes[str(name)] = _parse_resource_rule(spec)
    if "defaults" in raw and isinstance(raw["defaults"], dict):
        d = raw["defaults"]
        if isinstance(d.get("prepend"), list):
            cfg.defaults_before_body = [str(x) for x in d["prepend"]]
        after: list[str] = []
        if isinstance(d.get("append"), list):
            after.extend(str(x) for x in d["append"])
        if isinstance(d.get("sbatch"), list):
            after.extend(str(x) for x in d["sbatch"])
        if after:
            cfg.defaults_after_sbatch = after
    return cfg


def resolve_partition(partition_map: dict[str, str], queue: str) -> str | None:
    if queue in partition_map:
        return partition_map[queue]
    for pattern, dest in partition_map.items():
        if pattern.startswith("regex:"):
            rx = pattern[6:]
            if re.search(rx, queue):
                return dest
    return None
