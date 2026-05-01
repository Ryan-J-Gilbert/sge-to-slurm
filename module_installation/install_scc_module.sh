#!/usr/bin/env bash
# Install or refresh sge-to-slurm under an SCC-style package tree (sgeconvert/<version>/).
#
# Typical use (after newpkg, from the new version directory):
#   module load python3/3.12.4
#   export SCC_SGECONVERT_PKG_ROOT="$PWD"   # optional if you already cd'd there
#   bash /path/to/sge-to-slurm/module_installation/install_scc_module.sh
#
# This script is NOT intended to be sourced; run it with bash. It mutates the tree under
# SCC_SGECONVERT_PKG_ROOT (default: current directory).

set -euo pipefail

REPO_DEFAULT="https://github.com/Ryan-J-Gilbert/sge-to-slurm.git"

: "${SCC_SGECONVERT_PKG_ROOT:=$(pwd)}"
: "${SGE_TO_SLURM_REPO:=${REPO_DEFAULT}}"
: "${SGE_TO_SLURM_REF:=main}"
: "${SGE_TO_SLURM_PYTHON:=python3}"
: "${SCC_SGECONVERT_UTILITIES_DIR:=/share/module.8/utilities/sgeconvert}"

PKG_ROOT="$(cd "${SCC_SGECONVERT_PKG_ROOT}" && pwd)"
SRC_PARENT="${PKG_ROOT}/src"
CLONE_DIR="${SRC_PARENT}/sge-to-slurm"
INSTALL_ROOT="${PKG_ROOT}/install"
VENV_DIR="${INSTALL_ROOT}/.venv"
BIN_DIR="${INSTALL_ROOT}/bin"
MODULEFILE_DST="${PKG_ROOT}/modulefile.lua"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if [[ ! -d "${PKG_ROOT}" ]]; then
  die "SCC_SGECONVERT_PKG_ROOT is not a directory: ${PKG_ROOT}"
fi

if ! command -v git >/dev/null 2>&1; then
  die "git is not on PATH"
fi

if ! command -v "${SGE_TO_SLURM_PYTHON}" >/dev/null 2>&1; then
  die "Python not found: ${SGE_TO_SLURM_PYTHON} (load a python module, e.g. module load python3/3.12.4)"
fi

if ! "${SGE_TO_SLURM_PYTHON}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
  die "Need Python >= 3.11 (project requires-python); got ${SGE_TO_SLURM_PYTHON} ($(command -v "${SGE_TO_SLURM_PYTHON}"))"
fi

mkdir -p "${SRC_PARENT}" "${BIN_DIR}"

if [[ -d "${CLONE_DIR}/.git" ]]; then
  log "Updating existing clone: ${CLONE_DIR}"
  git -C "${CLONE_DIR}" fetch --tags origin
  git -C "${CLONE_DIR}" checkout "${SGE_TO_SLURM_REF}"
  git -C "${CLONE_DIR}" pull --ff-only origin "${SGE_TO_SLURM_REF}" || \
    git -C "${CLONE_DIR}" pull --ff-only
else
  if [[ -e "${CLONE_DIR}" ]]; then
    die "Path exists but is not a git repo: ${CLONE_DIR}"
  fi
  log "Cloning ${SGE_TO_SLURM_REPO} (ref: ${SGE_TO_SLURM_REF}) -> ${CLONE_DIR}"
  git clone --branch "${SGE_TO_SLURM_REF}" "${SGE_TO_SLURM_REPO}" "${CLONE_DIR}" || \
    git clone "${SGE_TO_SLURM_REPO}" "${CLONE_DIR}"
  git -C "${CLONE_DIR}" checkout "${SGE_TO_SLURM_REF}"
fi

if [[ ! -f "${CLONE_DIR}/pyproject.toml" ]]; then
  die "Clone missing pyproject.toml: ${CLONE_DIR}"
fi

MODULEFILE_SRC="${CLONE_DIR}/module_installation/modulefile.lua"

if [[ ! -d "${VENV_DIR}" ]]; then
  log "Creating venv: ${VENV_DIR}"
  "${SGE_TO_SLURM_PYTHON}" -m venv "${VENV_DIR}"
fi

PIP=( "${VENV_DIR}/bin/pip" )
if [[ ! -x "${PIP[0]}" ]]; then
  die "pip not found in venv: ${PIP[0]}"
fi

log "Upgrading pip and installing sge-to-slurm (editable-style path install)"
"${PIP[@]}" install --upgrade pip
"${PIP[@]}" install --upgrade "${CLONE_DIR}"

WRAPPER="${BIN_DIR}/sge-to-slurm"
VENV_CLI="${VENV_DIR}/bin/sge-to-slurm"
if [[ ! -x "${VENV_CLI}" ]]; then
  die "Console script missing after install: ${VENV_CLI}"
fi

# Prefer a tiny wrapper so PATH resolution is obvious and symlinks are not required.
cat > "${WRAPPER}" <<EOF
#!/usr/bin/env bash
exec "${VENV_CLI}" "\$@"
EOF
chmod +x "${WRAPPER}"

if [[ -f "${MODULEFILE_SRC}" ]]; then
  cp -f "${MODULEFILE_SRC}" "${MODULEFILE_DST}"
  log "Installed modulefile template: ${MODULEFILE_DST}"
else
  log "WARN: module template missing, skipped copy: ${MODULEFILE_SRC}"
fi

if [[ -n "${SCC_SGECONVERT_VERSION:-}" ]]; then
  MODULE_VER="${SCC_SGECONVERT_VERSION}"
else
  MODULE_VER="$(basename "${PKG_ROOT}")"
fi
if [[ -z "${MODULE_VER}" || "${MODULE_VER}" == "/" ]]; then
  die "Could not derive module version (basename of SCC_SGECONVERT_PKG_ROOT); set SCC_SGECONVERT_VERSION explicitly"
fi

UTIL_LINK="${SCC_SGECONVERT_UTILITIES_DIR}/${MODULE_VER}.lua"
if [[ -n "${SCC_SGECONVERT_SKIP_UTILITIES_SYMLINK:-}" ]]; then
  log "Skipping utilities symlink (SCC_SGECONVERT_SKIP_UTILITIES_SYMLINK is set)."
elif [[ ! -f "${MODULEFILE_DST}" ]]; then
  log "WARN: no ${MODULEFILE_DST}; not creating utilities symlink."
else
  if [[ -d "${SCC_SGECONVERT_UTILITIES_DIR}" && -w "${SCC_SGECONVERT_UTILITIES_DIR}" ]]; then
    ln -sf "${MODULEFILE_DST}" "${UTIL_LINK}"
    log "Utilities module symlink: ${UTIL_LINK} -> ${MODULEFILE_DST}"
  else
    log "WARN: cannot write utilities symlink (missing dir or no permission): ${SCC_SGECONVERT_UTILITIES_DIR}"
    log "Run manually (version=${MODULE_VER}):"
    log "  ln -sf ${MODULEFILE_DST} ${UTIL_LINK}"
  fi
fi

log "Done."
log "  CLI:        ${WRAPPER}"
log "  Python:     ${VENV_DIR}/bin/python"
log "  Modulefile: ${MODULEFILE_DST}"
log "  Version:    ${MODULE_VER} (set SCC_SGECONVERT_VERSION to override basename of package dir)"
log "Ensure modulefile.lua myModuleVersion() matches this directory name and help() text before publishing."
