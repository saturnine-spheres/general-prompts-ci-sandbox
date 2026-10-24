#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
root="${script_dir%/tools}"
report="${root}/validation-report.json"

while (($#)); do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || { printf '%s\n' 'ERROR: --root requires a value' >&2; exit 2; }
      root="$2"
      shift 2
      ;;
    --report)
      [[ $# -ge 2 ]] || { printf '%s\n' 'ERROR: --report requires a value' >&2; exit 2; }
      report="$2"
      shift 2
      ;;
    -h|--help)
      printf 'Usage: %s [--root PATH] [--report PATH]\n' "${0##*/}"
      exit 0
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
done

if [[ -n "${PYTHON:-}" ]]; then
  python_bin="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
  python_bin="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  python_bin="$(command -v python)"
else
  printf '%s\n' 'ERROR: Python 3.10 or newer is required; set PYTHON to its executable path.' >&2
  exit 127
fi

exec "$python_bin" "${script_dir}/validate_artifacts.py" --root "$root" --report "$report"
