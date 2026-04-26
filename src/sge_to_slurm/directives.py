from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field

from sge_to_slurm.config import PeRule, ResourceComplexRule, UserConfig, resolve_partition
from sge_to_slurm.models import LineStatus


def strip_sge_host_path(raw: str) -> tuple[str, bool]:
    """Strip optional ``host:`` prefix from -o/-e paths."""
    stripped = False
    s = raw.strip()
    if ":" in s and not s.startswith("/") and re.match(r"^[\w.-]+:", s):
        stripped = True
        s = s.split(":", 1)[1]
    return s, stripped


def parse_l_resources(arg: str) -> dict[str, str]:
    """Parse ``h_rt=12:00:00,mem=4G`` style resource list."""
    out: dict[str, str] = {}
    for part in arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        else:
            out[part] = ""
    return out


@dataclass
class DirectiveState:
    job_name: str | None = None
    output_path: str | None = None
    error_path: str | None = None
    join_stderr_stdout: bool = False
    mail_types: list[str] = field(default_factory=list)
    mail_user: str | None = None
    cwd: bool = False
    account: str | None = None
    project_unmapped: str | None = None
    partition: str | None = None
    array_spec: str | None = None
    hold_jids: list[str] = field(default_factory=list)
    time_limit: str | None = None
    mem_per_cpu: str | None = None
    mem_total: str | None = None
    cpus_per_task: int | None = None
    nodes: int | None = None
    ntasks: int | None = None
    ntasks_per_node: int | None = None
    gres_lines: list[str] = field(default_factory=list)
    other_sbatch: list[str] = field(default_factory=list)
    line_warnings: list[str] = field(default_factory=list)


def _mail_sge_to_slurm(flags: str) -> list[str]:
    mapping = {"b": "BEGIN", "e": "END", "a": "FAIL", "s": "ALL", "n": "NONE"}
    out: list[str] = []
    for ch in flags.replace(",", "").replace(" ", ""):
        if ch in mapping:
            m = mapping[ch]
            if m == "NONE":
                return ["NONE"]
            if m not in out and m != "NONE":
                out.append(m)
    return out if out else []


def _sge_array_to_slurm(spec: str) -> str:
    return spec.strip()


def _builtin_resource(key: str) -> ResourceComplexRule | None:
    if key == "h_rt":
        return ResourceComplexRule(slurm_flag="time", transform="identity")
    if key == "mem_per_core":
        return ResourceComplexRule(slurm_flag="mem-per-cpu", transform="identity")
    if key in ("mem_free", "s_vmem", "h_vmem"):
        return ResourceComplexRule(slurm_flag="mem", transform="identity")
    return None


def _apply_l_resources(
    state: DirectiveState,
    resources: dict[str, str],
    cfg: UserConfig,
    soft: bool,
    line_msgs: list[str],
) -> None:
    for key, val in resources.items():
        rule = cfg.resource_complexes.get(key) or _builtin_resource(key)
        if rule is None:
            line_msgs.append(f"-l key {key!r} not mapped; ignored")
            continue
        if soft:
            line_msgs.append("-l under -soft emitted as hard #SBATCH")
        flag = rule.slurm_flag
        value = val
        if rule.transform == "strip_suffix_G" and value.endswith("G"):
            value = value[:-1]
        if flag == "time":
            state.time_limit = value
        elif flag == "mem-per-cpu":
            state.mem_per_cpu = value
        elif flag == "mem":
            state.mem_total = value
        elif flag.startswith("gres"):
            state.gres_lines.append(f"#SBATCH --gres={value}")
        else:
            state.other_sbatch.append(f"#SBATCH --{flag}={value}")


