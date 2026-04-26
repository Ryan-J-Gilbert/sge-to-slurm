# sge-to-slurm

Convert **Sun Grid Engine (SGE)** batch scripts (typically submitted with `qsub` and lines starting with `#$`) into **Slurm** batch scripts (submitted with `sbatch`, using `#SBATCH`). The tool is a **best-effort migrator**: it prints a **line-by-line** report (with [Rich](https://rich.readthedocs.io/) colors), writes a new script next to the original, and uses an optional **site config** (YAML or TOML) so your cluster’s projects, queues, and parallel environments map cleanly to Slurm.

**Python:** 3.11+ (see `requires-python` in [`pyproject.toml`](pyproject.toml)).

---

## Table of contents

- [Quick start](#quick-start)
- [Installation](#installation)
- [CLI reference](#cli-reference)
- [Output files and I/O behavior](#output-files-and-io-behavior)
- [How conversion works](#how-conversion-works)
- [Terminal output (Rich)](#terminal-output-rich)
- [Exit codes](#exit-codes)
- [Configuration file](#configuration-file)
- [Supported SGE features](#supported-sge-features)
- [Body lines (shell)](#body-lines-shell)
- [Limitations](#limitations)
- [Project layout](#project-layout)
- [Development and tests](#development-and-tests)
- [References in this repo](#references-in-this-repo)

---

## Quick start

```bash
cd sge-to-slurm
uv sync --group dev
uv run sge-to-slurm path/to/job.sh --config sge_to_slurm.example.yaml
```

Default output: `path/to/job_slurm.sh` (same directory, `_slurm` inserted before the file extension). If that file already exists, the tool **exits with an error** unless you pass `--force`.

Dry run (no file written):

```bash
uv run sge-to-slurm path/to/job.sh --no-write
```

---

## Installation

### Recommended: uv (local virtual environment)

[uv](https://docs.astral.sh/uv/) keeps the project and dev tools in `.venv` instead of installing into your global Python.

```bash
uv sync --group dev    # install project + pytest (see [dependency-groups] in pyproject.toml)
uv run pytest
uv run sge-to-slurm --help
```

Lockfile: [`uv.lock`](uv.lock) — use `uv lock` after dependency changes.

### Alternative: pip

```bash
pip install -e ".[dev]"
pytest
sge-to-slurm --help
```

---

## CLI reference

The Typer application exposes:

| Command | Purpose |
|--------|---------|
| `convert` | Convert one input script (this is the main command). |
| `version` | Print package version from `sge_to_slurm.__version__`. |

**Entry point:** `sge-to-slurm` → `sge_to_slurm.cli:main`.  
`main()` prepends the word `convert` when the first CLI argument is **not** `convert`, `version`, `--help`, `-h`, or `--version`, and does not start with `-`. So these are equivalent when `job.sh` exists:

```bash
sge-to-slurm job.sh
sge-to-slurm convert job.sh
```

### `convert` arguments and options

| Argument / option | Short | Description |
|-------------------|-------|-------------|
| `INPUT_PATH` | — | Required. Path to the SGE-style script (must exist, must be a file). |
| `--output` | `-o` | Output path. Default: same directory as input, name `<stem>_slurm<suffix>` (e.g. `run.sh` → `run_slurm.sh`). |
| `--config` | `-c` | Optional YAML (`.yaml`/`.yml`) or TOML (`.toml`) site config. If omitted, conversion uses **built-in** `-l` mappings only and does not map `-P`/`-q`/custom `-pe` names. |
| `--force` | `-f` | Allow overwriting an existing output file. |
| `--no-write` | — | Parse, print the report, print the summary; **do not** write the output script. |
| `--quiet` | `-q` | Hide the per-line trace; summary panel still prints. |
| `--verbose` | `-v` | After each line in the trace, print emitted lines (e.g. transformed body). |
| `--encoding` | — | Text encoding for **reading** the input file (default `utf-8`). The output file is written with the same encoding. |

Global help:

```bash
uv run sge-to-slurm convert --help
```

---

## Output files and I/O behavior

- **Default path:** [`default_output_path`](src/sge_to_slurm/io_util.py) — `input.stem + "_slurm" + input.suffix`, same parent directory as the input.
- **No clobber:** If the target path exists and `--force` is not set, [`ensure_output_writable`](src/sge_to_slurm/io_util.py) raises `FileExistsError`; the CLI prints the error and exits with code **2**.
- **Atomic write:** [`atomic_write_text`](src/sge_to_slurm/io_util.py) writes to a temp file in the output directory, then `os.replace` onto the final name so readers never see a half-written script.

---

## How conversion works

High-level pipeline ([`converter.py`](src/sge_to_slurm/converter.py), [`directives.py`](src/sge_to_slurm/directives.py), [`body.py`](src/sge_to_slurm/body.py)):

1. **Read** the whole script as text (per `--encoding`).
2. **Classify each line:** blank, SGE directive (`#$ ...`), shebang (line 1 only, if it starts with `#!` after optional leading whitespace), other `#` lines as comments, everything else as **body**.
3. **Parse directives** with `shlex` (POSIX quoting) on the text after `#$`.
4. **Merge** all `#$` lines into one [`DirectiveState`](src/sge_to_slurm/directives.py) via [`merge_qsub_argv`](src/sge_to_slurm/directives.py), consulting [`UserConfig`](src/sge_to_slurm/config.py) for site-specific mappings.
5. **Transform body** lines: optional env-var substitution, `qsub` detection, heredoc warning (see [Body lines](#body-lines-shell)).
6. **Emit** the Slurm script:
   - Shebang from the original (or `#!/bin/bash` if missing).
   - Optional `defaults.prepend` from config, normalized to `#SBATCH` lines.
   - **`#SBATCH` block:** config `defaults.append` / `defaults.sbatch`, then all lines from [`state_to_sbatch_lines`](src/sge_to_slurm/directives.py) (derived from merged directives).
   - **Rest of script:** original non-directive lines in order (comments, blanks, body), with `#$` lines **omitted** except when a directive could not be converted (a comment line may be emitted to preserve context).

This matches the design choice to **group** `#SBATCH` directives near the top (after shebang), not to keep `#$` lines in place.

---

## Terminal output (Rich)

- **Per-line trace** (unless `--quiet`): for each input line, a colored arrow, line number, kind (`shebang`, `sge_directive`, `comment`, `blank`, `body`), and a short preview of the source. Optional message under the line for warnings/errors. With `--verbose`, emitted replacement lines are shown indented.
- **Arrow colors** ([`report.py`](src/sge_to_slurm/report.py)): green = OK, yellow = warning, red = error, dim = neutral (e.g. blank/comment).
- **Summary panel:** counts of lines by status (OK / warning / error), title **Fully successful** when there are zero warnings and zero errors on counted statuses, otherwise **Partially successful**; plus either the resolved output path or a dry-run note.

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success (including conversion with warnings or “error” line statuses — exit code does **not** reflect conversion quality). |
| `2` | Hard failure: bad config path/format, read/write error, or refuse to overwrite without `--force`. |

There is **no** `--strict` flag yet; red lines in the report do not change the process exit code by design.

---

## Configuration file

Loaded only when you pass `--config`. Implemented in [`config.py`](src/sge_to_slurm/config.py).

### Formats

- **YAML:** `.yaml` / `.yml` via PyYAML `safe_load`.
- **TOML:** `.toml` via the standard library `tomllib`.

Any other extension raises `ValueError` (printed as a config error, exit 2).

### Top-level keys (all optional)

#### `account` (mapping)

Maps SGE **`-P`** *project name* → Slurm **`--account=`** value.

If `-P foo` appears and `foo` is not in this table, the converter still emits a `# TODO:` comment in the output and marks the directive line with a **warning** (no `--account` guessed).

#### `partitions` (mapping)

Maps SGE **`-q`** *queue name* → Slurm **`--partition=`** value.

- Exact string keys match the queue name first.
- A key may be **`regex:PATTERN`**, in which case [`resolve_partition`](src/sge_to_slurm/config.py) uses `re.search(PATTERN, queue)` and the value is the partition name.

Unmapped `-q` → warning; no `#SBATCH --partition` emitted.

#### `parallel_environments` (mapping)

Maps **`-pe <name> <slots>`** to Slurm CPU / task layout via [`PeRule`](src/sge_to_slurm/config.py):

| `type` | Behavior |
|--------|----------|
| `openmp` | Sets `--cpus-per-task=<slots>` and `--nodes=1`. |
| `mpi_slots` | Requires `tasks_per_node` in the rule; sets `--ntasks=<slots>` and `--ntasks-per-node=<tasks_per_node>`. |

**Built-in fallback (no config entry):** PE names `omp` or ending with `_omp` are treated as `openmp`. Any other PE name **must** appear under `parallel_environments` or the `#$` line is marked **error** and a `# (SGE, unsupported) ...` comment is emitted in the body section.

#### `resource_complexes` (mapping)

Overrides or **adds** handling for **`-l`** resource *keys* (the part before `=` in `h_rt=12:00:00` or comma-separated lists).

Each value can be:

- A **string** → interpreted as `slurm_flag` for [`ResourceComplexRule`](src/sge_to_slurm/config.py), or
- A **mapping** with `slurm_flag` and optional `transform` (`identity` or `strip_suffix_G`).

Resolution order for each `-l` key: **config** first, then built-ins (see below).

How `slurm_flag` is applied in [`_apply_l_resources`](src/sge_to_slurm/directives.py):

| `slurm_flag` | Effect on `DirectiveState` / output |
|--------------|--------------------------------------|
| `time` | `--time=` |
| `mem-per-cpu` | `--mem-per-cpu=` |
| `mem` | `--mem=` |
| starts with `gres` | `#SBATCH --gres=<value>` |
| anything else | `#SBATCH --<flag>=<value>` |

#### `defaults` (mapping)

| Sub-key | Meaning |
|---------|---------|
| `prepend` | List of strings: each normalized to a `#SBATCH` line and written **after the shebang**, **before** the merged `#SBATCH` block from directives + `append`. |
| `append` | List of strings: merged into the start of the auto `#SBATCH` block (with `sbatch`, see below). |
| `sbatch` | Same storage as `append`: both lists are **concatenated** into `defaults_after_sbatch` (append first, then sbatch, in code order). |

Strings under `prepend` / `append` / `sbatch` may be either full lines (`#SBATCH --foo=bar`) or short forms (`--nodes=1`); see [`_normalize_sbatch_line`](src/sge_to_slurm/converter.py).

### Example file

See [`sge_to_slurm.example.yaml`](sge_to_slurm.example.yaml) for a copy-paste template.

### TOML shape

Same logical keys; use TOML tables, e.g.:

```toml
[account]
my_project = "my_slurm_account"
```

---

## Supported SGE features

### Built-in `-l` resource keys (no config required)

| Key | Slurm output |
|-----|----------------|
| `h_rt` | `--time=` |
| `mem_per_core` | `--mem-per-cpu=` |
| `mem_free`, `s_vmem`, `h_vmem` | `--mem=` (value passed through; semantics may differ from SGE — treated as heuristic) |

Other `-l` keys need **`resource_complexes`** in config or they are **ignored** with a warning on that directive line.

### Parsed `#$` options (merged across all directive lines)

| Option | Slurm / notes |
|--------|----------------|
| `-N` | `--job-name` |
| `-o` / `-e` | `--output` / `--error`; optional `host:` prefix stripped (warning) |
| `-j y` | Same file for stdout and stderr (`--output` and `--error` set to the same path) |
| `-m` | `--mail-type` (SGE letters mapped to Slurm types; `n` → `NONE`) |
| `-M` | `--mail-user` |
| `-cwd` | `#SBATCH --chdir=$PWD` (warning: needs Slurm 22.05+ or site-specific adjustment) |
| `-P` | `--account` only if `account` map in config matches |
| `-q` | `--partition` only if `partitions` map matches |
| `-t` | `--array=` (surface syntax copied; step semantics may differ — warning if `:` present) |
| `-hold_jid` | `--dependency=afterok:id:...` (warning: Slurm uses job IDs; names not supported) |
| `-l` | See built-in / config resource complexes |
| `-pe` | See `parallel_environments` and built-in `omp` / `*_omp` |
| `-soft` / `-hard` | Affects warnings for following options; emitted `#SBATCH` is still “hard” |

Any other **`-`** token is reported as **unsupported** on that line (error).

---

## Body lines (shell)

Handled in [`body.py`](src/sge_to_slurm/body.py). **The config file is not used** for body transformation today.

### Environment variables

Allowlisted **whole-token** replacements of `$VAR` and `${VAR}` outside single-quoted segments:

| SGE-style name | Rewritten to |
|----------------|--------------|
| `JOB_ID` | `${SLURM_JOB_ID}` |
| `JOB_NAME` | `${SLURM_JOB_NAME}` |
| `SGE_TASK_ID` | `${SLURM_ARRAY_TASK_ID}` |
| `SGE_TASK_FIRST` / `LAST` / `STEPSIZE` | `SLURM_ARRAY_TASK_MIN` / `MAX` / `STEP` |
| `NSLOTS` | `${SLURM_CPUS_PER_TASK}` |
| `NHOSTS` | `${SLURM_JOB_NUM_NODES}` |

No `$(...)`, arithmetic expansion, or double-quoted string special-casing beyond the simple single-quote state machine.

### Heredocs

If a line contains `<<`, env substitution is **skipped** for that line and a **warning** is recorded (“heredoc not analyzed”).

### Inline `qsub`

If a non-comment line matches the word `qsub` as a whole word, the line is left unchanged and marked **error** (“submit manually”).

---

## Limitations

- Not a full shell parser; nested quoting, heredocs, and dynamic `qsub` wrappers can confuse or skip rewrites.
- Slurm options and resource meanings are **cluster-dependent**; the tool emits common `#SBATCH` patterns — you must validate on your scheduler.
- Conversion **quality** (yellow/red lines) does **not** change the process exit code.
- **`--encoding`** applies to reading the input; Slurm script content is assembled as Unicode text then encoded the same way on write (no transcoding to another output encoding).

---

## Project layout

| Path | Role |
|------|------|
| [`pyproject.toml`](pyproject.toml) | Package metadata, `sge-to-slurm` console script, pytest and Ruff config, uv `dependency-groups.dev`. |
| [`uv.lock`](uv.lock) | Locked dependency versions for uv. |
| [`src/sge_to_slurm/`](src/sge_to_slurm/) | Application code. |
| [`src/sge_to_slurm/cli.py`](src/sge_to_slurm/cli.py) | Typer CLI, `main()`, `convert` / `version` commands. |
| [`src/sge_to_slurm/config.py`](src/sge_to_slurm/config.py) | Load YAML/TOML → `UserConfig`. |
| [`src/sge_to_slurm/converter.py`](src/sge_to_slurm/converter.py) | Line classification, merge directives, assemble output text. |
| [`src/sge_to_slurm/directives.py`](src/sge_to_slurm/directives.py) | Parse `#$`, merge into `DirectiveState`, emit `#SBATCH` lines. |
| [`src/sge_to_slurm/body.py`](src/sge_to_slurm/body.py) | Body env substitution, `qsub` / heredoc handling. |
| [`src/sge_to_slurm/io_util.py`](src/sge_to_slurm/io_util.py) | Default output path, atomic write, overwrite policy. |
| [`src/sge_to_slurm/models.py`](src/sge_to_slurm/models.py) | `LineStatus`, `LineKind`, `LineReport`, `ConversionResult`. |
| [`src/sge_to_slurm/report.py`](src/sge_to_slurm/report.py) | Rich per-line trace and summary panel. |
| [`sge_to_slurm.example.yaml`](sge_to_slurm.example.yaml) | Example site configuration. |
| [`tests/`](tests/) | Pytest tests and fixtures under `tests/fixtures/sge/`. |
| [`references/`](references/README.md) | Local copies of man pages / wiki-derived docs (not used at runtime). |

---

## Development and tests

```bash
uv sync --group dev
uv run pytest              # all tests
uv run pytest -q tests/test_converter.py
```

Tests cover: golden-style assertions on converted output, MPI PE + partition + account from config, unmapped `-P`, inline `qsub`, heredoc warning, TOML config load, CLI overwrite refusal / `--force`, `--no-write`, and `main()` argv behavior.

---

## References in this repo

Bundled documentation for human comparison (the converter does **not** read these files automatically):

- [`references/README.md`](references/README.md) — index of what each file is.
- [`references/man_qsub.txt`](references/man_qsub.txt) — `qsub` man page from your SCC.
- [`references/sbatch.1`](references/sbatch.1) — Slurm `sbatch` man source.
- [`references/techweb/`](references/techweb/) — Markdown exports of batch / SGE usage pages.

Use them when tuning [`sge_to_slurm.example.yaml`](sge_to_slurm.example.yaml) for your site.
