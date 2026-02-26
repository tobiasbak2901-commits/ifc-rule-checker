#!/usr/bin/env bash
# Start IFC Rule Checker using the miniconda ifc_ui environment.
# Usage:
#   ./run.sh            — launch the application
#   ./run.sh --doctor   — check runtime dependencies without opening the window
set -e
cd "$(dirname "$0")"
exec /home/tobias/miniconda3/envs/ifc_ui/bin/python app.py "$@"
