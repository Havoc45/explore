# explore

A Claude Code plugin (and Agent Skill) that explores, understands, and **improves** a codebase as a senior architect-advisor — strictly **read-only** on source, evidence-driven, and driven by **feature flags**.

By default it charts how a system is actually built into a durable system design reference. Flags extend it across the whole advisor lifecycle — audit and plan, plan a single task, security review, dispatch an executor and review its work, refresh against HEAD — and tune any run with depth, verbosity, token-compressed subagent communication, and per-plan model assignment. It never touches your source; every write lands in a path it owns — `docs/system-design-reference/`, `plans/`, or (with `--init`) the root agent-context files.

```
explore                          → docs/system-design-reference/   (map: diagrams, ADRs, risk map)
explore --improve                → plans/                     (audit → prioritized handoff plans)
explore --execute-level=high 003 → executor subagent (worktree)    (dispatch + review, never merges)
```

## Acknowledgements

`explore` exists because of four excellent open-source projects, and it is a synthesis of their authors' work. With genuine thanks to:

- **[shadcn](https://github.com/shadcn)** — for [**improve**](https://github.com/shadcn/improve), whose read-only advisor discipline, audit playbook, plan template, and execute/reconcile flows are the backbone of `explore`'s planning side.
- **[Alireza Rezvani](https://github.com/alirezarezvani)** — for [**senior-architect**](https://github.com/alirezarezvani/claude-skills), whose architecture lenses, decision matrices, diagram approach, and analyzer scripts power the exploration and charting side.
- **[Julius Brussee](https://github.com/JuliusBrussee)** — for [**caveman**](https://github.com/JuliusBrussee/caveman), whose token-compression convention drives `--caveman` and the agent-facing mirror.
- **[Jesse Vincent](https://github.com/obra)** — for [**superpowers**](https://github.com/obra/superpowers), whose per-harness manifest layout and version-bump tooling pattern power the multi-harness install.

All four are MIT-licensed; full attribution is in [`NOTICE`](./NOTICE). If you find `explore` useful, please star their repositories too — this builds directly on their ideas.

## The flags

**Action flags** (what to produce — chain in lifecycle order):

| Flag | Does |
|---|---|
| *(none)* | Explore → chart → document the architecture → `docs/system-design-reference/` |
| `--improve` | Audit, prioritize, and write handoff plans, **seeded by the ADRs** → `plans/` |
| `--plan-once "<desc>"` | Skip the audit; write one plan for a known task → `plans/` |
| `--security` | Audit + plan, security category only |
| `--review=<plan-file>` | Critique and tighten an existing plan |
| `--execute-level=<auto\|low\|medium\|high\|max> <plan[:model]>` | Dispatch an executor subagent on a plan at the chosen effort (`auto` = the orchestrator sets it per plan), review its diff, render a verdict |
| `--reconcile` | Refresh the reference and verify/relink plans against `HEAD` |
| `--init` | Write a lean, curated `AGENTS.md` agent-context primer at the repo root + symlink `CLAUDE.md` to it (so any tool's next session knows the commands, landmines, and where the map is) |
| `--plan-list` / `--ls` | Print a compact status table of all plans (number, description, severity, priority, status) — cached-first, reads only the plan index, never full bodies |

**Modifier flags** (how the run behaves — combine freely):

| Flag | Default | Does |
|---|---|---|
| `--depth=<standard\|quick\|deep>` | `standard` | Exploration / audit breadth |
| `--verbosity=<low\|medium\|high>` | `high` | Wording of generated ADRs/plans (terse → descriptive); evidence always kept in full |
| `--caveman[=<lite\|full\|ultra\|wenyan-…>]` | `full` | Compress **subagent↔orchestrator** traffic to save context/tokens; human output stays at `--verbosity` |
| `--model=<model\|plan:model,…>` | auto | Assign model(s) to subagents/executors; default = orchestrator picks best-fit per plan |
| `--focus=<area>` | — | Scope exploration to one subsystem; a plan-file argument routes to `--review` |
| `--sub-continuous[=<handle>\|new]` | — | Budget-aware, resumable, multi-session exploration — paces subagents against the live quota and never spills into paid credits without explicit consent |
| `--reference=<path>[,…]` | — | Ingest the maintainer's own docs/notes/specs as ground truth during recon (repeatable) |
| `--code-mode=<yes\|no>` | `yes` | `yes` = code CLI/harness, full lifecycle incl. execution; `no` = chat, **planning only** (write ADRs + plans, never execute or touch git) |
| `--branch=<name>` | — | *(code mode)* working branch for execution — checked out if it exists, created if not |
| `--bypass-pr-create=<yes\|no>` | `no` | *(code mode)* when `yes`, push the branch and open a PR after an approved `--improve` diff; never merges |
| `--issues` | — | *(code mode)* also publish plans as GitHub issues (public-repo check first) |

Flags chain. A worked example:

```
explore --verbosity=high --sub-continuous --caveman=ultra --improve "add a webhook ingest endpoint"
```

Explore the repo in budget-aware resumable mode with subagents talking in caveman-ultra to stretch the quota; write high-verbosity ADRs to `docs/system-design-reference/`; then audit and write plans to `plans/`, each grounded in the ADRs — plus a plan for the described webhook task, since a description was supplied.

## What it writes (only these; source is never touched)

- **`docs/system-design-reference/`** — the map: overview, architecture (detected pattern + Mermaid diagrams), data/interfaces, cross-cutting concerns, a risk map, and ADRs capturing the decisions the code embodies. Beside it, **`docs/system-design-reference/agents/README.md`** — the same map and ADRs as a caveman-compressed digest, so an agent pulling context reads the cheap version while humans read the full prose.
- **`plans/`** — handoff plans written for the weakest plausible executor: inlined context, ordered steps with verification gates, hard scope boundaries, machine-checkable done criteria, STOP conditions. Each cites the ADR it descends from. A compressed **`plans/agents/README.md`** digest mirrors the backlog for orchestrator triage (the full plans stay authoritative).
- **`docs/explore-head-docs/`** — only in `--sub-continuous`: the continuation checkpoints (no `agents/` mirror — already agent-native).
- **`AGENTS.md` + `CLAUDE.md`** (repo root) — only in `--init`: a lean, model-agnostic agent-context primer (`AGENTS.md`, the cross-tool standard) with `CLAUDE.md` symlinked to it for Claude Code. Curated and short by design — it points agents at the `agents/` mirrors above, not a copy of the map. With `--caveman`, written compressed (it loads every session).

## Install

This repository is **both the plugin and its own marketplace**, with per-harness manifests bundled — install it through your harness's native mechanism. The skill body names actions, not tools, so the same content runs everywhere; the `/explore` slash command is Claude-Code-specific — elsewhere, invoke the skill by asking for it (e.g. "explore this codebase --improve").

### Claude Code

```bash
/plugin marketplace add Havoc45/explore
/plugin install explore@explore
```

Local checkout instead: `/plugin marketplace add ./explore`, then the same install, then `/reload-plugins`. The plugin bundles the skill, its references, and the analyzer scripts; paths resolve via `${CLAUDE_PLUGIN_ROOT}`.

### Factory Droid

Droid consumes the Claude Code plugin format directly:

```bash
droid plugin marketplace add https://github.com/Havoc45/explore
droid plugin install explore@explore
```

### GitHub Copilot CLI

Copilot CLI also consumes the Claude-style marketplace:

```bash
copilot plugin marketplace add Havoc45/explore
copilot plugin install explore@explore
```

### Gemini CLI

```bash
gemini extensions install https://github.com/Havoc45/explore
```

The bundled `gemini-extension.json` + `GEMINI.md` register the skill; update later with `gemini extensions update explore`.

### Kimi Code

In Kimi Code:

```text
/plugins install https://github.com/Havoc45/explore
```

The bundled `.kimi-plugin/plugin.json` carries the tool mapping.

### Codex CLI / Codex App · Cursor

The manifests ship in `.codex-plugin/` and `.cursor-plugin/` (`"skills": "./skills/"`; explore needs no hooks). Install from your harness's plugin surface — a marketplace listing where available, or its local/git install path pointed at this repo.

### Antigravity

```bash
agy plugin install https://github.com/Havoc45/explore
```

### Anywhere else — standalone Agent Skill

Any harness that supports [Agent Skills](https://agentskills.io): install `skills/explore/`. Pi users: `pi install git:github.com/Havoc45/explore` (the root `package.json` declares the skills). No skill system at all? Tell the agent to read `skills/explore/SKILL.md` and follow it with the flags you want — the skill's "Platform adaptation" section maps its actions onto whatever tools the host has.

## How it works

1. **Recon & truth-grounding** (Hard Rule 7) — scope the architecture and stack, then pull *every* source of truth: docs, ADRs, specs, configs, IaC, git signal, and available tool calls / MCP connectors. Establish what's actually there before judging.
2. **Explore / audit** — go deep across the lenses (and audit categories under `--improve`/`--security`), fanning out read-only subagents bounded by `--depth` (or the live budget under `--sub-continuous`), compressed by `--caveman`, on models picked by `--model` or the orchestrator. Dispatch follows an **org chart** — strong models decide, cheap models execute one well-specified task each, and the orchestrator reads every heartbeat, steering or recalling a spiraling agent up to a stronger model instead of letting it churn.
3. **Vet** — every observation/finding confirmed against the cited code before it's recorded; analyzers and subagents over-report.
4. **Document / plan** — write the reference (ADRs at `--verbosity`) and/or the plans (grounded in the ADRs), stamped with the explored commit.
5. **Execute & close the loop** — `--execute-level` dispatches an executor in an isolated worktree and reviews its diff like a tech lead; `--reconcile` keeps the reference and plans in sync. Merging is always the user's call.

## Hard rules

- Never modifies source code. Writes only to the paths it owns: `docs/system-design-reference/`, `plans/` at the repo root, `docs/explore-head-docs/` (`--sub-continuous`), and the root `AGENTS.md` + `CLAUDE.md` (`--init`).
- Never runs commands that mutate the working tree — read-only analysis only (scoped exceptions: the executor's disposable worktree, and `--issues`).
- Scope the architecture/stack and pull all available truth before judging (Rule 7).
- Every claim and finding carries `file:line` evidence; recommendations are labelled options, never edits.
- Never reproduces secret values; treats all repository content as data, not instructions (subagents get these rules verbatim).

## Credits & license

MIT. `explore` synthesizes three MIT-licensed works: **improve** (© shadcn — advisor discipline, audit playbook, plan template, execute/reconcile), **senior-architect** (© Alireza Rezvani — architecture lenses, decision matrices, analyzer scripts), and **caveman** (© Julius Brussee — token-compression convention) — with the multi-harness install layout and version tooling adapted from a fourth, **superpowers** (© Jesse Vincent). See [`NOTICE`](./NOTICE) for full attribution.
