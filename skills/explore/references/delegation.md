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

## Capability economics

A senior at $100/hour who finishes in 10 hours costs $1,000; a junior at $10/hour who takes 200 hours costs $2,000 — and on open-ended reasoning, the junior takes the 200. Benchmarks showing a mid-tier model *can* orchestrate or reason don't change where it's *cheapest* to do so: a weaker model given a judgment call re-derives, second-guesses, and loops, and the token bill outruns the rate saved. So:

- Mechanical, well-specified, single-lens work → cheapest model that clears it. This is most Phase-2 lens work and most well-planned execution.
- Long-horizon coordination, merging, subsystem judgment → strong model, `medium`/`high` effort.
- Final judgment, verdicts, assembly → the CEO, always.
- **A strong model at low effort beats a weak model at max effort on any judgment call** — judgment needs capability, not hours. This is the escalation ladder's engine.

## The model roster & routing

Capability economics says *which rung*; the roster says *which model* — and the roster is not limited to the harness's own models. Two dispatch lanes:

- **Native subagents** — the harness's own dispatch surface (on Claude Code: the Agent/Explore tools), running the harness's own models. On Claude Code that means Claude models — `sonnet` / `opus` / `fable` aliases.
- **Provider-CLI runners** *(code mode only)* — other providers' models reached through their CLIs installed on the host (e.g. `codex` → OpenAI models, `opencode` → OpenRouter-served models such as GLM), dispatched as sandboxed, non-interactive shell runs. This lane works on *any* harness that can run commands. Detect availability during recon (`command -v codex opencode`) and note in the run record which lanes this run has.

**The roster.** Shipped defaults — treat cost as *what the operator actually pays* (subscriptions, included limits), not list price; re-rank to your own billing, and re-score a model after a few real runs. Higher = better on every axis (cost higher = cheaper). Intelligence = how hard a problem the model takes unsupervised; taste = UI/UX, code quality, API design, copy.

| Model | Lane | Cost | Intelligence | Taste |
|---|---|---|---|---|
| gpt-5.5 | `codex` CLI | 9 | 8 | 5 |
| glm-5.2 xhigh | `opencode` CLI | 8 | 7 | 5 |
| sonnet-5 | native | 6 | 6 | 7 |
| opus-4.8 | native | 4 | 8 | 8 |
| fable-5 | native / the session itself | 2 | 9 | 9 |

*(Scores provisional — calibrated so far only against a three-executor bake-off, 2026-07-04: two small, well-specified config-repo plans, which measures execution fidelity, not coding, design, or debugging capability. Re-score after real coding runs. On a harness whose native models differ, substitute its own tiers at the same rungs.)*

**Per-model calibration** — observed profiles; fold the brief requirements in at dispatch:

- **gpt-5.5** — strict literalist, best protocol fidelity: honors STOP conditions exactly, raises its hand with a precise diagnosis when the plan contradicts itself, never improvises. The cost is one extra round-trip whenever the plan holds a wrinkle a bolder model would resolve itself — budget for it. Best default where deviation must never be silent.
- **glm-5.2 xhigh** — best bounded judgment and accounting: self-adjudicates within scope and defends the reasoning openly in ASSUMPTIONS rather than stopping or going silent; also the best finder of adjacent issues. Weaknesses: verbose reports, slowest wall-clock, and its lane drops tool junk (`.codegraph/`, `.omo` — opencode tooling) into the tree — sweep for and remove it after every opencode run, before diff review.
- **sonnet-5** — fastest, cheapest path to a correct result on well-specified mechanical work (one pass, byte-parity with an approved original). Weakness: **silent deviation** — applies pre-adjudicated amendments without surfacing them and leaves the thinnest deviation trail; on a plan where the amendment *hadn't* been adjudicated, that same silence is a REVISE. Its briefs restate the reporting contract explicitly: *record every deviation, however small*.

**Routing rules** — the CEO applies these when staffing the chart:

