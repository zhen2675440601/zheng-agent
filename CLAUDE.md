# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository status

This repository is currently in the design stage. There is no application code yet; the existing source of truth is the design material under `docs/specs/`.

Current design docs:
- `docs/specs/agent-harness-design-notes.md`
- `docs/specs/agent-harness-v0.1-harness-first-architecture.md`
- `docs/specs/agent-harness-v0.1-contract-definitions.md`
- `docs/specs/agent-harness-v0.1-state-machine.md`

When implementing, treat those documents as the active product and architecture baseline unless the user explicitly changes direction.

## Repository rules and hooks

Project Claude hooks are defined in `.claude/settings.json`.

Current project hooks:
- `SessionStart` posts a reminder that this is a design-stage repository and that `CLAUDE.md` plus `docs/specs/` are the source of truth before implementation.
- `PostToolUse` on `Write|Edit` injects lightweight context to keep `docs/specs/` and `CLAUDE.md` aligned when repository-level guidance changes.

Git ignore rules currently include:
- `.claude/settings.local.json` is ignored as a machine-local personal override.

No blocking, formatting, test, or command-running hooks are configured yet.

## Common commands

Initialize environment:
- `python -m pip install -e .[dev]`

Run unit tests:
- `pytest -q`

Run a single test:
- `pytest tests/runtime/test_engine.py::test_engine_completes_run_with_action -q`

There is no local CLI or web UI yet.

Current concrete package layout starts under `src/zheng_agent/core/`.

## Architecture overview

The project is intended to be a harness-first agent execution system rather than a generic agent framework.

The architectural center is not the agent itself. The core system revolves around:
- contracts
- run lifecycle
- state machine
- action gateway
- trace
- evaluation
- replay

### Core design principles

#### Contract-first
All execution must be governed by explicit contracts:
- Task Contract
- Agent Decision Contract
- Action Contract
- Result Contract
- Eval Contract

Agent behavior should be treated as structured, contract-bound decision making, not freeform tool orchestration.

#### Controlled execution boundaries
Two boundaries are first-class in v0.1:
- tools/actions are invoked only through an Action Gateway
- run and step progression must go through an explicit state machine

An agent should not directly call tools, mutate run state, or bypass the harness to produce side effects.

#### Verifiability over convenience
The current v0.1 success criterion is verifiability. The goal is not just to run agents, but to make runs inspectable, evaluable, and comparable.

## Planned module shape

The current architecture docs propose a Python-first core with modules shaped roughly like:

```text
core/
  contracts/
  state_machine/
  runtime/
  action_gateway/
  tracing/
  evaluation/
  replay/
  agent/
```

Important dependency direction:
- `runtime` depends on `contracts`, `state_machine`, `action_gateway`, and `tracing`
- `evaluation` depends on `contracts` and `tracing`
- `replay` depends on `tracing`, `runtime`, and `contracts`
- `agent` depends on `contracts`

Avoid reversing these dependencies. In particular:
- `contracts` should not depend on execution modules
- `tracing` should not depend on concrete agent implementations
- `agent` should not depend on runtime internals

## Key domain objects

Based on the current specs, future code will likely center around these objects:
- `TaskSpec`
- `Run`
- `StepAttempt`
- `AgentDecision`
- `ActionRequest`
- `ActionResult`
- `RunResult`
- `EvalResult`

If implementation diverges from these names, preserve the same boundaries and responsibilities.

## State model

The current design defines explicit run and step state machines.

Run states:
- `created`
- `validated`
- `ready`
- `running`
- `waiting_action`
- `paused`
- `completed`
- `failed`
- `cancelled`

Step states:
- `pending`
- `ready`
- `running`
- `waiting_action`
- `completed`
- `failed`

State transitions should be event-driven and explicit. Do not encode hidden status changes in ad hoc control flow.

## Implementation guidance

When starting implementation work in this repository:
1. Read the docs in `docs/specs/` first.
2. Preserve the harness-first model; do not drift into a generic plugin-first agent framework.
3. Freeze and implement contracts, state machine transitions, and trace schemas before building higher-level orchestration.
4. Treat Action Gateway mediation as mandatory for external actions.
5. Keep trace and evaluation as first-class runtime outputs, not optional debugging add-ons.

## Current priority order

The design docs imply this implementation order:
1. contracts
2. state machine
3. runtime skeleton
4. action gateway
5. trace store and event schema
6. evaluation interface
7. replay
8. CLI and examples
9. web trace viewer

## Notes for future updates

Once the repository has actual code, expand this file with:
- the concrete package layout
- exact development commands
- testing entry points
- any project-specific conventions discovered during implementation
