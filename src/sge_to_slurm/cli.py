from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from sge_to_slurm import __version__
from sge_to_slurm.config import load_config
from sge_to_slurm.converter import convert_file
from sge_to_slurm.io_util import atomic_write_text, default_output_path, ensure_output_writable
from sge_to_slurm.report import print_line_reports, print_summary

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert Sun Grid Engine (qsub) batch scripts to Slurm (sbatch) scripts.",
)


def _resolve_config_path(config: Path | None) -> Path | None:
    """Resolve config path with CLI arg first, then module/env defaults."""
    if config is not None:
        return config
    env_cfg = os.getenv("SGE_TO_SLURM_CONFIG")
    if env_cfg:
        return Path(env_cfg)
    return None


@app.command("convert")
def convert_cmd(
    input_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            readable=True,
            dir_okay=False,
            help="Path to the SGE/qsub-style shell script.",
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path (default: <stem>_slurm<suffix> next to input)."),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", "-c", help="YAML or TOML file with site mappings."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite the output file if it already exists."),
    ] = False,
    no_write: Annotated[
        bool,
        typer.Option("--no-write", help="Parse and report only; do not write an output file."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress per-line trace; still print summary."),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Show emitted lines for each input line."),
    ] = False,
    encoding: Annotated[
        str,
        typer.Option("--encoding", help="Text encoding for reading the input script."),
    ] = "utf-8",
) -> None:
    """Convert INPUT to a Slurm batch script and print a line-by-line report."""
    console = Console(stderr=False)
    err_console = Console(stderr=True)

    out_path = output if output is not None else default_output_path(input_path)

    try:
        cfg = load_config(_resolve_config_path(config))
    except (OSError, ValueError) as e:
        err_console.print(f"[red]Config error:[/red] {e}")
        raise typer.Exit(code=2) from e

    try:
        result = convert_file(input_path, cfg, encoding=encoding)
    except OSError as e:
        err_console.print(f"[red]Read error:[/red] {e}")
        raise typer.Exit(code=2) from e

    print_line_reports(console, result, verbose=verbose, quiet=quiet)

    wrote: str | None = None
    if not no_write:
        try:
            ensure_output_writable(out_path, force)
        except FileExistsError as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(code=2) from e
        try:
            atomic_write_text(out_path, result.output_text, encoding=encoding)
            wrote = str(out_path.resolve())
        except OSError as e:
            err_console.print(f"[red]Write error:[/red] {e}")
            raise typer.Exit(code=2) from e

    print_summary(console, result, wrote)


@app.command("version")
def version_cmd() -> None:
    """Print the package version."""
    typer.echo(__version__)


def main() -> None:
    argv = sys.argv[1:]
    if argv:
        first = argv[0]
        if first not in ("convert", "version", "--help", "-h", "--version") and not first.startswith("-"):
            sys.argv = [sys.argv[0], "convert", *argv]
    app()


if __name__ == "__main__":
    main()
