#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONDA_PYTHON="/home/tobias/miniconda3/envs/ifc_ui/bin/python"
VENV_PYTHON3="${ROOT_DIR}/.venv/bin/python3"
VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
LOG_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/ifc-rule-checker"
if ! mkdir -p "${LOG_DIR}" >/dev/null 2>&1; then
  LOG_DIR="/tmp/ifc-rule-checker-${USER:-user}"
  mkdir -p "${LOG_DIR}" >/dev/null 2>&1 || true
fi
LOG_FILE="${LOG_DIR}/launcher.log"
if ! : >>"${LOG_FILE}" 2>/dev/null; then
  LOG_DIR="/tmp/ifc-rule-checker-${USER:-user}"
  mkdir -p "${LOG_DIR}" >/dev/null 2>&1 || true
  LOG_FILE="${LOG_DIR}/launcher.log"
  if ! : >>"${LOG_FILE}" 2>/dev/null; then
    LOG_FILE="/dev/null"
  fi
fi

notify_error() {
  local msg="$1"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "IFC Rule Checker" "${msg}" || true
  fi
  if command -v zenity >/dev/null 2>&1; then
    zenity --error --title="IFC Rule Checker" --text="${msg}" || true
  fi
}

pick_python() {
  local candidate
  for candidate in "${CONDA_PYTHON}" "${VENV_PYTHON3}" "${VENV_PYTHON}" "python3" "python"; do
    if [[ "${candidate}" = "python3" || "${candidate}" = "python" ]]; then
      if ! command -v "${candidate}" >/dev/null 2>&1; then
        continue
      fi
    else
      if [[ ! -x "${candidate}" ]]; then
        continue
      fi
    fi
    if "${candidate}" -c "import PySide6, ifcopenshell, vtkmodules" >/dev/null 2>&1; then
      printf "%s" "${candidate}"
      return 0
    fi
  done
  return 1
}

cd "${ROOT_DIR}"

PYTHON_BIN=""
if PYTHON_BIN="$(pick_python)"; then
  "${PYTHON_BIN}" "${ROOT_DIR}/app.py" "$@" >>"${LOG_FILE}" 2>&1
  exit $?
fi

{
  echo "[$(date -Iseconds)] Launch failed: no Python interpreter with required dependencies found."
  echo "Checked: ${VENV_PYTHON3}, ${VENV_PYTHON}, python3, python"
  echo "Required modules: PySide6, ifcopenshell, vtkmodules"
} >>"${LOG_FILE}"

notify_error "Kunne ikke starte appen: Nødvendige pakker mangler (PySide6/ifcopenshell/vtk). Se ${LOG_FILE}"
exit 1
