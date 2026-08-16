# Delegation & oversight — the org chart

How the orchestrator staffs, watches, and steers every dispatch. The economics it operationalizes: **the right model, with the right, accurate, minimal context, at the right effort** — every token spent where intelligence compounds, none on churn. This file governs *any* dispatch the skill makes — Phase-2 explorers, `--execute-level` executors, and any sub-subagent a manager spawns — and it operates inside the Hard Rules (a delegated agent still receives Hard Rules 4 and 6 verbatim, still cites evidence, still never edits outside its sanctioned scope).

## The org chart

| Rung | Model tier | Carries | Returns |
|---|---|---|---|
| **CEO** (the orchestrator) | the session model — the run's judgment tier, never offloaded | the end goal, the whole map, all judgment | decisions, verdicts, the assembled deliverable |
| **Manager** | strong — near-CEO capability | one subsystem / category / campaign leg, end-to-end, *plus* the direction and end goal | one merged, vetted, combined result — and any question a worker raised that it couldn't settle |
| **Worker** | cheap, fast, good at one thing | **one task**: clear goal, inlined context, machine-checkable done criteria, STOP conditions — *not* the whole picture | evidence-cited observations, or a diff plus the full accounting |

**When the manager rung exists.** Two rungs (CEO → workers) is the default — a `standard`-depth run doesn't need middle management. Add managers only when one agent can't hold a subsystem *and* the CEO can't hold all subsystems at once: a `deep` audit, a multi-package monorepo (one manager per package/bounded context), a long `--sub-continuous` campaign (one manager per campaign leg). A manager that merely forwards worker output is overhead — cut the rung.

**Staffing rules:**

- **Decisions never move down the chart.** Architecture, approach, scope, tradeoffs, verdicts belong to the CEO (a manager may decide *within* its delegated subsystem, in the direction the CEO set). Never assign open-ended reasoning — "decide the approach", "choose the architecture", "figure out what matters here" — to a worker-tier model. Execution moves down; judgment stays up.
- **Every brief is self-contained** — Hard Rule 3 applied down the chart. A worker has not seen this conversation, the map, or any other brief. A manager's brief additionally states the end goal and direction, because a manager must be able to judge whether its leg still serves them.
- **Every worker brief carries the raise-hand rule, verbatim:** *"If, from what you can see, this task appears mis-aimed — the file doesn't do what this brief assumes, the approach contradicts what you find — STOP and say so. Do not complete a task you can see is pointed wrong."* A worker needn't know the whole picture, but it must be allowed to question its own heading. (The executor preamble in `closing-the-loop.md` carries the executor-tier form of this rule alongside its STOP conditions.)
- **Managers vet before reporting up.** Phase-3 vetting travels with the delegation: a manager confirms its workers' evidence against the code before merging, so the CEO reviews one honest combined result, not N raw over-reports.

**Companion staffing — caveman cavecrew.** When the caveman plugin's cavecrew agents are present on the harness, worker-tier **NATIVE** units may staff `cavecrew-investigator` (read-only location sweeps) and `cavecrew-reviewer` (a diff-review lens); their returns are caveman-compressed — ~60% smaller for orchestrator ingestion. `cavecrew-builder` is **NOT** an executor lane — executors follow the worktree protocol (`--execute-level`, SKILL.md "Execution mode"). Orchestrator-side compression stays governed by the existing `--caveman` doctrine (`references/caveman.md`) — pointer, no duplication.

## Capability economics

A senior at $100/hour who finishes in 10 hours costs $1,000; a junior at $10/hour who takes 200 hours costs $2,000 — and on open-ended reasoning, the junior takes the 200. Benchmarks showing a mid-tier model *can* orchestrate or reason don't change where it's *cheapest* to do so: a weaker model given a judgment call re-derives, second-guesses, and loops, and the token bill outruns the rate saved. So:

- Mechanical, well-specified, single-lens work → cheapest model that clears it. This is most Phase-2 lens work and most well-planned execution.
- Long-horizon coordination, merging, subsystem judgment → strong model, `medium`/`high` effort.
- Final judgment, verdicts, assembly → the CEO, always.
- **A strong model at low effort beats a weak model at max effort on any judgment call** — judgment needs capability, not hours. This is the escalation ladder's engine.

## The model roster & routing

Capability economics says *which rung*; the roster says *which model* — and the roster is not limited to the harness's own models. Two dispatch lanes:

