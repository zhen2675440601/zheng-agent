# Cross-device Development and GitHub Handoff Notes

## Current repository state

This project is still in the design stage.

Current committed-worthy files are:
- `CLAUDE.md`
- `docs/specs/agent-harness-design-notes.md`
- `docs/specs/agent-harness-v0.1-harness-first-architecture.md`
- `docs/specs/agent-harness-v0.1-contract-definitions.md`
- `docs/specs/agent-harness-v0.1-state-machine.md`
- `.claude/settings.json`

Current machine-local file that should usually stay local:
- `.claude/settings.local.json`

## Recommended Git strategy

For cross-device development, commit project-level collaboration files, but do not rely on machine-local Claude settings being portable.

Recommended:
- commit `.claude/settings.json`
- do not commit `.claude/settings.local.json`
- add a `.gitignore` entry for `.claude/settings.local.json`

Why:
- `.claude/settings.json` contains project-wide hooks and shared Claude behavior
- `.claude/settings.local.json` contains personal local overrides and may differ across machines

## Recommended first push contents

The first GitHub push should contain only the shared design baseline and shared Claude project config:
- design specs under `docs/specs/`
- `CLAUDE.md`
- `.claude/settings.json`

This keeps the repository clean and makes a second machine able to resume with the same repository-level context.

## What to do on the next computer

After cloning on another computer:
1. verify Claude Code is installed
2. verify the repository-level hooks from `.claude/settings.json` are loaded
3. if hooks do not appear immediately, open `/hooks` once or restart Claude Code
4. create a fresh local `.claude/settings.local.json` only if that machine needs personal overrides
5. make sure `jq` is available in the shell PATH if you want shell-based hook validation to work without absolute paths

## PATH note for jq on this machine

`jq` is installed on the current machine, but it was not available on the current bash PATH during validation.

Observed path:
- `C:/Users/seato/AppData/Local/Microsoft/WinGet/Packages/jqlang.jq_Microsoft.Winget.Source_8wekyb3d8bbwe/jq.exe`

Implication:
- repository config is valid
- future shell commands that assume plain `jq` may fail unless PATH is fixed on each machine

## GitHub publication checklist

Before pushing to GitHub:
- initialize git if this directory is still not a git repository
- create `.gitignore`
- ignore `.claude/settings.local.json`
- review `.claude/settings.json` and confirm its hooks are intended to be team-shared
- review docs for any machine-specific absolute paths or personal notes
- create the first commit with the design baseline
- add the GitHub remote
- push the branch

## Suggested .gitignore minimum

Suggested minimum entries:

```gitignore
.claude/settings.local.json
```

You can expand this later once real build artifacts exist.

## Collaboration guidance

At this stage, the repository source of truth is still the design material. When switching devices, keep these aligned:
- `docs/specs/`
- `CLAUDE.md`
- `.claude/settings.json`

If architecture or working rules change, update those three areas together so the next machine and the next Claude session inherit the same context.