1. **Quota preservation.** The session model's quota is the scarcest budget in the run — spend it only where intelligence compounds: orchestration, judgment, vetting, verdicts, assembly. Worker-tier units (lens sweeps, audit categories, well-specified execution, mechanical analysis) go to a provider-CLI lane whenever one is installed; native subagents are the worker-tier *fallback*, not the default.
2. **The Lane column binds.** A roster model is dispatched only through its listed lane. OpenRouter also serves Claude models (`openrouter/anthropic/claude-sonnet-5`, …), so the `opencode` lane *can* reach them — never route it: that swaps included-subscription quota for pay-per-token spend, drops the harness's native dispatch surface, and voids rule 7's different-provider independence (and `--variant` flags are silently ignored off glm-5.2, so effort quietly vanishes). Rule 1 offloads worker-tier *units* to cheaper CLI-lane models; it never re-lanes a Claude model. A named model unavailable on its lane falls back *within* the lane: native Claude tiers descend to the **sonnet-4.6 floor** — never lower, never Haiku (rule 8), never sideways into a CLI lane; an unavailable CLI-lane model is a preflight **reassign** (constraints below).
3. **Defaults, not limits.** Standing permission to escalate: judge the output, not the price tag. A cheaper model's return that doesn't meet the bar is redone one tier up without asking — escalating costs less than shipping mediocre work (the escalation ladder already encodes this).
4. **Intelligence > taste > cost** when axes conflict for anything that ships; cost is a tie-breaker only.
5. **Bulk/mechanical work** (clear-spec execution, migrations, data analysis, lens sweeps) → gpt-5.5. glm-5.2 xhigh is the second bulk lane — an independent perspective, or the substitute when `codex` is absent or its limits exhausted.
6. **Anything user-facing** (UI, copy, API design) needs taste ≥ 7 — a Claude tier, on the native lane (rule 2).
7. **Verdicts and reviews stay with the CEO.** Optionally commission one independent second-opinion review from a *different provider* (read-only CLI run) — advisory input to the verdict, never the verdict itself.
8. **Never staff Haiku.** The cheap tier is a CLI lane — or sonnet-5 at low effort when no CLI is installed (floor per rule 2: sonnet-4.6).

**Rung staffing with the roster:**

| Rung | Default staffing |
|---|---|
| CEO | the session model — never offloaded |
| Manager | opus-4.8 (native); fable-5 for the hardest campaign legs |
| Worker | gpt-5.5 (`codex`) or glm-5.2 xhigh (`opencode`); sonnet-5 when no CLI lane exists |
| Executor | per plan: mechanical, well-specified → a CLI lane; taste-sensitive or user-facing diffs → opus-4.8 / sonnet-5 native |

**Dispatch mechanics** (verified command shapes; adjust model ids to the host's config):

Read-only worker — Phase-2 lens, audit category, second-opinion review:

```bash
codex exec --json -s read-only -C <repo-root> -c model_reasoning_effort=<low|medium|high|xhigh> \
  -o <report-file> "<self-contained brief>"
opencode run -m openrouter/z-ai/glm-5.2 --variant xhigh --format json --dir <repo-root> \
  "<self-contained brief>"
```

The read-only guarantees differ by lane: **codex `-s read-only` is an OS-level sandbox** — that worker cannot mutate the tree even if its reasoning goes wrong. **opencode's default-deny permissions are application-level gating**, and config-dependent (a host config that allows edits weakens them) — cheap insurance is the executors' main-tree check (below) after an opencode worker run too. Direct `-o <report-file>` (and any captured stdout) into a scratch directory or a path this skill owns — never into the user's working tree (the analyzers' `--output` rule, applied to runners). The `--json` / `--format json` event streams are where the **session id** for steering comes from — capture it at dispatch.

Executor — `--execute-level`, confined to the disposable worktree:

```bash
codex exec --json -s workspace-write -C <worktree> -c model_reasoning_effort=<effort> \
  -o <report-file> "<plan, inlined, + executor preamble>"
opencode run -m openrouter/z-ai/glm-5.2 --variant <high|xhigh> --format json --dir <worktree> --auto \
  "<plan, inlined, + executor preamble>"
```