- **Native subagents** — the harness's own dispatch surface (on Claude Code: the Agent/Explore tools), running the harness's own models. On Claude Code that means Claude models — `sonnet` / `opus` / `fable` aliases.
- **Provider-CLI runners** *(code mode only)* — other providers' models reached through their CLIs installed on the host (e.g. `codex` → OpenAI models, `opencode` → OpenRouter-served models such as GLM). Each is a **minion platform**: reachable over two transports (a registered MCP server, or sandboxed shell runs — "Dispatch transports" in `references/delegation-transports.md`), and able to spawn its *own* native subagents below itself ("Minion platforms" below). The shell transport works on *any* harness that can run commands. Detect availability during recon (`command -v codex opencode`, plus whether their MCP servers are registered — the tools are visible) and note in the run record which lanes and transports this run has.

**The roster.** The shipped default score table (C/I/T per model), the per-model calibration notes, and the tried-but-unrostered record live in `references/model-roster.md` — read it before staffing. Scores there are defaults: treat cost as *what the operator actually pays*, re-rank to the operator's billing, and re-score after real runs.

**Role profile.** When the saved config carries `optimizations.omp_roles` (written by `--setup-plugin` — `references/setup.md` "Token optimization (OMP-style roles)"), rung-staffing defaults resolve through the roles instead of recomputing from raw C/I/T: `plan` and `slow` staff the CEO/manager tiers, `smol` staffs the worker/executor tier. The escalation ladder and the never-Haiku floor are unchanged, and the role values are lane + model ids resolved from the effective roster at run time — never hard-coded ids.

**User roster override.** When `${XDG_CONFIG_HOME:-$HOME/.config}/explore/roster.json` exists **and is schema-valid** (written by `--setup-plugin` — schema and wizard in `references/setup.md`; an invalid file is treated as absent), it is **authoritative**: its lanes are the enabled lanes and its models the eligible models, with their C/I/T scores replacing the table above for staffing decisions; entries with `null` axes are staffed conservatively (worker rung only, never user-facing work). The table above applies when no valid roster file exists **or when a valid roster leaves no locally usable lane** (`references/setup.md` "Cross-harness loading"). The pre-built lane wrapper agents (`agents/codex-worker.md`, `agents/opencode-worker.md`) read the roster at run time: a valid roster row for their lane overrides their shipped default model, and their report labels carry the model actually dispatched. (`usage_probe.py` is unaffected: its probe model is a fixed quota-header read, roster-independent by design; its limit is lane coverage — claude + codex today.) **The effective roster** = the valid saved roster when one exists (its enabled lanes restricted to those locally usable; if that restriction leaves no usable lane, the effective roster is the shipped defaults for the run — `references/setup.md` "Cross-harness loading"), else the shipped defaults. Every routing default below that activates a lane because its CLI is installed is implicitly qualified: *and the effective roster enables that lane*. When the effective roster leaves a doctrine default without an eligible model (no enabled CLI lane for second opinions, panels, or the computer-use observer), use an eligible different-model lane where one exists, otherwise say so in the run record and proceed with reduced coverage — never silently re-enable a disabled lane.

**Per-model calibration** — observed behavioural profiles per model live in `references/model-roster.md` "Per-model calibration"; fold the brief requirements in at dispatch.

**Routing rules** — the CEO applies these when staffing the chart:

