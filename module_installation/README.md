# SCC module install (`sgeconvert`)

This directory holds the **Environment Modules** template (`modulefile.lua`) and a **one-shot installer** for publishing `sge-to-slurm` on the SCC shared package tree (`/share/pkg.8/...`).

## Layout (after install)

From the package version directory (example: `/share/pkg.8/sgeconvert/0.1.0/`):

| Path | Purpose |
|------|---------|
| `src/sge-to-slurm/` | Git clone of this project (updated on each run) |
| `install/.venv/` | Dedicated virtualenv with runtime dependencies |
| `install/bin/sge-to-slurm` | Wrapper that runs the venv CLI (on `PATH` when the module loads) |
| `modulefile.lua` | Copy of `module_installation/modulefile.lua` for that version (edit version strings before release) |
| `sge_to_slurm.scc.yaml` | SCC default mapping config copied from the repo root |

The Lua modulefile sets `SCC_SGECONVERT_*` and prepends `install/bin` to `PATH`, matching the paths above.
It also sets `SGE_TO_SLURM_CONFIG=$SCC_SGECONVERT_BASE/sge_to_slurm.scc.yaml`, so `sge-to-slurm` uses that config by default when `--config` is omitted.

The installer also creates a symlink **`/share/module.8/utilities/sgeconvert/{version}.lua`** → **`modulefile.lua`** when that utilities directory exists and is writable. Here `{version}` is the last path component of your package directory (for example `1.0` when you run the script from `/share/pkg.8/sgeconvert/1.0`), or the value of `SCC_SGECONVERT_VERSION` if you set it. That matches a manual:

```bash
cd /share/module.8/utilities/sgeconvert
ln -sf /share/pkg.8/sgeconvert/1.0/modulefile.lua 1.0.lua
```

The file next to `install/` on the package tree is always named **`modulefile.lua`**.

## One-time manual steps (new version)

Run these on SCC **before** the automated script:

```bash
cd /share/pkg.8
ls sgeconvert/
module load newpkg
newpkg
```

Use `newpkg` to create a new **sgeconvert** version directory. Then:

```bash
cd /share/pkg.8/sgeconvert/<new-version>/
```

Replace `<new-version>` with the directory name you chose (it should match what you put in `modulefile.lua` and in this repo’s version metadata — see [Version bumps when releasing](#version-bumps-when-releasing)).

## Automated install / update

1. Load a suitable Python (project requires **3.11+**), for example:

   ```bash
   module load python3/3.12.4
   ```

2. From the **new package version directory** (the parent of `install/` and `src/`):

   ```bash
   export SCC_SGECONVERT_PKG_ROOT="$PWD"   # optional if your shell is already there
   bash /path/to/sge-to-slurm/module_installation/install_scc_module.sh
   ```

   If you already copied this repo onto SCC, use the real path to `install_scc_module.sh` inside your clone.

**Do not `source` this script** — execute it with `bash` so `set -euo pipefail` and exits behave correctly.

### Environment variables (optional)

| Variable | Default | Meaning |
|----------|---------|---------|
| `SCC_SGECONVERT_PKG_ROOT` | `$PWD` | Root of this module version (contains `install/`, `src/`) |
| `SGE_TO_SLURM_REPO` | `https://github.com/Ryan-J-Gilbert/sge-to-slurm.git` | Git remote |
| `SGE_TO_SLURM_REF` | `main` | Branch or tag to deploy |
| `SGE_TO_SLURM_PYTHON` | `python3` | Interpreter used to create the venv |
| `SCC_SGECONVERT_VERSION` | *(unset)* | Version label for the utilities symlink (e.g. `1.0.lua`); default is the **basename** of `SCC_SGECONVERT_PKG_ROOT` |
| `SCC_SGECONVERT_UTILITIES_DIR` | `/share/module.8/utilities/sgeconvert` | Directory where `{version}.lua` is created |
| `SCC_SGECONVERT_SKIP_UTILITIES_SYMLINK` | *(unset)* | If non-empty, skip creating the utilities symlink (e.g. local dry run) |

## What the script does

1. Ensures `src/` and `install/bin/` exist under `SCC_SGECONVERT_PKG_ROOT`.
2. Clones or **git pull** updates `src/sge-to-slurm`.
3. Creates `install/.venv` if missing, then `pip install --upgrade` the clone (installs the `sge-to-slurm` console script into the venv).
4. Writes `install/bin/sge-to-slurm` as a small `exec` wrapper around `.venv/bin/sge-to-slurm` (so users do not rely on activating the venv).
5. Copies `module_installation/modulefile.lua` **from the checked-out clone** to `modulefile.lua` next to `install/` (so the template matches the deployed Git revision).
6. Copies `sge_to_slurm.scc.yaml` from the checked-out clone to the package root as the module default config.
7. Symlinks **`utilities_dir/{version}.lua`** → **`modulefile.lua`** (absolute target), with `{version}` from `SCC_SGECONVERT_VERSION` or the basename of the package directory. Requires step 5 to have produced `modulefile.lua` and the utilities directory to exist and be writable (otherwise the script prints the exact `ln -sf` to run by hand).

## Version bumps when releasing

When you tag or publish a new release, keep these **in sync**:

1. [`pyproject.toml`](../pyproject.toml) — `project.version`
2. [`src/sge_to_slurm/__init__.py`](../src/sge_to_slurm/__init__.py) — `__version__`
3. [`module_installation/modulefile.lua`](modulefile.lua) — `help([[...]])` first line and any other user-visible version text; ensure `myModuleVersion()` in the real SCC modulefile matches the directory name under `/share/pkg.8/sgeconvert/`.

After editing files in the repo, re-run `install_scc_module.sh` on SCC (or bump `SGE_TO_SLURM_REF` to a tag) so `src/sge-to-slurm` and the venv pick up the change.

## Venv vs copying `bin`

The installer uses **`pip install` into `install/.venv`** instead of copying the repository into `install/bin`. That satisfies `pyproject.toml` dependencies (Typer, Rich, PyYAML) in one place and keeps `install/bin` limited to small launchers.

If anything fails, check that the Python module is loaded, you have network access for `git clone`/`pip`, and `SCC_SGECONVERT_PKG_ROOT` points at the **version directory**, not the inner `install/` folder.
