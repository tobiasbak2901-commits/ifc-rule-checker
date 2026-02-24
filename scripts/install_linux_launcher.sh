#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
APPS_DIR="${DATA_HOME}/applications"
ICON_DIR="${DATA_HOME}/icons/hicolor/scalable/apps"
DESKTOP_FILE="${APPS_DIR}/ifc-rule-checker.desktop"
ICON_NAME="ifc-rule-checker"
LAUNCHER_SCRIPT="${ROOT_DIR}/scripts/run_ifc_rule_checker.sh"
ICON_SOURCE="${ROOT_DIR}/assets/branding/ponker_icon_square.svg"
ICON_TARGET="${ICON_DIR}/${ICON_NAME}.svg"

if [[ ! -f "${ICON_SOURCE}" ]]; then
  echo "Mangler ikonfil: ${ICON_SOURCE}" >&2
  exit 1
fi

mkdir -p "${APPS_DIR}" "${ICON_DIR}"
cp "${ICON_SOURCE}" "${ICON_TARGET}"
chmod 644 "${ICON_TARGET}"
chmod +x "${LAUNCHER_SCRIPT}"

cat > "${DESKTOP_FILE}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=IFC Rule Checker
Comment=Open IFC Rule Checker
Exec=${LAUNCHER_SCRIPT} %u
Path=${ROOT_DIR}
Icon=${ICON_NAME}
Terminal=false
Categories=Utility;Development;
StartupNotify=true
StartupWMClass=ifc-rule-checker
EOF

chmod 644 "${DESKTOP_FILE}"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${APPS_DIR}" >/dev/null 2>&1 || true
fi
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 >/dev/null 2>&1 || true
fi

echo "Launcher installeret: ${DESKTOP_FILE}"
echo "Søg efter 'IFC Rule Checker' i app-menuen, start appen, og pin den til startlinjen."
