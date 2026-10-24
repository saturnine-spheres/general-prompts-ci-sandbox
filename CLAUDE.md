# Claude Code instructions

Claude Code reads this file instead of `AGENTS.md`, so it imports the repository's operating instructions and the generated agent pack:

@AGENTS.md
@.assurance/agent-pack.md

Use `/deliver <specification, file, or issue reference>` to take a specification to a pull or merge request through the process in `.assurance/process.json`. The hooks in `.claude/settings.json` run `verify-fast` after edits and refuse commits and finishing while the repository's rules or gates fail; the CI evidence gate decides at merge.