def _apply_pe(
    state: DirectiveState,
    pe_name: str,
    slots: int,
    cfg: UserConfig,
    line_msgs: list[str],
) -> bool:
    """Return False if PE could not be mapped (caller marks line ERROR)."""
    rule = cfg.parallel_environments.get(pe_name)
    if rule is None:
        if pe_name == "omp" or pe_name.endswith("_omp"):
            rule = PeRule(type="openmp")
        else:
            return False
    if rule.type == "openmp":
        state.cpus_per_task = slots
        state.nodes = 1
        line_msgs.append("OpenMP PE -> --cpus-per-task (verify site policy)")
    elif rule.type == "mpi_slots":
        tpn = rule.tasks_per_node or 1
        if slots % tpn != 0:
            line_msgs.append(
                f"slots {slots} not divisible by tasks_per_node {tpn}; check ntasks layout"
            )
        state.ntasks = slots
        state.ntasks_per_node = tpn
        line_msgs.append("MPI PE -> ntasks / ntasks-per-node from config")
    return True


def _worst(a: LineStatus, b: LineStatus) -> LineStatus:
    order = {
        LineStatus.NEUTRAL: 0,
        LineStatus.OK: 1,
        LineStatus.WARNING: 2,
        LineStatus.ERROR: 3,
    }
    return a if order[a] >= order[b] else b


def merge_qsub_argv(
    state: DirectiveState,
    argv: list[str],
    cfg: UserConfig,
) -> tuple[LineStatus, list[str]]:
    """
    Merge one directive line's argv into ``state``.
    Returns (worst status, human messages for this line).
    """
    msgs: list[str] = []
    status = LineStatus.OK
    i = 0
    soft_next = False

    while i < len(argv):
        tok = argv[i]
        if tok in ("-soft",):
            soft_next = True
            i += 1
            continue
        if tok in ("-hard",):
            soft_next = False
            i += 1
            continue

        if tok == "-N" and i + 1 < len(argv):
            state.job_name = argv[i + 1]
            if soft_next:
                msgs.append("-N with -soft (treated as hard)")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-o" and i + 1 < len(argv):
            path, host_strip = strip_sge_host_path(argv[i + 1])
            state.output_path = path
            if host_strip:
                msgs.append("stripped hostname: from -o path")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-e" and i + 1 < len(argv):
            path, host_strip = strip_sge_host_path(argv[i + 1])
            state.error_path = path
            if host_strip:
                msgs.append("stripped hostname: from -e path")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-j" and i + 1 < len(argv):
            state.join_stderr_stdout = argv[i + 1].lower() in ("y", "yes")
            i += 2
            soft_next = False
            continue
        if tok == "-m" and i + 1 < len(argv):
            state.mail_types = _mail_sge_to_slurm(argv[i + 1])
            i += 2
            soft_next = False
            continue
        if tok == "-M" and i + 1 < len(argv):
            state.mail_user = argv[i + 1]
            i += 2
            soft_next = False
            continue
        if tok == "-cwd":
            state.cwd = True
            msgs.append("-cwd -> #SBATCH --chdir=$PWD (requires Slurm 22.05+ or adjust)")
            status = _worst(status, LineStatus.WARNING)
            i += 1
            soft_next = False
            continue
        if tok == "-P" and i + 1 < len(argv):
            proj = argv[i + 1]
            if proj in cfg.account_map:
                state.account = cfg.account_map[proj]
                state.project_unmapped = None
            else:
                state.project_unmapped = proj
                state.account = None
                msgs.append(f"no account mapping for -P {proj!r} in config")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-q" and i + 1 < len(argv):
            q = argv[i + 1]
            resolved = resolve_partition(cfg.partition_map, q)
            if resolved:
                state.partition = resolved
            else:
                state.partition = None
                msgs.append(f"no partition mapping for -q {q!r}")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-t" and i + 1 < len(argv):
            spec = argv[i + 1]
            state.array_spec = _sge_array_to_slurm(spec)
            if ":" in spec:
                msgs.append("-t step may differ from Slurm --array semantics")
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-hold_jid" and i + 1 < len(argv):
            raw = argv[i + 1]
            state.hold_jids.extend(
                x.strip() for x in raw.replace(" ", ",").split(",") if x.strip()
            )
            msgs.append("afterok uses job IDs; verify dependency targets")
            status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-l" and i + 1 < len(argv):
            resources = parse_l_resources(argv[i + 1])
            before = len(msgs)
            _apply_l_resources(state, resources, cfg, soft_next, msgs)
            if len(msgs) > before or soft_next:
                status = _worst(status, LineStatus.WARNING)
            i += 2
            soft_next = False
            continue
        if tok == "-pe" and i + 2 < len(argv):
            pe_name = argv[i + 1]
            try:
                slots = int(argv[i + 2])
            except ValueError:
                msgs.append(f"invalid slot count for -pe {pe_name}")
                status = LineStatus.ERROR
                i += 3
                soft_next = False
                continue
            if not _apply_pe(state, pe_name, slots, cfg, msgs):
                msgs.append(f"unknown PE {pe_name!r}; add parallel_environments in config")
                status = LineStatus.ERROR
            else:
                status = _worst(status, LineStatus.WARNING)
            i += 3
            soft_next = False
            continue

        if tok.startswith("-"):
            msgs.append(f"unsupported: {tok}")
            status = LineStatus.ERROR
        i += 1
        soft_next = False

    return status, msgs