1. **Quota preservation.** The session model's quota is the scarcest budget in the run — spend it only where intelligence compounds: orchestration, judgment, vetting, verdicts, assembly. Worker-tier units (lens sweeps, audit categories, well-specified execution, mechanical analysis) go to a provider-CLI lane whenever one is installed **and enabled by the effective roster**; native subagents are the worker-tier *fallback*, not the default.
2. **The Lane column binds.** A roster model is dispatched only through its listed lane. OpenRouter also serves Claude models (`openrouter/anthropic/claude-sonnet-5`, …), so the `opencode` lane *can* reach them — never route it: that swaps included-subscription quota for pay-per-token spend, drops the harness's native dispatch surface, and voids rule 7's different-provider independence (and `--variant` flags are silently ignored off glm-5.2, so effort quietly vanishes). Rule 1 offloads worker-tier *units* to cheaper CLI-lane models; it never re-lanes a Claude model. A named model unavailable on its lane falls back *within* the lane: native Claude tiers descend to the **sonnet-4.6 floor** — never lower, never Haiku (rule 8), never sideways into a CLI lane; an unavailable CLI-lane model is a preflight **reassign** (constraints below).
3. **Defaults, not limits.** Standing permission to escalate: judge the output, not the price tag. A cheaper model's return that doesn't meet the bar is redone one tier up without asking — escalating costs less than shipping mediocre work (the escalation ladder already encodes this).
4. **Intelligence > taste > cost** when axes conflict for anything that ships; cost is a tie-breaker only.
5. **Coding and bulk/mechanical work** (clear-spec execution, migrations, data analysis, lens sweeps) → gpt-5.6-sol, as much of it as clears the taste bar — at ~30× Claude quota it is effectively free, so don't ration it. Don't let cost pick the wrong model either way: use the cheap lane to gather information and try things *before* moving work to an expensive tier. glm-5.2 xhigh is the second bulk lane — an independent perspective, or the substitute when `codex` is absent or its limits exhausted (and the coding fallback for opus-5 when native quota should be preserved).
6. **Anything user-facing** (UI, copy, API design) needs taste ≥ 7 — on current weights that is gpt-5.6-sol, glm-5.2 xhigh (at the line), or a Claude tier; among those, quota preservation (rule 1) picks the lane. Below-7 models never ship user-facing work.
7. **Verdicts and reviews stay with the CEO.** Plan/implementation reviews sit at fable-5 or opus-5; additionally commission an independent second-opinion review from a *different provider* (read-only CLI run — default gpt-5.6-sol **where the effective roster enables the codex lane; otherwise the strongest enabled different-provider lane, or reduced coverage stated in the run record**; near-free at its quota, so do it liberally on anything non-trivial) — advisory input to the verdict, never the verdict itself. On high severity or user request, the single second opinion widens to the **judge panel** (`closing-the-loop.md` "The judge panel"): same principle, N raters instead of one, still advisory — an escalation, never the default.
8. **Never staff Haiku.** The cheap tier is an **enabled** CLI lane — or sonnet-5 at low effort when the effective roster enables no installed CLI lane (floor per rule 2: sonnet-4.6).

**The model-guard hook.** The plugin ships a PreToolUse guard (`hooks/model-guard.py`, wired in `hooks/hooks.json`) that blocks Fable-class and Haiku subagent dispatches on the native Agent/Task tools, so rules 1 and 8 hold mechanically rather than by memory alone. The override protocol is **one explicit operator approval per session**: the operator says go, then the brief carries `MODEL_GUARD_OK` (the hook then allows with a note to record the override), and the run record logs the approval. This guard only sees the native Agent/Task surface — a Workflow-script `agent()` call's model override runs outside the hook's reach, so that same rule binds there by doctrine and reviewers check it; the gap is real, not papered over. Separately, handing the session model a complex-logic or design-decision task requires an explicit operator ask (AskUserQuestion) once per session — the CEO's judgment is never quietly offloaded.

**Rung staffing with the roster:**

| Rung | Default staffing |
|---|---|
| CEO | the session model — never offloaded |
| Manager | opus-5 (native); fable-5 for the hardest campaign legs |
| Worker | gpt-5.6-sol (`codex`) or glm-5.2 xhigh (`opencode`); sonnet-5 when no CLI lane exists |
| Executor | per plan: mechanical, well-specified → a CLI lane; taste-sensitive or user-facing diffs → gpt-5.6-sol (taste 8, quota-free) or opus-5 / sonnet-5 native |

**Model labeling — every running thing announces its model.** The harness UI shows *its own* model for a wrapper agent and nothing at all for a shell run, so the label is often the only truth about who is actually working. The rule, applied to every dispatch without exception:

