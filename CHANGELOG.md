# Changelog

All notable changes to the `explore` plugin. This project adheres to
[Semantic Versioning](https://semver.org/) and the spirit of
[Keep a Changelog](https://keepachangelog.com/).

## [2.12.0] — 2026-07-10

### Changed
- **Roster: gpt-5.5 → gpt-5.6-sol** (`delegation.md`; renames in SKILL.md,
  `closing-the-loop.md`, README): the codex lane's default is now gpt-5.6-sol
  (matches `~/.codex/config.toml`), weights cost 9 / intelligence 8 / **taste 8**
  (was 5). glm-5.2 xhigh re-weighted to cost 8 / intelligence 7 / **taste 7**
  (was 4). Fallout: routing rule 6 (user-facing needs taste ≥ 7) no longer
  implies a native Claude tier — gpt-5.6-sol and glm-5.2 xhigh now clear the
  bar, so quota preservation (rule 1) picks the lane; the executor staffing row
  adds gpt-5.6-sol for taste-sensitive diffs. The gpt-5.5 behavioural
  calibration (strict literalist, extra round-trip on plan wrinkles) carries
  over to gpt-5.6-sol until a real run contradicts it.

### Fixed
- **Knoxville vault drops** (`init.md` "Knoxville handoff" rework; SKILL.md
  Hard Rule 1, recon, Phase 4) — linked repos ended runs with vault projects
  missing most of the reference set (e.g. pid-nuxt lacking `architecture`,
  `overview`, `data-model`, `concerns`, the decisions index). Three root
  causes fixed: (1) Hard Rule 1 never sanctioned vault writes, so runs
  improvised — the linked vault project folder is now an explicit owned
  destination (with `knoxville sync` sanctioned); (2) only the `--init`
  primer had a vault mapping — a routing table now maps **every** output
  (reference set → `docs/` as `doc`, ADRs → `adr/`, plans → `plans/`,
  mirrors + primer → `agents/`; `--sub-continuous` head-docs stay repo-side)
  with a file-for-file parity rule and a `docs_list` tick-off as the
  completion criterion; (3) nothing committed the vault — MCP CRUD
  auto-commits only under `sync.auto: true` and no `docs_sync` tool exists,
  so every vault-writing run now ends with `knoxville sync` and confirms
  `committed` / `no changes`.
- **Knoxville facts refreshed** against the current repo
  (`github.com/Havoc45/Knoxville`): vault root read from
  `~/.config/knoxville/config.json` `vaultRoot` (never assume the default
  path); project skeleton `adr/ plans/ docs/ agents/ archive/` + `_index.md`
  + `.knoxville-link.json`; doc types `adr|plan|doc|agent`; tool list now
  includes `docs_list`, `docs_materialize` (vault → repo write-back,
  dry-run default), `docs_restore`.

## [2.11.0] — 2026-07-08

### Added
- **Critical-path queue sequencing** (`delegation.md` "Big queues run on the
  critical path"; dispatch section of `closing-the-loop.md`; `sub-continuous.md`
  unit ordering; Phase-5 pointer in SKILL.md): big queues are ordered before
  staffing — dependency edges first, then priority (severity/P-level), then
  leverage — and launched in that order with maximum parallelism the order
  allows; free slots take the next *independent* unit, never filler that blocks
  a prerequisite's slot.
- **Judge panel — escalation verification** (`closing-the-loop.md`; APPROVE
  row, Phase-5 summary in SKILL.md; routing rule 7 cross-ref in
  `delegation.md`): default verification stays CEO review + one independent
  second opinion; a panel of 2–3 independent read-only raters (different
  models, different providers where lanes allow) is convened only on user
  request or when the CEO judges severity warrants it (HIGH finding,
  security/schema/public-API surface, CEO–second-opinion disagreement,
  wide-blast-radius multi-plan PR). Fixed format — `RATING` /
  `VERDICT: SHIP|FIX-FIRST` / `TOP ISSUES` with `file:line`; ratings advisory
  to the CEO's verdict, majority-flagged issues reopen REVISE, and a convened
  panel clears before any `--bypass-pr-create=yes` PR.
- **Sub-continuous refresh loop + hard 90% line** (`sub-continuous.md`; flag
  row in SKILL.md): per-harness usage-command table (Claude Code / Codex
  `/usage`; OpenCode via Opencode Go `ogc-usage`; other harnesses must be
  named by the user); the checkpoint write must complete before 90% of the
  quota window is consumed (hard backstop under the existing 20% reserve);
  after a quota-caused checkpoint the session schedules **one wake** at the
  reset time (harness scheduler; no scheduler → report reset time + resume
  command) whose prompt is `explore --sub-continuous` — on fire it reads
  `HEAD`, loads the head-doc, re-runs pre-flight, and continues. Context-only
  checkpoints resume immediately instead of waiting.

## [2.10.0] — 2026-07-06

### Added
- **Model labeling rule** (`references/delegation.md`; pointer in SKILL.md "Model &
  effort assignment"): every running dispatch announces its **true** model — agent
  labels `gpt-5.5:<task>`, shell-run descriptions `[glm-5.2] <run>`, worktree paths
  `<plan-id>-<model>/`, run-record lines `model @ effort via lane`. A wrapper agent
  shows the harness its own model, so the label is the only truth about who is
  actually working.
- **Codex lane quirks** (`delegation.md`): runs outlive harness shell caps (10-min
  Bash default — background + poll for the `-o` report file; the report file, not
  process exit, is the completion signal); **stdin hang** — `codex exec` blocks
  forever reading a non-TTY stdin, always append `</dev/null` (hit live on
  0.142.5); `--output-schema` (structured final message), `--add-dir` (extra
  writable dir), `--skip-git-repo-check`, `--ephemeral` (no resume), model default
  from `~/.codex/config.toml`.
- **Computer-use verification lane** (`delegation.md`; review step 7 in
  `closing-the-loop.md`): gpt-5.5 via codex as the local runtime observer — UI
  flows, browser automation, simulators, app launching, screenshots. Artifact dir →
  self-contained prompt → `codex exec -C <root> --add-dir "$ARTIFACT_DIR"
  -s danger-full-access -o "$REPORT"` → read report + screenshots. Carved out as the
  **only** sanctioned `danger-full-access` use (observe-and-report briefs only;
  `workspace-write` for non-GUI runtime checks). Live-verified end-to-end
  (screenshot capture PASS).
- **Wrapper pattern for gpt-5.5 inside native workflow fan-outs** (`delegation.md`):
  thin low-effort native wrapper writes the codex prompt, shells out, returns the
  report; `gpt-5.5:` label mandatory; parallel codex implementers need worktree
  isolation; harness token budgets count only native tokens — codex work is
  invisible to them.
- **Big-queue parallelism** (`delegation.md` flag interplay; dispatch section of
  `closing-the-loop.md`): independent queued plans (pairwise-disjoint in-scope
  paths, no dependency edges) execute concurrently, one executor per plan in its
  own worktree, CLI lanes staffed first, bounded by the `--depth` cap; reviews stay
  serial with the CEO. When in doubt, sequence.
- **Knoxville docs-vault handoff** (`references/init.md`; SKILL.md recon +
  `--init` row): detect a linked vault (`.knoxville.json`, stub `CLAUDE.md`
  starting `<!-- knoxville-stub -->`, registered `knoxville` MCP server, PATH
  binary, config/vault dirs); linked → the `--init` primer lands **in the vault**
  (`docs_create`/`docs_update`), repo root untouched; installed-not-linked →
  invoke `docs_init` over MCP on the user's behalf (relaying `needs_decision`
  round-trips); absent → recommend and offer clone → build → `claude mcp add`
  setup (npm package unpublished as of 2026-07).

### Changed
- **Roster: gpt-5.5 primacy** (`delegation.md`): included quota runs **~30× any
  Claude tier's** — effectively free; default coding workhorse, standing
  independent second-opinion reviewer, and the computer-use verification agent.
  Routing rule 5 widened from bulk/mechanical to coding generally; rule 7 now
  defaults second opinions to gpt-5.5, commissioned liberally.
- **Roster: glm-5.2 taste 5 → 4** (design taste a notch below gpt-5.5's); made the
  explicit coding fallback for **both** gpt-5.5 (lane absent/exhausted) and
  opus-4.8 (native-quota preservation).
- **Executor preamble** (`closing-the-loop.md`) carries operator style prefs:
  concise simple solutions; verify via check commands (typecheck/lint/targeted
  tests), no dev servers, no builds unless the plan says so; TypeScript never
  `any` unless the plan allows; keep the repo's existing package manager.

## [2.9.0] — 2026-07-06

### Added
- **MCP dispatch transport for the provider-CLI lanes** (`references/delegation.md`,
  new "Dispatch transports" + "MCP call shapes"). Each lane is now reachable two
  ways: a registered MCP server — `codex mcp-server` (tools `codex` /
  `codex-reply`), and a new vendored zero-dep wrapper
  `skills/explore/scripts/opencode-mcp.mjs` over `opencode serve` (six tools:
  `opencode_run` / `fire` / `status` / `wait` / `steer` / `abort`, one server
  rooted per `directory` across repos and worktrees) — or the existing sandboxed
  shell runs, which remain the universal fallback (no registration, non-MCP
  harnesses, dispatch from inside a subagent). Registration snippets in
  `README.md` "Minion platforms (optional)".
- **Minion platforms — tier-3 nesting** (`delegation.md`): one lane dispatch can
  be a *manager with minions* — codex `multi_agent` (stable, default-on at
  0.142.5; collab tools `spawn_agent`/`wait`/`close_agent`; spawns only when the
  brief explicitly asks) and opencode task-tool subagents (children inspectable
  at `GET /session/{id}/children`; per-agent model fixed in config). `--depth`
  caps bound total agents *including* platform-spawned minions, so fan-out
  briefs carry their own cap; a platform that fans out is a manager and vets
  before reporting up.
- **Mid-run steering** (`delegation.md`, `closing-the-loop.md`): opencode
  `opencode_steer` aborts the in-flight turn and redirects the same session — a
  true interrupt (live-verified); codex steers checkpoint-style via
  `codex-reply` (same server process; the live server retains the thread's
  cwd/sandbox) with shell `codex exec resume` as the restart fallback — thread
  ids interoperate between the two transports. REVISE rounds updated for both.
- **Capability posture** (SKILL.md, org chart): staff as if on the max tier —
  the org chart never shrinks to the orchestrator's own model or plan tier;
  complex tasks get worktrees, sandboxed minions, and parallel lanes by
  default. Judgment placement still follows the session model; spend governance
  (throttle ladder, credits guard, pay-per-token consent) binds unchanged.

### Changed
- **Roster: glm-5.2 provisionality retired** (`references/delegation.md`). Proven on
  real coding work: slightly below gpt-5.5 (which still leads most areas), cheaper
  per token, and the standing fallback when the `codex` lane is absent or
  exhausted. The provisional caveat now covers only the native-tier scores
  (still calibrated on execution fidelity alone).
- Tag/link record reconciled (CHANGELOG footer, HANDOVER): v1.0.0–v2.1.0 predate
  the repo; v2.2.0's changes are in-repo (`347f036`) but no commit carried a
  2.2.0 manifest, so it has no tag anchor; v2.1.1 (`b2ab369`) is the first
  tagged, linked release.
- Live-verified against codex 0.142.5 / opencode 1.17.13: `codex exec --json`
  now emits `thread_id` in `thread.started` (the "session id missing from
  `--json`" caveat is stale); the codex MCP thread registry is
  per-server-process; opencode permission gating rides the host config through
  both transports (a stalled async run usually = pending permission ask).
  "One run = one unit" narrowed to the shell transport — MCP dispatches have
  real heartbeats (`opencode_status` polls, codex progress events).

## [2.8.1] — 2026-07-04

### Fixed
- **Lane binding made explicit** (`references/delegation.md`, new routing rule 2 "The
  Lane column binds"; old rules 2–7 renumbered 3–8). The roster's Lane column was
  reference, not a rule — quota preservation ("CLI lane whenever one is installed")
  plus opencode exposing `openrouter/anthropic/claude-sonnet-5` let a live session
  route sonnet-5 through the `opencode` lane. Now: a roster model is dispatched only
  through its listed lane; Claude models are never re-laned through a provider CLI
  (pay-per-token instead of included quota, no native dispatch surface, voids the
  different-provider second-opinion independence, `--variant` silently ignored off
  glm-5.2). Rule 6 (user-facing taste ≥ 7) clarified to "a Claude tier, on the
  native lane".

### Added
- **Model-unavailability fallback floor** (same rule): a named model unavailable on
  its lane falls back *within* the lane — native Claude tiers descend to the
  **sonnet-4.6 floor**, never lower, never Haiku, never sideways into a CLI lane;
  an unavailable CLI-lane model remains a preflight reassign.

### Changed
- **Roster calibrated** against the 2026-07-04 three-executor bake-off (two small,
  well-specified config-repo plans; scores stay provisional — execution fidelity
  measured, coding/design/debugging capability not yet): sonnet-5 intelligence
  5 → 6 (one-pass byte-parity with the approved original, correct handling of the
  pre-adjudicated amendment). New per-model calibration notes with
  brief requirements at dispatch: gpt-5.5 strict literalist (budget an extra round
  on plan wrinkles), glm-5.2 self-adjudicates openly but drops `.codegraph/`/`.omo`
  tool junk (sweep after every opencode run, before diff review), sonnet-5
  silent-deviation risk (briefs restate *record every deviation, however small*).

## [2.8.0] — 2026-07-04

### Added
- **The model roster & routing** (`references/delegation.md`, new section; SKILL.md
  "Model & effort assignment" expanded). Staffing is no longer limited to the harness's
  own models — two dispatch lanes: **native subagents** (on Claude Code: `sonnet` /
  `opus` / `fable`) and **provider-CLI runners** (`codex` → OpenAI models, `opencode` →
  OpenRouter-served models such as glm-5.2), detected at recon via `command -v`. The
  shipped roster ranks gpt-5.5, glm-5.2 xhigh, sonnet-5, opus-4.8, and fable-5 on
  cost / intelligence / taste, with routing rules: **quota preservation** (the session
  model is spent only where intelligence compounds — orchestration, vetting, verdicts;
  worker-tier units offload to a CLI lane whenever one is installed), defaults-not-limits
  escalation (judge the output, not the price tag), intelligence > taste > cost for
  anything that ships, taste ≥ 7 for user-facing work, never staff Haiku. Dispatch
  mechanics are verified command shapes: `codex exec -s read-only|workspace-write
  -C <dir> -c model_reasoning_effort=low|medium|high|xhigh -o <report>` (+
  `codex exec resume <session-id>` for steering/REVISE — confinement restated on every
  resume), `opencode run -m openrouter/z-ai/glm-5.2 --variant high|xhigh` (+
  `-s <session-id>`; `--auto` only inside a worktree) — codex's OS-level sandbox enforces
  Hard Rules 1–2 mechanically; the opencode lane is permission-gated, with a mandatory
  post-run main-tree check (`git status --porcelain` unchanged) instead. Includes
  the `--execute-level`→effort mapping per lane and the CLI-runner constraints (one run
  = one unit = one heartbeat; spiral detection across resumes; briefs carry the same
  verbatim rules; returns vetted like any worker's; lane preflight + reassign-on-failure).
- **CLI-lane executor dispatch** (`references/closing-the-loop.md`). `--execute-level`
  can now dispatch the executor through a provider CLI confined to the disposable
  worktree (the orchestrator creates the worktree; codex's sandbox pins writes inside it,
  the opencode lane adds the post-run main-tree check); REVISE resumes the same CLI
  session with the confinement restated from inside the worktree; high-risk diffs may get
  one **second-opinion review from a different provider** (read-only run — advisory
  input; the verdict stays the CEO's).
- **Offload lanes in `--sub-continuous`** (`references/sub-continuous.md` pre-flight §5).
  Provider-CLI dispatches spend the other provider's budget, not the Claude quota pool —
  prefer offloading worker units under quota pressure; the throttle ladder cuts *native*
  workers first; a CLI lane hitting its own limit idles (reassign or drain), never
  routing its work onto Claude credits. The credits guard governs the Claude quota only.

- **Pay-per-token lane consent** (`--sub-continuous`): at pre-flight, lanes are
  classified subscription vs pay-per-token; a metered lane (e.g. OpenRouter) needs one
  explicit user consent with a projected per-unit cost before it's staffed in a campaign
  — the credits-guard principle applied to the other provider's wallet.

### Changed
- **Hard Rules 1–2 amended** for the CLI lane: Rule 1 now names the executor as "a
  native subagent, or a provider-CLI run" and owns the disposable worktree + captured
  report file for the run's duration; Rule 2's worktree-creation exception covers the
  generated `advisor/<plan-id>` branch and the worktree the orchestrator itself creates
  for a provider-CLI executor.
- **CEO tier redefined** from "the strongest model in the run" to "the session model —
  the run's judgment tier, never offloaded" (the roster can staff workers that outrank
  the session model on raw intelligence; judgment stays with the orchestrator).
- SKILL.md Phase 1 recon now detects available dispatch lanes (`command -v codex
  opencode`); Phase 2 names the CLI-runner fan-out option beside native Explore agents;
  README documents the two lanes in the `--model` row and "How it works".

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

[2.12.0]: https://github.com/Havoc45/explore/releases/tag/v2.12.0
[2.11.0]: https://github.com/Havoc45/explore/releases/tag/v2.11.0
[2.10.0]: https://github.com/Havoc45/explore/releases/tag/v2.10.0
[2.9.0]: https://github.com/Havoc45/explore/releases/tag/v2.9.0
[2.8.1]: https://github.com/Havoc45/explore/releases/tag/v2.8.1
[2.8.0]: https://github.com/Havoc45/explore/releases/tag/v2.8.0
[2.7.0]: https://github.com/Havoc45/explore/releases/tag/v2.7.0
[2.6.0]: https://github.com/Havoc45/explore/releases/tag/v2.6.0
[2.5.0]: https://github.com/Havoc45/explore/releases/tag/v2.5.0
[2.4.0]: https://github.com/Havoc45/explore/releases/tag/v2.4.0
[2.3.0]: https://github.com/Havoc45/explore/releases/tag/v2.3.0
[2.1.1]: https://github.com/Havoc45/explore/releases/tag/v2.1.1

<!-- v1.0.0–v2.1.0 predate this repository (built before the first git commit), so no
     tags exist for them. v2.2.0's changes are in-repo (347f036) but no commit ever
     carried a 2.2.0 manifest, so it has no tag anchor either. Those headings are
     intentionally unlinked; v2.1.1 (b2ab369) is the first tagged, linked release. -->
