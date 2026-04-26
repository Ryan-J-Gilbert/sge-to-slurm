from __future__ import annotations

from pathlib import Path

from sge_to_slurm.body import transform_body_line
from sge_to_slurm.config import UserConfig
from sge_to_slurm.directives import (
    DirectiveState,
    merge_qsub_argv,
    parse_directive_line,
    state_to_sbatch_lines,
)
from sge_to_slurm.models import ConversionResult, LineKind, LineReport, LineStatus


def _normalize_sbatch_line(line: str) -> str:
    s = line.strip()
    if s.startswith("#SBATCH") or s.startswith("# -"):
        return s
    if not s:
        return ""
    return f"#SBATCH {s}"


def convert_script(source: str, cfg: UserConfig) -> ConversionResult:
    raw_lines = source.splitlines(keepends=True)
    reports: list[LineReport] = []
    state = DirectiveState()

    for idx, raw in enumerate(raw_lines, start=1):
        if raw.endswith("\r\n"):
            nl = "\r\n"
            content = raw[:-2]
        elif raw.endswith("\n"):
            nl = "\n"
            content = raw[:-1]
        elif raw.endswith("\r"):
            nl = "\r"
            content = raw[:-1]
        else:
            nl = ""
            content = raw

        if not content.strip():
            reports.append(
                LineReport(
                    line_no=idx,
                    kind=LineKind.BLANK,
                    status=LineStatus.NEUTRAL,
                    source=content,
                    message="",
                    emitted=[raw],
                )
            )
            continue

        dparse = parse_directive_line(content)
        if dparse.is_directive:
            if dparse.parse_error:
                reports.append(
                    LineReport(
                        line_no=idx,
                        kind=LineKind.SGE_DIRECTIVE,
                        status=LineStatus.ERROR,
                        source=content,
                        message="could not parse #$ line (shlex error)",
                        emitted=[f"# (SGE, unparseable) {content}{nl}"],
                    )
                )
                continue
            assert dparse.argv is not None
            st, msgs = merge_qsub_argv(state, dparse.argv, cfg)
            msg = "; ".join(msgs) if msgs else ""
            emitted: list[str] = []
            if st == LineStatus.ERROR:
                emitted = [f"# (SGE, unsupported) {content}{nl}"]
            reports.append(
                LineReport(
                    line_no=idx,
                    kind=LineKind.SGE_DIRECTIVE,
                    status=st,
                    source=content,
                    message=msg,
                    emitted=emitted,
                )
            )
            continue

        if idx == 1 and content.lstrip().startswith("#!"):
            st = LineStatus.OK
            msg = ""
            if " -l" in content or content.rstrip().endswith("-l"):
                st = LineStatus.WARNING
                msg = "shebang uses -l (login shell); verify Slurm environment"
            reports.append(
                LineReport(
                    line_no=idx,
                    kind=LineKind.SHEBANG,
                    status=st,
                    source=content,
                    message=msg,
                    emitted=[raw],
                )
            )
            continue

        if content.lstrip().startswith("#"):
            reports.append(
                LineReport(
                    line_no=idx,
                    kind=LineKind.COMMENT,
                    status=LineStatus.NEUTRAL,
                    source=content,
                    message="",
                    emitted=[raw],
                )
            )
            continue

        bt = transform_body_line(content)
        rep_status = bt.status
        if rep_status == LineStatus.NEUTRAL:
            rep_status = LineStatus.NEUTRAL
        reports.append(
            LineReport(
                line_no=idx,
                kind=LineKind.BODY,
                status=rep_status,
                source=content,
                message="; ".join(bt.messages) if bt.messages else "",
                emitted=[bt.text + nl],
            )
        )

    sbatch_lines: list[str] = []
    for ln in cfg.defaults_after_sbatch:
        n = _normalize_sbatch_line(ln)
        if n:
            sbatch_lines.append(n)
    sbatch_lines.extend(state_to_sbatch_lines(state))

    out_parts: list[str] = []
    shebang_written = False
    for rep in reports:
        if rep.kind == LineKind.SHEBANG:
            out_parts.extend(rep.emitted)
            shebang_written = True
            break

    if not shebang_written:
        out_parts.append("#!/bin/bash\n")

    for extra in cfg.defaults_before_body:
        n = _normalize_sbatch_line(extra)
        if n:
            out_parts.append(n + "\n")

    for sb in sbatch_lines:
        out_parts.append(sb + "\n")

    for rep in reports:
        if rep.kind in (LineKind.SHEBANG, LineKind.SGE_DIRECTIVE):
            continue
        out_parts.extend(rep.emitted)

    output_text = "".join(out_parts)
    return ConversionResult(output_text=output_text, lines=reports, output_path=None)


def convert_file(path: Path, cfg: UserConfig, encoding: str = "utf-8") -> ConversionResult:
    text = path.read_text(encoding=encoding)
    return convert_script(text, cfg)
