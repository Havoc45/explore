# Sub-continuous exploration — budget-aware, resumable, multi-session

`explore --sub-continuous` lets a large exploration span **several quota windows** without losing work or quality. Before exploring, it reads how much budget is left, plans an amount of work that fits *under* the limit with a reserve, explores that much to the normal standard, and then writes a **head-doc** — a self-contained continuation checkpoint — so the next invocation (in a fresh window) picks up exactly where this one stopped. It is the mode for people on **standard / limited-quota plans** who want the full depth of `explore` without bursting their session limit or their wallet.

The discipline is unchanged — read-only on source, evidence-cited, vetted before recording. What changes is that the work is **decomposed into checkpointable units**, **bounded by a live budget**, and **persisted between sessions**.

## Two pressures that force a checkpoint

A long exploration runs into two independent ceilings; this mode respects both:

1. **Quota** — the rolling usage limit. In **Claude Code**, read it with `/usage` (quota remaining + reset time). All Claude surfaces share one quota pool across models and products, so that single number already reflects usage "regardless of model." This is the primary budget.
2. **Context window** — working memory. In Claude Code, `/context` reports headroom. A session can have quota left but a nearly-full context window, at which point quality degrades. Checkpointing and resuming in a fresh session resets the context window too.

Either ceiling approaching its reserve triggers a checkpoint. (Related Claude Code signals: `/status` for plan allocation, `/cost` for API-mode spend — informational only.)

**Harness-agnostic fallback.** If the harness has no usage command, degrade gracefully in this order: (a) use whatever quota/usage signal the harness exposes; (b) if none, fall back to a conservative fixed cap (`MAX_UNITS_PER_SESSION`, default **3**) and always checkpoint at the end; (c) optionally ask the user for their remaining budget up front. Never assume unlimited budget in this mode — that defeats its purpose.

## The budget pre-flight (run first, every session)

