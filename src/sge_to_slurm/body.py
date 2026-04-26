from __future__ import annotations

import re
from dataclasses import dataclass

from sge_to_slurm.models import LineStatus

# Whole-word SGE -> Slurm (common job / array / slot variables)
DEFAULT_ENV_MAP: dict[str, str] = {
    "JOB_ID": "SLURM_JOB_ID",
    "JOB_NAME": "SLURM_JOB_NAME",
    "SGE_TASK_ID": "SLURM_ARRAY_TASK_ID",
    "SGE_TASK_FIRST": "SLURM_ARRAY_TASK_MIN",
    "SGE_TASK_LAST": "SLURM_ARRAY_TASK_MAX",
    "SGE_TASK_STEPSIZE": "SLURM_ARRAY_TASK_STEP",
    "NSLOTS": "SLURM_CPUS_PER_TASK",
    "NHOSTS": "SLURM_JOB_NUM_NODES",
}


@dataclass
class BodyTransformResult:
    text: str
    status: LineStatus
    messages: list[str]


_QSUB_INLINE = re.compile(r"\bqsub\b")


def detect_inline_qsub(line: str) -> bool:
    s = line.strip()
    if s.startswith("#"):
        return False
    return bool(_QSUB_INLINE.search(line))


def transform_body_line(
    line: str,
    env_map: dict[str, str] | None = None,
) -> BodyTransformResult:
    """
    Quoting-aware replacement of ``$VAR`` / ``${VAR}`` for allowlisted SGE names.
    Single-quoted segments are skipped. Heredocs (``<<``) are skipped with a warning.
    """
    if re.search(r"<<", line):
        return BodyTransformResult(
            text=line,
            status=LineStatus.WARNING,
            messages=["heredoc (<<) on line; env substitution skipped"],
        )
    if detect_inline_qsub(line):
        return BodyTransformResult(
            text=line,
            status=LineStatus.ERROR,
            messages=["line contains qsub; not transformed - submit manually"],
        )

    mapping = env_map if env_map is not None else DEFAULT_ENV_MAP
    out: list[str] = []
    i = 0
    changed = False
    in_single = False

    while i < len(line):
        c = line[i]
        if c == "'" and not in_single:
            in_single = True
            out.append(c)
            i += 1
            continue
        if in_single:
            out.append(c)
            if c == "'":
                in_single = False
            i += 1
            continue
        if c == "$":
            _name, repl, consumed = _try_replace_var(line, i, mapping)
            if repl is not None:
                out.append(repl)
                changed = True
                i += consumed
                continue
        out.append(c)
        i += 1

    if not changed:
        return BodyTransformResult(text=line, status=LineStatus.NEUTRAL, messages=[])
    return BodyTransformResult(text="".join(out), status=LineStatus.OK, messages=[])


def _try_replace_var(
    line: str,
    start: int,
    mapping: dict[str, str],
) -> tuple[str | None, str | None, int]:
    """
    If line[start] == '$', try to match a mapped variable.
    Returns (original_name, replacement, char_count_consumed) or (None, None, 0).
    """
    if start >= len(line) or line[start] != "$":
        return None, None, 0
    if start + 1 < len(line) and line[start + 1] == "{":
        end = line.find("}", start + 2)
        if end == -1:
            return None, None, 0
        name = line[start + 2 : end]
        if name in mapping:
            inner = mapping[name]
            return name, "${" + inner + "}", end - start + 1
        return None, None, 0
    j = start + 1
    while j < len(line) and (line[j].isalnum() or line[j] == "_"):
        j += 1
    if j == start + 1:
        return None, None, 0
    name = line[start + 1 : j]
    if name in mapping:
        return name, "${" + mapping[name] + "}", j - start
    return None, None, 0
