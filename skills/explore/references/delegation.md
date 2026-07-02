# Delegation & oversight — the org chart

How the orchestrator staffs, watches, and steers every dispatch. The economics it operationalizes: **the right model, with the right, accurate, minimal context, at the right effort** — every token spent where intelligence compounds, none on churn. This file governs *any* dispatch the skill makes — Phase-2 explorers, `--execute-level` executors, and any sub-subagent a manager spawns — and it operates inside the Hard Rules (a delegated agent still receives Hard Rules 4 and 6 verbatim, still cites evidence, still never edits outside its sanctioned scope).

## The org chart

| Rung | Model tier | Carries | Returns |
|---|---|---|---|
| **CEO** (the orchestrator) | the strongest model in the run | the end goal, the whole map, all judgment | decisions, verdicts, the assembled deliverable |
| **Manager** | strong — near-CEO capability | one subsystem / category / campaign leg, end-to-end, *plus* the direction and end goal | one merged, vetted, combined result — and any question a worker raised that it couldn't settle |
| **Worker** | cheap, fast, good at one thing | **one task**: clear goal, inlined context, machine-checkable done criteria, STOP conditions — *not* the whole picture | evidence-cited observations, or a diff plus the full accounting |

**When the manager rung exists.** Two rungs (CEO → workers) is the default — a `standard`-depth run doesn't need middle management. Add managers only when one agent can't hold a subsystem *and* the CEO can't hold all subsystems at once: a `deep` audit, a multi-package monorepo (one manager per package/bounded context), a long `--sub-continuous` campaign (one manager per campaign leg). A manager that merely forwards worker output is overhead — cut the rung.

**Staffing rules:**

- **Decisions never move down the chart.** Architecture, approach, scope, tradeoffs, verdicts belong to the CEO (a manager may decide *within* its delegated subsystem, in the direction the CEO set). Never assign open-ended reasoning — "decide the approach", "choose the architecture", "figure out what matters here" — to a worker-tier model. Execution moves down; judgment stays up.
- **Every brief is self-contained** — Hard Rule 3 applied down the chart. A worker has not seen this conversation, the map, or any other brief. A manager's brief additionally states the end goal and direction, because a manager must be able to judge whether its leg still serves them.
- **Every worker brief carries the raise-hand rule, verbatim:** *"If, from what you can see, this task appears mis-aimed — the file doesn't do what this brief assumes, the approach contradicts what you find — STOP and say so. Do not complete a task you can see is pointed wrong."* A worker needn't know the whole picture, but it must be allowed to question its own heading. (The executor preamble in `closing-the-loop.md` carries the executor-tier form of this rule alongside its STOP conditions.)
- **Managers vet before reporting up.** Phase-3 vetting travels with the delegation: a manager confirms its workers' evidence against the code before merging, so the CEO reviews one honest combined result, not N raw over-reports.

## Capability economics

A senior at $100/hour who finishes in 10 hours costs $1,000; a junior at $10/hour who takes 200 hours costs $2,000 — and on open-ended reasoning, the junior takes the 200. Benchmarks showing a mid-tier model *can* orchestrate or reason don't change where it's *cheapest* to do so: a weaker model given a judgment call re-derives, second-guesses, and loops, and the token bill outruns the rate saved. So:

- Mechanical, well-specified, single-lens work → cheapest model that clears it. This is most Phase-2 lens work and most well-planned execution.
- Long-horizon coordination, merging, subsystem judgment → strong model, `medium`/`high` effort.
- Final judgment, verdicts, assembly → the CEO, always.
- **A strong model at low effort beats a weak model at max effort on any judgment call** — judgment needs capability, not hours. This is the escalation ladder's engine.

## Spiral detection

A **spiral** is a model reasoning in circles — token spend rising, convergence absent. Weak models handed ambiguity spiral; so do executors whose plan hid a judgment call. Signals — treat **any two together** as a spiral:

- the same file(s) re-read or the same search re-run, yielding nothing new
- consecutive check-ins that restate rather than advance (no new `file:line`, no status movement)
- the progress map / claim board unmoved across two heartbeats
- repeated failed attempts at one step whose variations don't respond to the failure
- token/quota spend far past the unit estimate with no output to show