1. **Read the budget.** `/usage` → `remaining%` and reset time; `/context` → context headroom. Record both in the head-doc ledger — plus whether the plan is already in **overage/credits** territory (see the credits guard below; if so, this session doesn't start units at all).
2. **Hold back a reserve.** Checkpointing a context-heavy session is *not* free (writing the head-doc and any partial drafts costs tokens), so reserve headroom and stop starting new units once you cross it:
   - `CHECKPOINT_RESERVE` — default **20%** of the quota window (raise it for big repos, where the checkpoint write is larger).
   - `CONTEXT_RESERVE` — default **15%** of the context window.
3. **Estimate per-unit cost conservatively, then calibrate.** You usually can't see per-token cost, so estimate in `/usage` percentage points. After the **first** unit completes, re-read `/usage`; the delta is your measured per-unit cost. Use it to decide how many more units fit before the reserve: `affordable_units ≈ (remaining% − CHECKPOINT_RESERVE) / measured_cost_per_unit`. Round **down**.
4. **Concurrency caution.** Parallel subagents all draw from the *same* pool, so N concurrent agents burn the rolling window ~N× faster even though total quota cost is similar. If the rolling window (not total quota) is the binding constraint, prefer **fewer concurrent agents per session** — concurrency buys wall-clock speed, not quota, and can trip the rate limit sooner. The budget, not the standard Phase-2 caps (≤4 / ≤8), sets concurrency here.
5. **Offload lanes don't draw the pool.** Provider-CLI dispatches (`codex`, `opencode`, over either transport — the roster in `delegation.md`) spend that provider's own budget, not the Claude quota window, so under quota pressure they are the cheapest concurrency there is: prefer offloading worker units to an installed CLI lane, and when the throttle ladder cuts concurrency, cut **native** subagents first — an offloaded worker costs the pool only the context spent reading its return. Their spend is still real: at pre-flight, classify each lane — a **subscription / included-limit lane** (e.g. codex on a plan) is the free-offload case; a **pay-per-token lane** (e.g. OpenRouter metered billing) is the user's wallet, so staffing it in a campaign requires one explicit user consent, given a projected per-unit cost — the same principle as the credits guard, applied to the other provider. Record the consent and per-lane usage in the ledger. A CLI lane hitting *its own* limit simply idles — reassign or drain that lane, never route its work back onto Claude credits. The credits guard below governs the Claude quota.

## Pacing — the throttle ladder & the credits guard

The pre-flight is not a one-shot estimate. **Re-read the budget after every unit**, not only the first: recalibrate the measured per-unit cost, recompute `affordable_units`, and project when the reserve will be hit at the current burn rate. Budget reads are nearly free; a mis-paced session is not.

**The throttle ladder.** As the projection approaches the reserve, slow down in steps instead of running full speed into a cliff:

1. **Full fan-out** — the projection clears the reserve comfortably: run the session's planned concurrency.
2. **Halve concurrency** — the projection lands within ~2 units of the reserve: stop launching parallel batches; halve the concurrent subagents.
3. **Single-file** — within ~1 unit of the reserve: one unit at a time, budget re-read between each.
4. **Drain** — the next unit no longer fits: start nothing new; let in-flight subagents *finish their current unit* (killing them mid-unit wastes everything they already burned), then vet what completed. "Pause" in this mode always means drain, never kill.
5. **Checkpoint & stop** — write the head-doc and end the session, per the session loop.

Rungs are one-way within a session — never re-accelerate on a single optimistic read. Record every step-down (and why) in the ledger: a paced session that stopped early must say so.

**The credits guard.** Some plans spill into **paid overage credits / pay-as-you-go** once the included quota window is exhausted. The quota window is the budget this mode manages; credits are the user's wallet, and spending it is never this skill's call:

- Detect it at pre-flight and at every re-read: quota exhausted (or the usage surface reporting overage/extra-usage billing active) while the session could technically continue → you are **on credits**.
- On credits, jump straight to **drain → checkpoint → stop**, whatever rung you were on. The drain and the checkpoint write are the one sanctioned spend on credits — the minimal cost of not losing the campaign record (a killed session with no checkpoint wastes *everything* already spent). Report the reset time from the usage signal and tell the user the campaign resumes with `explore --sub-continuous` in the refreshed window — the head-doc makes the resume seamless. If the harness can schedule or defer a resume until the reset time, offer that.
- Continue on credits **only** if the user explicitly says so *in this session, after being told* — a standing config or an earlier yes doesn't carry.
- Never count credits as headroom in `affordable_units` — the estimate always ends at the included quota.

## Decompose into checkpointable units

Split the exploration into units that can each finish, be vetted, and be recorded independently — so a checkpoint never lands mid-thought:

- **Recon** is always unit 0 (cheap, and everything else depends on it).
- Then one unit per **lens** (pattern, components, layers, data-flow, data-model, dependencies, deployment, cross-cutting, scale) or per **package / bounded context** on a monorepo.
- Order by leverage: the units that explain the most of the system first, so an interrupted campaign is still useful early.

A unit is "done" only after Phase 3 vetting — partial-but-**verified**, never partial-and-guessed.

## The head-doc store

A second, clearly-operational location under `docs/`, separate from the deliverable:

```
docs/explore-head-docs/
├── HEAD                       # one line: the active campaign handle (fast resume pointer)
├── <handle>.head.md           # the living head-doc for a campaign (progress, ledger, findings-so-far, next steps)
└── <handle>.partials/         # optional: per-agent/per-unit shards for large or concurrent campaigns
```

- **Handle** — a unique campaign id, format `<repo-slug>-<YYYYMMDD>-<6hex>` (e.g. `shopify-vite-20260623-9f3a1c`; generate the suffix with `openssl rand -hex 3` or any nonce). It is written into the filename **and** the head-doc front-matter, and echoed in `HEAD`. The handle is how a later session knows *which* exploration to continue.
- The head-doc is the **source of truth** for the campaign. The polished `system-design-reference/` is written only at completion (or progressively, with the head-doc tracking what's been promoted).

> **Permitted-writes note.** In `sub-continuous` mode, Hard Rule 1's single write location is extended to **two**: `docs/system-design-reference/` (the deliverable) and `docs/explore-head-docs/` (the continuation store). Both are documentation the skill creates and owns; the read-only-on-source invariant is unchanged, and you still never touch a file you did not create.

## Head-doc format

```markdown
---
handle: shopify-vite-20260623-9f3a1c
repo: ComfortWorks/shopify-vite
commit: 990fb65
status: in-progress            # in-progress | complete
sessions: 1
created: 2026-06-23T11:00:00+08:00
updated: 2026-06-23T13:20:00+08:00
---

# Explore head-doc — shopify-vite-20260623-9f3a1c

## Budget ledger
| Session | Quota at start | Context at start | Units planned | Units done | Stopped because |
|---|---|---|---|---|---|
| 1 | 38% remaining (resets 16:40) | 70% free | components, layers, data-flow | components ✓, layers ✓, data-flow ◐ | hit 20% checkpoint reserve |

Measured cost/unit this session: ~9% per lens (calibrated after unit 1).
Pacing events: stepped to rung 2 (halved concurrency) after unit 2 — projection within 2 units of reserve; drain + checkpoint after unit 3.

## Progress map  ← the resumable state
| Unit (lens / package) | Status | Evidence captured | Promoted to reference? |
|---|---|---|---|
| recon | done | overview facts | overview.md (draft) |
| pattern | done | index.ts:13-23 | architecture.md |
| components | done | index.ts, 4 modules | architecture.md |
| layers & boundaries | done | … | partial |
| data flow | partial | dev flow done; build flow pending | no |
| dependencies | pending | — | — |
| deployment | pending | — | — |
| cross-cutting / risks | pending | — | — |

Status legend: pending · claimed:<agent-id> · in-progress · partial · done

## Findings so far (verified, not all promoted)
- [components] vitePluginShopify returns 4 plugins — `index.ts:13-23`
- [data-flow/dev] placeholder origin rewritten in transform — `html.ts:213-216`
  (evidence-cited, vetted; promotion to the reference happens at completion)

## Open threads — start here next session
1. Finish build-mode data-flow (closeBundle manifest→tags, `html.ts:291+`).
2. Dependencies lens — run `dependency_analyzer.py` seed, then verify.
3. Cross-cutting + risk synthesis.

## Agent-tree plan (remaining)
- Next session, budget permitting: dependencies + deployment as 2 units; then cross-cutting + risks.
- If quota is tight (<25%): one unit, then checkpoint again.

## Notes for concurrent agents (blackboard mode — see below)
- Claim a unit by setting its Status to `claimed:<agent-id>` before exploring.
- Append findings under your own `### <agent-id>` block; the orchestrator reconciles into the table and the reference.
```

## The session loop

```
pre-flight (read /usage, /context; set reserves; credits check)
  └─ resume? read HEAD / passed handle → load head-doc → verify vs current commit
allocate units for this session = affordable_units (rounded down), highest-leverage first
explore each allocated unit:  fan out (throttle-ladder-bounded) → vet (Phase 3) → record into head-doc
  └─ re-read /usage + /context → recalibrate cost/unit, re-project → step the ladder down if needed
when remaining% ≤ CHECKPOINT_RESERVE  OR  context ≤ CONTEXT_RESERVE  OR  on credits  OR  units exhausted:
  └─ drain in-flight → checkpoint: update progress map, ledger, findings-so-far, open threads; write head-doc + HEAD; STOP
```

The checkpoint write is the **last** thing the session does, while it still has the reserve — so it can never be cut off mid-write, which would corrupt the only record of the campaign.

## Resume algorithm (next invocation)

1. `explore --sub-continuous` with no handle → read `docs/explore-head-docs/HEAD`, load that campaign's head-doc. `explore --sub-continuous=<handle>` → load that specific one. `explore --sub-continuous=new` → force a fresh campaign.
2. If a head-doc is found, reconstruct context from it (you need nothing from the prior session's conversation — the head-doc is self-contained, per Rule 3). **Verify against the current commit:** if the code moved since the head-doc's `commit`, re-validate any `done` unit the change touched and note the drift; pending units are unaffected.
3. Run a fresh pre-flight (new window = new budget) and continue with the pending/partial units.
4. If no head-doc exists, it's a new campaign: generate a handle, write `HEAD`, do recon, begin.

## Completion & promotion

When the progress map has no `pending`/`partial` units left:

1. Promote the accumulated, vetted findings into the final **`docs/system-design-reference/`** following `system-design-reference.md` (the normal Phase-4 output — diagrams, ADRs, risk map). This is the finished deliverable.
2. Set the head-doc `status: complete`. Either leave it as a campaign record or archive it (move under `docs/explore-head-docs/archive/`); clear or repoint `HEAD`. Never delete it silently — it's the audit trail of how the reference was built.

The head-docs are scaffolding; `system-design-reference/` is the building. A reader only ever needs the building.

## Inter-agent / blackboard mode

The head-doc doubles as a **shared blackboard** so the protocol works whether or not the harness lets agents talk directly:

- **No direct messaging (lowest common denominator):** the head-doc *is* the channel. Sessions hand off through it sequentially; that's the baseline that makes the feature work on any harness, because a persistent file survives a session dying.
- **Concurrent subagents in one session:** they coordinate through the head-doc's progress map as a **claim board** — an agent sets a unit's status to `claimed:<agent-id>` before working it (avoiding duplicate exploration), and appends its findings under its own delimited `### <agent-id>` block so parallel writes don't clobber. The orchestrator reconciles claimed→done and merges blocks into the table. For heavy campaigns, give each agent its own shard in `<handle>.partials/` and reconcile at checkpoint.
- **Harnesses with direct agent-to-agent messaging or workflow-tree communication:** use that to coordinate faster (claim negotiation, "I found the auth boundary, you take billing"), but **keep the head-doc as the durable source of truth** — messaging is the fast path, the head-doc is what survives a crash or a window reset. Never let coordination live only in volatile inter-agent messages.

In all three cases the rule is the same: ephemeral coordination may speed things up, but the head-doc is the record that lets a brand-new session, with zero prior context, resume the campaign.

## Quality & wallet guarantees

- **Quality is not traded for budget.** Each unit is explored to the same depth and evidence standard and vetted before it's recorded; the mode does *fewer units per session*, never *shallower units*. The head-doc carries the standard across the seam.
- **Wallet is protected by never re-doing work.** The progress map means a resumed campaign never re-explores a `done` unit; findings are promoted into the reference once, at completion, not rewritten each pass; and the conservative reserve prevents a wasted, cut-off session that produced no checkpoint.
