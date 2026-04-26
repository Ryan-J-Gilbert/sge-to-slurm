from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from sge_to_slurm.models import ConversionResult, LineStatus


def _arrow_style(status: LineStatus) -> str:
    if status == LineStatus.ERROR:
        return "bold red"
    if status == LineStatus.WARNING:
        return "bold yellow"
    if status == LineStatus.NEUTRAL:
        return "dim"
    return "bold green"


def print_line_reports(
    console: Console,
    result: ConversionResult,
    *,
    verbose: bool,
    quiet: bool,
) -> None:
    if quiet:
        return
    for rep in result.lines:
        arrow = Text("→ ", style=_arrow_style(rep.status))
        head = Text(f"L{rep.line_no} ", style="cyan")
        kind = Text(f"[{rep.kind.value}] ", style="dim")
        msg = Text(rep.message, style="dim") if rep.message else Text("")
        line_preview = rep.source if len(rep.source) < 120 else rep.source[:117] + "..."
        src = Text(line_preview, style="white")

        row = Text.assemble(arrow, head, kind, src)
        console.print(row)
        if rep.message:
            console.print(Text(f"    {rep.message}", style="yellow dim"))
        if verbose and rep.emitted:
            for em in rep.emitted:
                em_stripped = em.rstrip("\r\n")
                console.print(Text(f"    => {em_stripped}", style="green dim"))


def print_summary(console: Console, result: ConversionResult, wrote_path: str | None) -> None:
    ok, warn, err = result.counts
    if err == 0 and warn == 0:
        title = "Fully successful"
        border = "green"
    else:
        title = "Partially successful"
        border = "yellow" if err == 0 else "red"

    body = (
        f"[green]OK (converted / clean):[/green] {ok}\n"
        f"[yellow]Warnings (partial):[/yellow] {warn}\n"
        f"[red]Not converted (errors):[/red] {err}\n"
    )
    if wrote_path:
        body += f"\n[bold]Output written:[/bold] {wrote_path}"
    else:
        body += "\n[bold]Dry run:[/bold] no file written (--no-write)"

    console.print(Panel(body, title=title, border_style=border))