Check at every heartbeat (below). Detection is the CEO's (or the owning manager's) job, not the spiraling agent's — a model inside a spiral reports progress.

## The escalation ladder

On a detected spiral, climb — in order, one rung at a time:

1. **Narrow and retry — once.** Recall the agent. Sharpen the brief: smaller goal, more inlined context, an explicit first step, tighter done criterion. Re-dispatch at the same tier. If the sharpened brief still spirals, the problem is not the brief.
2. **Escalate the decision, not the task.** Recall. Extract the *blocking question* ("does this API tolerate X?", "which of these two shapes is right?") and hand it one rung up — a stronger model at **low effort**, fast reasoning, because the context is already assembled and it needs judgment, not hours. This is cheap; a spiral is not.
3. **Re-dispatch downward.** Decision in hand, send the now-unambiguous task back down to a worker with the answer inlined.
4. **The CEO takes it directly.** A task that escalates twice was never delegable — finish it at the top and record why, so the next plan or brief doesn't repeat the mis-delegation. *This rung exists only for read-only analysis and judgment work.* For an `--execute-level` task the CEO never writes the code itself — Hard Rule 1 holds at every rung — so the terminal rung there is **BLOCK plus a rewritten plan** carrying what was learned (the verdict table in `closing-the-loop.md`).

**Never feed a spiral:** no extra turns, no second retry, no second cheap agent pointed at the same question, no "one more revision round" hoping it converges. The `--execute-level` REVISE loop follows this ladder on spiral detection — a revision that restates rather than advances is a spiral, so skip the remaining round and climb: settle the blocking decision up the chart, re-dispatch with the answer inlined, or BLOCK (see `closing-the-loop.md`).

## Heartbeats & the steering protocol

Dispatch is not fire-and-forget. A **heartbeat** is any interim signal an agent emits, and the CEO (or owning manager) *reads every one*:

| Phase | Heartbeat source |
|---|---|
| Phase 2 (explore/audit) | each subagent's per-lens return |
| `--sub-continuous` | claim-board status changes and per-agent `### <agent-id>` blocks on the blackboard head-doc |
| Phase 5 (`--execute-level`) | the executor's STATUS report; each REVISE-round reply |
| Manager rung | the manager's report per merged worker result |

On each heartbeat, answer three questions — **advancing? still aimed at the end goal? still needed?** — and steer accordingly:

- **narrow** — progress but wandering: tighten the brief's scope
- **redirect** — the goal moved (an earlier result changed the picture): restate the goal to the agent
- **reassign** — wrong specialist: recall, re-brief a fitter agent/model
- **escalate** — spiral detected: the ladder above
- **stop** — the work is no longer needed: recall it; the cheapest steer there is

Use direct agent messaging where the harness supports it (fast path), but **record every steer, escalation, and stop in the durable record** — the head-doc ledger under `--sub-continuous`, the plan's Status block under `--execute-level`, the run notes otherwise. Steering that lives only in volatile messages dies with the session; the record is what lets a resumed campaign know *why* the plan changed.

## Interplay with the flags

- **`--model` default** *is* the CEO staffing the chart; an explicit `--model` pins tiers, and the CEO still watches and escalates.
- **`--execute-level=auto`** sets effort per plan by the rule in SKILL.md "Model & effort assignment" — rung × plan difficulty.
- **`--depth`**: `quick` = no managers, ≤1 worker; `standard` = CEO + workers (≤4 concurrent); `deep` = managers allowed (≤8 concurrent). The caps bound **total** concurrent agents, manager-spawned workers included — a manager rung re-slices the cap, it doesn't raise it. (Under `--sub-continuous`, the live budget replaces these caps.)
- **`--caveman`** compresses heartbeat transport; evidence stays verbatim, and auto-clarity holds for anything security-relevant or ambiguous.
- **`--sub-continuous`**: heartbeats ride the blackboard; when the throttle ladder cuts spend, cut worker concurrency first — the manager's merge and the CEO's judgment are the last things to cut, because unjudged raw output is the real waste.
- **No-subagent harness**: the chart collapses to one agent working rung by rung, lens by lens — and the guardrails still bind: watch *yourself* for the same spiral signals, and on detecting one, stop, decide the blocking question at full capability, then continue mechanically.