- **Agents / subagents / workflow calls**: label (or description) starts with the true worker's model **and effort** — `gpt-5.6-sol@high:review-auth`, `glm-5.2@xhigh:lens-data`, `opus-5@medium:manager-billing`. For a wrapper (a native agent that shells out to a CLI lane), the prefix names the *real* worker, not the wrapper — the UI will show the wrapper's Claude model, so the label is the only indication the work is gpt-5.6-sol's (and at what effort).
- **Shell runs**: the run's stated description carries model + effort — `[gpt-5.6-sol @ high] audit: security lens`, so a background `codex`/`opencode` process is identifiable at a glance.
- **Wrapper reports carry the runtime**: a lane wrapper's returned report opens `[<model> @ <effort> · ran <Xm Ys>]` — elapsed since the CLI/MCP dispatch, timed by the wrapper — because the harness UI's elapsed clock measures the wrapper, not the worker, and dies with the widget; the report line is what survives into the run record.
- **Worktrees & branches**: encode plan and model in the path — worktree `../<repo>-wt/<plan-id>-gpt-5.6-sol/`, generated branches stay `advisor/<plan-id>` (the worktree path carries the model; a branch name outlives the run and shouldn't).
- **Run record / heartbeat log**: every dispatch line states model + effort + lane (`gpt-5.6-sol @ high via codex-MCP`), so the record is reproducible and a stuck run is attributable without archaeology.

**Dispatch transports & lane mechanics** live in `references/delegation-transports.md` — load it per lane: codex installed → read the codex sections of `references/delegation-transports.md`; opencode → its opencode sections; inside herdr → its herdr transport section; computer-use verification → its computer-use section. Load only the sections for lanes that exist on this host.

**gpt-5.6-sol inside native workflow fan-outs (wrapper pattern).** A harness's workflow/agent `model` parameter takes only native models — it cannot name gpt-5.6-sol. To put codex work inside a native fan-out, spawn a **thin native wrapper** (cheapest native tier, low effort) whose brief is: write the self-contained codex prompt, run `codex exec` via shell, return the report (structured output on the wrapper if the harness supports it). On Claude Code the pattern ships pre-built: the plugin's `codex-worker` and `opencode-worker` agents (`agents/`) are these wrappers with every lane quirk baked in — dispatch them by name instead of hand-rolling the wrapper brief; other harnesses build the wrapper manually per this paragraph. Rules that keep the pattern honest: label the wrapper `gpt-5.6-sol:<task>` (labeling rule above — the UI shows the wrapper's model, the label is the only truth); parallel codex *implementation* wrappers each get an isolated worktree, or their edits collide in the shared checkout; and a harness token budget counts only native tokens — codex work is invisible to it, so budget math must not read "cheap" as "idle".

**Minion platforms — tier-3 nesting.** Both lanes can spawn their *own* native subagents, so one lane dispatch can be a **manager with minions** instead of a single worker:

- **codex**: `multi_agent` (stable and default-on since 0.142.5) — collab tools `spawn_agent` / `wait` / `close_agent`, child threads at depth 1 by default. Codex spawns **only when the brief explicitly asks** ("spawn one worker per X, wait for all, merge").
- **opencode**: task-tool subagents (built-ins `explore` / `general`, or named agents from the host's config); child sessions are inspectable at `GET /session/{id}/children`. A subagent's model is fixed by its agent config, not chooseable per call — pre-declare one agent per role×tier where that matters.

Two rules keep nesting inside the org chart. **The `--depth` caps bound total concurrent agents *including* platform-spawned minions** — the platform's spawns don't report to the harness, so a fan-out brief must carry its own cap ("at most N minions"). And **a platform that fans out is a manager**: its brief carries the end goal and direction, it vets its minions' returns before reporting one merged result up, and Phase-3 vetting of that merged result still happens on your side.

**CLI-runner constraints** — so the org chart holds across lanes:

- **One shell run = one unit.** A shell run emits no mid-run heartbeat; its single terminal return *is* the heartbeat. Keep those briefs one well-specified unit small, and apply spiral detection *across runs* — a resumed run that restates its previous return rather than advancing is a spiral signal. The MCP transport loosens this: `opencode_status` polls are real heartbeats (and codex streams progress events where the harness surfaces them), so longer units are steerable there — the steering protocol below applies to them unchanged.
- **Briefs carry identical obligations:** self-contained (Hard Rule 3), Hard Rules 4 and 6 verbatim, the raise-hand rule verbatim, the report format when executing — and they compress under `--caveman` exactly like native subagent prompts (auto-clarity holds). When `optimizations.context_architecture` is enabled, a brief additionally cites by relPath every fragment it inlines — model-visible ⟺ logged (`references/context-architecture.md`).
- **Returns are vetted like any worker's** — Phase-3 confirmation against the code before anything is recorded. A different provider does not change the trust model: a return is a claim, not a fact, and Rule 6 applies to what the runner read *and* to what it sent back.
- **Preflight before staffing a lane:** run the mandatory probe below and pick the transport while you're there (MCP tools visible → MCP; else shell). A lane failing mid-run is a **reassign** steer — move the unit to the next lane and record it; never route around a failed lane by silently spending the session model.

**Preflight probe — mandatory, once per run**

**When.** At Phase-1 recon, before the first dispatch of any run that will staff a CLI lane. Re-probe a lane only when it later fails, then apply the reassign rule above.

**Probe ladder.** Run cheapest first and stop at the first failure for each lane:

1. **Presence:** `command -v codex opencode`.
2. **Model availability:** for codex, `codex exec -s read-only -c model_reasoning_effort=low "Reply with exactly: OK" </dev/null` (auth + model, ~2k tokens); for opencode, `opencode models | grep -F "<model-id>"` (model listed, free, no API call).
3. **Transport health:** check only the transport the run will use. For MCP: codex gets one minimal tool call; opencode gets `opencode_health` (free, no model spend) — it reports server state, server version, and `wrapper_version` in one shot, catching a stale wrapper before the first dispatch. A shell lane needs no extra check beyond the model ping.

The stale-transport failure-shapes table lives in `references/delegation-transports.md` "Stale-transport failure shapes and refresh".

**Outcome recording.** The run record states, per lane, the probed-at result: `ok`, `absent`, `refreshed`, or `failed→reassigned`.

**Cost.** The full ladder costs at most one ~2k-token codex ping and pennies of opencode time; a stalled dispatch costs 15s–10min each. Never skip the probe to save the ping.

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
| Provider-CLI runner | shell: its single terminal return (or the JSONL event stream, when watched live) — one run, one heartbeat. MCP: `opencode_status` polls / codex progress events — real interim heartbeats |

On each heartbeat, answer three questions — **advancing? still aimed at the end goal? still needed?** — and steer accordingly:

- **narrow** — progress but wandering: tighten the brief's scope
- **redirect** — the goal moved (an earlier result changed the picture): restate the goal to the agent
- **reassign** — wrong specialist: recall, re-brief a fitter agent/model
- **escalate** — spiral detected: the ladder above
- **stop** — the work is no longer needed: recall it; the cheapest steer there is

Use direct agent messaging where the harness supports it (fast path), but **record every steer, escalation, and stop in the durable record** — the head-doc ledger under `--sub-continuous`, the plan's Status block under `--execute-level`, the run notes otherwise. Steering that lives only in volatile messages dies with the session; the record is what lets a resumed campaign know *why* the plan changed.

## Interplay with the flags

- **`--model` default** *is* the CEO staffing the chart (per the roster above); an explicit `--model` pins tiers, and the CEO still watches and escalates. `--model` may name any roster model — a native name pins the native lane; a CLI-lane model requires that CLI on the host (absent → say so and fall back per the roster, never silently substitute).
- **`--execute-level=auto`** sets effort per plan by the rule in SKILL.md "Model & effort assignment" — rung × plan difficulty.
- **`--depth`**: `quick` = no managers, ≤1 worker; `standard` = CEO + workers (≤4 concurrent); `deep` = managers allowed (≤8 concurrent). The caps bound **total** concurrent agents, manager-spawned workers included — a manager rung re-slices the cap, it doesn't raise it. (Under `--sub-continuous`, the live budget replaces these caps.)
- **`--caveman`** compresses heartbeat transport; evidence stays verbatim, and auto-clarity holds for anything security-relevant or ambiguous.
- **`--sub-continuous`**: heartbeats ride the blackboard; when the throttle ladder cuts spend, cut *native* worker concurrency first — offload lanes don't draw the quota pool (`sub-continuous.md` pre-flight §5). The manager's merge and the CEO's judgment are the last things to cut, because unjudged raw output is the real waste.
- **Big queues run on the critical path.** When many units are queued (a full audit sweep, several executable plans), **sequence before you staff**: order the queue by dependency edges first (a prerequisite launches before anything that needs its result), then priority (severity / P-level, highest first), then leverage — that ordered queue is the run's critical path. Launch in that order and parallelize everything the order allows: read-only units fan out across the CLI lanes and native workers up to the `--depth` cap; *writing* units (executors) parallelize only when their plans' in-scope paths are disjoint and no plan depends on another — then each runs in its **own worktree** (`<plan-id>-<model>` path per the labeling rule), one executor per plan, CLI lanes first (quota rule 1). Free concurrency slots are filled with the next *independent* unit down the order — never with filler that would occupy a slot an unblocked prerequisite is about to need. Review stays serial and stays with the CEO. Scope overlap or a dependency edge → those plans run in sequence; when in doubt, sequence — a merge conflict costs more than the parallelism saves.
- **No-subagent harness**: the chart collapses to one agent working rung by rung, lens by lens — and the guardrails still bind: watch *yourself* for the same spiral signals, and on detecting one, stop, decide the blocking question at full capability, then continue mechanically.