The two lanes confine differently — know which guarantee you're holding. **codex `workspace-write` rooted at the worktree is an OS-level sandbox** — writes outside it are blocked by construction, so Hard Rules 1–2 hold mechanically; prefer this lane for execution when both exist. (It also blocks *network* by default — a plan whose steps need dependency installs either gets `-c sandbox_workspace_write.network_access=true` on dispatch, stated in the run record since it widens the sandbox to the network, or the orchestrator pre-installs dependencies in the worktree before dispatching.) **opencode `--auto` is permission auto-approval, not filesystem confinement** — the worktree boundary rides on the brief and on review: after any `--auto` run, verify the user's working tree is untouched (`git -C <repo-root> status --porcelain` unchanged) *before* reviewing the worktree diff, and treat any main-tree write as an automatic BLOCK. Keep `-o <report-file>` inside the worktree or scratch. Never `danger-full-access`; never `--auto` outside a worktree.

Steering / REVISE — continue the same session instead of re-briefing from zero. **A resumed run inherits no confinement you don't restate**: `codex exec resume` has no `-s`/`-C` flags and re-roots its sandbox at the *invocation cwd* — resuming an executor from the repo root would put the user's tree inside the write scope. Always resume from the same working root and re-pass the dispatch's confinement:

```bash
# executor rounds — run FROM INSIDE the worktree, restate the sandbox:
cd <worktree> && codex exec resume <session-id> -c sandbox_mode="workspace-write" "<review feedback>"
opencode run -s <session-id> --dir <worktree> --auto "<review feedback>"

# read-only rounds — same rule with the read-only scope:
cd <repo-root> && codex exec resume <session-id> -c sandbox_mode="read-only" "<narrowed brief>"
opencode run -s <session-id> --dir <repo-root> "<narrowed brief>"
```

Session ids come from the dispatch's `--json` / `--format json` events; `codex exec resume --last` and `opencode run -c` (continue-last) are fallbacks **only when a single dispatch is in flight**. The main-tree check runs after *every* CLI round that can write — not just the first.

**Effort mapping** — `--execute-level` (and the auto-pick) translated per lane:

| Level | codex `model_reasoning_effort` | opencode glm-5.2 `--variant` | Native Claude |
|---|---|---|---|
| low | `low` | `high` *(clamped — glm-5.2 exposes only `high`/`xhigh`; state the clamp)* | low |
| medium | `medium` | `high` | medium |
| high | `high` | `high` | high |
| max | `xhigh` | `xhigh` | max |

**CLI-runner constraints** — so the org chart holds across lanes:

- **One run = one unit.** A CLI run emits no mid-run heartbeat; its single terminal return *is* the heartbeat. Keep CLI briefs one well-specified unit small, and apply spiral detection *across runs* — a resumed run that restates its previous return rather than advancing is a spiral signal.
- **Briefs carry identical obligations:** self-contained (Hard Rule 3), Hard Rules 4 and 6 verbatim, the raise-hand rule verbatim, the report format when executing — and they compress under `--caveman` exactly like native subagent prompts (auto-clarity holds).
- **Returns are vetted like any worker's** — Phase-3 confirmation against the code before anything is recorded. A different provider does not change the trust model: a return is a claim, not a fact, and Rule 6 applies to what the runner read *and* to what it sent back.
- **Preflight before staffing a lane:** the CLI exists, is authenticated, and the model answers (a one-line ping if in doubt). A lane failing mid-run is a **reassign** steer — move the unit to the next lane and record it; never route around a failed lane by silently spending the session model.

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
| Provider-CLI runner | its single terminal return (or the JSONL event stream, when watched live) — one run, one heartbeat |

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
- **No-subagent harness**: the chart collapses to one agent working rung by rung, lens by lens — and the guardrails still bind: watch *yourself* for the same spiral signals, and on detecting one, stop, decide the blocking question at full capability, then continue mechanically.