def state_to_sbatch_lines(state: DirectiveState) -> list[str]:
    lines: list[str] = []
    if state.job_name:
        lines.append(f"#SBATCH --job-name={state.job_name}")
    if state.account:
        lines.append(f"#SBATCH --account={state.account}")
    if state.project_unmapped and not state.account:
        lines.append(
            f"# TODO: map SGE -P {state.project_unmapped} to #SBATCH --account=... in config (account:)"
        )
    if state.partition:
        lines.append(f"#SBATCH --partition={state.partition}")
    if state.time_limit:
        lines.append(f"#SBATCH --time={state.time_limit}")
    if state.mem_per_cpu:
        lines.append(f"#SBATCH --mem-per-cpu={state.mem_per_cpu}")
    if state.mem_total:
        lines.append(f"#SBATCH --mem={state.mem_total}")
    if state.cpus_per_task:
        lines.append(f"#SBATCH --cpus-per-task={state.cpus_per_task}")
    if state.nodes is not None:
        lines.append(f"#SBATCH --nodes={state.nodes}")
    if state.ntasks is not None:
        lines.append(f"#SBATCH --ntasks={state.ntasks}")
    if state.ntasks_per_node is not None:
        lines.append(f"#SBATCH --ntasks-per-node={state.ntasks_per_node}")
    if state.array_spec:
        lines.append(f"#SBATCH --array={state.array_spec}")
    if state.hold_jids:
        dep = ":".join(state.hold_jids)
        lines.append(f"#SBATCH --dependency=afterok:{dep}")
    if state.mail_types:
        lines.append(f"#SBATCH --mail-type={','.join(state.mail_types)}")
    if state.mail_user:
        lines.append(f"#SBATCH --mail-user={state.mail_user}")
    if state.cwd:
        lines.append("#SBATCH --chdir=$PWD")
    out_path = state.output_path
    err_path = state.error_path
    if state.join_stderr_stdout and out_path:
        lines.append(f"#SBATCH --output={out_path}")
        lines.append(f"#SBATCH --error={out_path}")
    else:
        if out_path:
            lines.append(f"#SBATCH --output={out_path}")
        if err_path:
            lines.append(f"#SBATCH --error={err_path}")
    lines.extend(state.gres_lines)
    lines.extend(state.other_sbatch)
    return lines


@dataclass
class DirectiveLineParse:
    is_directive: bool
    argv: list[str] | None = None
    parse_error: bool = False


def parse_directive_line(content: str) -> DirectiveLineParse:
    stripped = content.strip()
    if not stripped.startswith("#$"):
        return DirectiveLineParse(is_directive=False)
    rest = stripped[2:].strip()
    if not rest:
        return DirectiveLineParse(is_directive=True, argv=[])
    try:
        return DirectiveLineParse(is_directive=True, argv=shlex.split(rest, posix=True))
    except ValueError:
        return DirectiveLineParse(is_directive=True, argv=None, parse_error=True)
