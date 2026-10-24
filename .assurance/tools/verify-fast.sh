#!/usr/bin/env bash
# Verifier tier entrypoint. Installed as .assurance/tools/verify-fast.sh, verify.sh, and so on;
# the tier is the file name. Local runs and CI call this same file.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
name="${BASH_SOURCE[0]##*/}"
tier="${name%.sh}"

if [[ -n "${PYTHON:-}" ]]; then python_bin="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then python_bin="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then python_bin="$(command -v python)"
else printf '%s\n' 'ERROR: Python 3.9 or newer is required; set PYTHON to its executable path.' >&2; exit 127
fi

exec "$python_bin" "${script_dir}/run_verifier.py" --tier "$tier" --root "${script_dir}/../.." "$@"
