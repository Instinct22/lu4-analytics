#!/bin/bash
# Совместимость: используйте корневой start.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/start.sh" "$@"
