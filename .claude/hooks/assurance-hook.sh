#!/usr/bin/env bash
# Claude Code hook entrypoint (general-prompts Claude Code adapter). Usage: assurance-hook.sh <event>
# Finds a working Python 3.9+ (the Windows Store "python3" alias is skipped) and runs assurance_hooks.py.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
for candidate in "${PYTHON:-}" python3 python; do
  [[ -n "$candidate" ]] || continue
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' >/dev/null 2>&1; then
    exec "$candidate" "${script_dir}/assurance_hooks.py" "$@"
  fi
done
printf '%s\n' 'assurance hook: Python 3.9 or newer was not found; set PYTHON' >&2
exit 1
