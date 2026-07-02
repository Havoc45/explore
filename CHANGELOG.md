# Changelog

All notable changes to the `explore` plugin. This project adheres to
[Semantic Versioning](https://semver.org/) and the spirit of
[Keep a Changelog](https://keepachangelog.com/).

## [2.7.0] — 2026-07-02

### Added
- **`--execute-level=auto`** — the orchestrator sets the executor's reasoning effort per
  plan, with the same judgment as the model auto-pick: mechanical, well-specified work →
  `low`/`medium`; cross-cutting refactors, security, ambiguous specs → `high`/`max`. The
  chosen model *and* effort are stated per plan for reproducibility.
- **Delegation & oversight — the org chart** (new SKILL.md section +
  `references/delegation.md`). Every dispatch follows one hierarchy: the CEO (orchestrator,
  strongest model) holds the end goal and all judgment; managers (strong models) own
  long-horizon subtasks on `deep`/monorepo/campaign runs; workers (cheap, fast models) get
  one self-contained task each with the raise-hand rule. Capability economics made explicit
  (weak models execute, strong models decide — the $100/h senior beats the $10/h junior on
  reasoning), with **spiral detection** (signals: re-reads, restating check-ins, unmoved
  progress map), an **escalation ladder** (narrow-once → escalate the *decision* to a
  stronger model at low effort → re-dispatch → CEO takes it), and a **steering protocol**
  (heartbeats read on every interim signal; narrow/redirect/reassign/escalate/stop, durably
  recorded). The `--execute-level` REVISE loop now escalates a spiraling executor instead
  of burning the second revision round.
- **`--sub-continuous` pacing: the throttle ladder & the credits guard.** The budget is
  re-read after *every* unit (not just the first), the burn rate re-projected, and
  concurrency stepped down in one-way rungs (full fan-out → halve → single-file → drain →
  checkpoint) instead of hitting the reserve cliff. "Pause" always means *drain* — in-flight
  subagents finish their unit rather than being killed mid-way. When the included quota is
  exhausted and the plan would spill into paid overage credits, the session drains,
  checkpoints, reports the reset time, and stops — continuing on credits requires the
  user's explicit same-session consent, and credits are never counted as headroom.
- **Multi-harness installability** (patterned on obra/superpowers). Per-harness manifests:
  `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.kimi-plugin/plugin.json`
  (with a Kimi tool mapping), `gemini-extension.json` + `GEMINI.md` (extension-declared
  context pointer), and a root `package.json` declaring the skills for pi. A new
  **Platform adaptation** SKILL.md section states the actions-not-tools rule and the
  specified degradations. README gains per-harness install docs (Claude Code, Factory
  Droid, Copilot CLI, Gemini CLI, Kimi Code, Codex/Cursor, Antigravity, pi, standalone).
  Explore ships no hooks and needs no session-start bootstrap — ports are manifests +
  discovery only.
- **Version-bump tooling** — `scripts/bump-version.sh` + `.version-bump.json` (adapted from
  superpowers, MIT © Jesse Vincent — see NOTICE §4; rewritten for python3/perl, no jq, and
  YAML-frontmatter support for SKILL.md). Keeps all 8 declared version fields in lockstep:
  `<X.Y.Z>` bumps them, `--check` detects drift, `--audit` greps the repo for undeclared
  stragglers. `.claude-plugin/marketplace.json` now carries the plugin version too.

### Changed
- SKILL.md frontmatter description pruned — duplicate trigger phrasings collapsed, modifier
  flag list dropped (always-loaded context cost cut, triggers kept one-per-branch).
- `commands/explore.md` collapsed to a thin pointer at the skill's command surface —
  previously it restated every flag, so each new flag had to be edited twice (two sources
  of truth); SKILL.md is now the single source.
- `closing-the-loop.md` executor-model line fixed: it said "default `sonnet`",
  contradicting SKILL.md's orchestrator-best-fit default — now defers to the org chart.

## [2.6.0] — 2026-06-25

### Added
- **`--plan-list` / `--ls`** — a fast, read-only dashboard that prints one status table of
  every plan (number, description, severity, priority, status) and stops. It skips recon and
  exploration and never reads full plan bodies: it renders from cached context if the plans
  were already read this session, otherwise from the cheapest index (`plans/agents/README.md`
  digest, then `plans/README.md`), so it costs almost nothing. The plan index and the
  compressed digest now carry a status table whose columns match the flag.

## [2.5.0] — 2026-06-25

### Added
- **Execution principles (the executor's contract)** — five principles governing the
  executor dispatched by `--execute-level`, harmonised with the Hard Rules so they don't
  collide across recon → reconcile: handle uncertainty by type (ask if costly-to-reverse,
  experiment if it's a "does it work" question), most-direct-solution without weakening
  existing behaviour, stay in scope, suggest better ways (bounded), and end with a full
  accounting. The key harmonisation: principle 1(b)'s "run an experiment" is bounded by
  Hard Rule 2 — read-only outside the worktree, free inside the executor's disposable one.
- The executor dispatch preamble now carries these principles plus Hard Rules 4 & 6
  verbatim, and the report format gained NOT DONE / ASSUMPTIONS / SMELLS lines; the diff
  review now explicitly checks for silently weakened behaviour and carries SMELLS forward.

## [2.4.0] — 2026-06-25

### Added
- **Bundled Mermaid verifier** (`skills/explore/scripts/mermaid-verify.mjs`, optional, needs
  `npm i mermaid jsdom`). It goes beyond `mermaid.parse()` — it parses *and renders* every
  diagram in strict and loose mode and lint-checks the documented escaping rules, with a
  non-zero exit code for CI/pre-commit gating.

### Fixed
- **Diagram guidance was wrong for sequence diagrams.** Escaping is diagram-specific:
  flowchart/class/ER use HTML entities (`&lt;`/`&gt;`), but in **sequence diagrams** a `;`
  terminates the statement — so HTML entities (which contain `;`) break them. Sequence
  diagrams must use mermaid entity codes (`#60;`, `#62;`, `#38;`, `#59;`, `#35;`). The
  guidance in `system-design-reference.md` now states both correctly.
- Regenerated the `shopify-vite` reference diagrams to the current `flowchart` keyword;
  all verified rendering clean.

## [2.3.0] — 2026-06-25

### Added
- **`--reference=<path>`** — ingest the maintainer's own docs, notes, specs, or glossaries
  as first-class ground truth during recon (repeatable).
- **`--code-mode=<yes|no>`** (default `yes`) — declares the surface. `yes` = code CLI/harness
  (Claude Code), full lifecycle including execution; `no` = chat, **planning only** (write the
  ADRs and plans, never execute, dispatch, or touch git).
- **`--branch=<name>`** *(code mode)* — sets the executor's working branch; checked out if it
  exists, created from HEAD if not.
- **`--bypass-pr-create=<yes|no>`** (default `no`, code mode) — when `yes`, push the working
  branch and open a PR after an approved `--improve` diff. Still never merges.

### Changed
- Hardened the Mermaid diagram guidance against render errors — explicit rules (quote
  special-character labels, alphanumeric ids, reserved `end`, escape angle brackets, one edge
  per line, `flowchart` over `graph`) and corrected skeletons that render as-is.
- Hard Rules 1 & 2 now state the code-mode-only git exceptions (branch creation, push, PR)
  precisely; `--issues` is likewise marked code-mode only.

## [2.2.0] — 2026-06-24

### Added
- **Agent-facing `agents/` mirror.** Every action that writes a human-facing reference
  now also writes a caveman-compressed mirror beside it for agents to read instead of the
  verbose human ADRs — `docs/system-design-reference/agents/README.md` (pattern, components
  with verbatim `file:line`, boundaries, ADR digests, risk map) and `plans/agents/README.md`
  (a backlog digest for triage; full plans stay authoritative). The mirror is always
  compressed natively (independent of `--caveman`), evidence stays verbatim, and the human
  docs are unchanged. `--init`'s primer now links the mirror so the next session reads cheap
  context. `--sub-continuous` is exempt (head-docs are agent-native already).

## [2.1.1] — 2026-06-24

### Changed
- **Plans are written to `plans/` at the repo root again** (reverted from `docs/plans/`).
  This restores the directory convention used by the upstream `improve` skill and its
  forks, so the workflow stays tool-agnostic — a fork or `/improve` and `explore` write
  to the same place. Hard Rule 1 documents the rationale.

## [2.1.0] — 2026-06-24

### Added
- **`--init`** — writes a lean, curated `AGENTS.md` agent-context primer at the repo
  root and symlinks `CLAUDE.md` to it (the cross-tool standard, with a Windows/no-symlink
  fallback to an `@AGENTS.md` import). Paired with `--caveman`, the primer is written
  compressed. Reference: `skills/explore/references/init.md`.

### Changed
- Author set to **Havoc45**.

## [2.0.0] — 2026-06-24

### Changed (breaking)
- **Converted the positional variants to a feature-flag interface.** One `explore`
  command; flags select the mode. `quick`/`deep` → `--depth`; the `improve` skill's
  lifecycle is merged in as `--improve`, `--plan-once`, `--security`, `--review`,
  `--execute-level`, and `--reconcile`; subsystem focus → `--focus`; resumable mode →
  `--sub-continuous`.

### Added
- **`--verbosity`** (low/medium/high; default high) — controls ADR/plan wording without
  trimming evidence.
- **`--caveman`** — compresses subagent ↔ orchestrator communication (and the
  sub-continuous scratch) to save context/tokens, while the human deliverable stays at
  `--verbosity`. Reference: `skills/explore/references/caveman.md`.
- **`--model`** and `--execute-level` effort levels for per-plan model/effort assignment.
- **Hard Rule 7** — ground in maximum truth first (scope the architecture/stack and pull
  all docs, specs, configs, tool calls, and MCP before judging).
- Vendored the `improve` audit-playbook, plan-template, and closing-the-loop references.

## [1.1.0]

### Added
- **`--sub-continuous`** — budget-aware, resumable, multi-session exploration that reads
  the live usage budget, checkpoints into head-docs, and resumes in a fresh quota window.

## [1.0.0]

### Added
- Initial `explore` skill — a read-only architecture-understanding workflow
  (recon → explore → vet → chart & document) producing a durable system design reference
  under `docs/system-design-reference/` (diagrams, ADRs, risk map).

[2.7.0]: https://github.com/Havoc45/explore/releases/tag/v2.7.0
[2.6.0]: https://github.com/Havoc45/explore/releases/tag/v2.6.0
[2.5.0]: https://github.com/Havoc45/explore/releases/tag/v2.5.0
[2.4.0]: https://github.com/Havoc45/explore/releases/tag/v2.4.0
[2.3.0]: https://github.com/Havoc45/explore/releases/tag/v2.3.0
[2.2.0]: https://github.com/Havoc45/explore/releases/tag/v2.2.0
[2.1.1]: https://github.com/Havoc45/explore/releases/tag/v2.1.1
[2.1.0]: https://github.com/Havoc45/explore/releases/tag/v2.1.0
[2.0.0]: https://github.com/Havoc45/explore/releases/tag/v2.0.0
[1.1.0]: https://github.com/Havoc45/explore/releases/tag/v1.1.0
[1.0.0]: https://github.com/Havoc45/explore/releases/tag/v1.0.0
