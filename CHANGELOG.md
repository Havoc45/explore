# Changelog

All notable changes to the `explore` plugin. This project adheres to
[Semantic Versioning](https://semver.org/) and the spirit of
[Keep a Changelog](https://keepachangelog.com/).

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

[2.1.1]: https://github.com/Havoc45/explore/releases/tag/v2.1.1
[2.1.0]: https://github.com/Havoc45/explore/releases/tag/v2.1.0
[2.0.0]: https://github.com/Havoc45/explore/releases/tag/v2.0.0
[1.1.0]: https://github.com/Havoc45/explore/releases/tag/v1.1.0
[1.0.0]: https://github.com/Havoc45/explore/releases/tag/v1.0.0
