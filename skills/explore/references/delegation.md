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
- **Provider-CLI runners** *(code mode only)* — other providers' models reached through their CLIs installed on the host (e.g. `codex` → OpenAI models, `opencode` → OpenRouter-served models such as GLM). Each is a **minion platform**: reachable over two transports (a registered MCP server, or sandboxed shell runs — "Dispatch transports" below), and able to spawn its *own* native subagents below itself ("Minion platforms" below). The shell transport works on *any* harness that can run commands. Detect availability during recon (`command -v codex opencode`, plus whether their MCP servers are registered — the tools are visible) and note in the run record which lanes and transports this run has.

**The roster.** Shipped defaults — treat cost as *what the operator actually pays* (subscriptions, included limits), not list price; re-rank to your own billing, and re-score a model after a few real runs. Higher = better on every axis (cost higher = cheaper). Intelligence = how hard a problem the model takes unsupervised; taste = UI/UX, code quality, API design, copy.

| Model | Lane | Cost | Intelligence | Taste |
|---|---|---|---|---|
| gpt-5.6-sol | `codex` CLI | 9 | 8 | 8 |
| glm-5.2 xhigh | `opencode` CLI | 8 | 7 | 7 |
| sonnet-5 | native | 6 | 6 | 7 |
| opus-4.8 | native | 4 | 8 | 8 |
| fable-5 | native / the session itself | 2 | 9 | 9 |

*(gpt-5.6-sol — the codex lane's current default, superseding gpt-5.5 — and glm-5.2 are validated on real coding work: gpt-5.6-sol leads across most areas, and its included quota runs **~30× any Claude tier's** (Fable included) — treat it as effectively free, route coding volume there first, and commission it liberally for extra independent reviews. With taste now 8/7, the CLI lanes clear the user-facing bar (rule 6), not just the bulk lane. glm-5.2 sits slightly below gpt-5.6-sol — a notch lower on every axis — and is the standing coding fallback for **both** gpt-5.6-sol (lane absent/exhausted) and opus-4.8 (native quota worth preserving). The native-tier scores remain provisional — calibrated only against the 2026-07-04 three-executor bake-off (execution fidelity, not coding/design/debugging) — re-score them as real runs land. On a harness whose native models differ, substitute its own tiers at the same rungs.)*

**Per-model calibration** — observed profiles; fold the brief requirements in at dispatch:

- **gpt-5.6-sol** — strict literalist, best protocol fidelity: honors STOP conditions exactly, raises its hand with a precise diagnosis when the plan contradicts itself, never improvises. The cost is one extra round-trip whenever the plan holds a wrinkle a bolder model would resolve itself — budget for it. Best default where deviation must never be silent. Effectively free (quota note above): the default coding workhorse, the standing second-opinion reviewer, and the computer-use verification agent (lane below). *(Profile observed on gpt-5.5; the taste-8 re-rank is operator-validated, the behavioural notes carry over until a 5.6-sol run contradicts them.)*
- **glm-5.2 xhigh** — the proven coding alternate: slightly below gpt-5.6-sol on capability, cheaper per token, and the model the codex lane fails over to. Best bounded judgment and accounting: self-adjudicates within scope and defends the reasoning openly in ASSUMPTIONS rather than stopping or going silent; also the best finder of adjacent issues. Weaknesses: verbose reports, slowest wall-clock, and its lane drops tool junk (`.codegraph/`, `.omo` — opencode tooling) into the tree — sweep for and remove it after every opencode run, before diff review.
- **sonnet-5** — fastest, cheapest path to a correct result on well-specified mechanical work (one pass, byte-parity with an approved original). Weakness: **silent deviation** — applies pre-adjudicated amendments without surfacing them and leaves the thinnest deviation trail; on a plan where the amendment *hadn't* been adjudicated, that same silence is a REVISE. Its briefs restate the reporting contract explicitly: *record every deviation, however small*.

**Routing rules** — the CEO applies these when staffing the chart:

1. **Quota preservation.** The session model's quota is the scarcest budget in the run — spend it only where intelligence compounds: orchestration, judgment, vetting, verdicts, assembly. Worker-tier units (lens sweeps, audit categories, well-specified execution, mechanical analysis) go to a provider-CLI lane whenever one is installed; native subagents are the worker-tier *fallback*, not the default.
2. **The Lane column binds.** A roster model is dispatched only through its listed lane. OpenRouter also serves Claude models (`openrouter/anthropic/claude-sonnet-5`, …), so the `opencode` lane *can* reach them — never route it: that swaps included-subscription quota for pay-per-token spend, drops the harness's native dispatch surface, and voids rule 7's different-provider independence (and `--variant` flags are silently ignored off glm-5.2, so effort quietly vanishes). Rule 1 offloads worker-tier *units* to cheaper CLI-lane models; it never re-lanes a Claude model. A named model unavailable on its lane falls back *within* the lane: native Claude tiers descend to the **sonnet-4.6 floor** — never lower, never Haiku (rule 8), never sideways into a CLI lane; an unavailable CLI-lane model is a preflight **reassign** (constraints below).
3. **Defaults, not limits.** Standing permission to escalate: judge the output, not the price tag. A cheaper model's return that doesn't meet the bar is redone one tier up without asking — escalating costs less than shipping mediocre work (the escalation ladder already encodes this).
4. **Intelligence > taste > cost** when axes conflict for anything that ships; cost is a tie-breaker only.
5. **Coding and bulk/mechanical work** (clear-spec execution, migrations, data analysis, lens sweeps) → gpt-5.6-sol, as much of it as clears the taste bar — at ~30× Claude quota it is effectively free, so don't ration it. Don't let cost pick the wrong model either way: use the cheap lane to gather information and try things *before* moving work to an expensive tier. glm-5.2 xhigh is the second bulk lane — an independent perspective, or the substitute when `codex` is absent or its limits exhausted (and the coding fallback for opus-4.8 when native quota should be preserved).
6. **Anything user-facing** (UI, copy, API design) needs taste ≥ 7 — on current weights that is gpt-5.6-sol, glm-5.2 xhigh (at the line), or a Claude tier; among those, quota preservation (rule 1) picks the lane. Below-7 models never ship user-facing work.
7. **Verdicts and reviews stay with the CEO.** Plan/implementation reviews sit at fable-5 or opus-4.8; additionally commission an independent second-opinion review from a *different provider* (read-only CLI run — default gpt-5.6-sol, near-free at its quota, so do it liberally on anything non-trivial) — advisory input to the verdict, never the verdict itself. On high severity or user request, the single second opinion widens to the **judge panel** (`closing-the-loop.md` "The judge panel"): same principle, N raters instead of one, still advisory — an escalation, never the default.
8. **Never staff Haiku.** The cheap tier is a CLI lane — or sonnet-5 at low effort when no CLI is installed (floor per rule 2: sonnet-4.6).

**Rung staffing with the roster:**

| Rung | Default staffing |
|---|---|
| CEO | the session model — never offloaded |
| Manager | opus-4.8 (native); fable-5 for the hardest campaign legs |
| Worker | gpt-5.6-sol (`codex`) or glm-5.2 xhigh (`opencode`); sonnet-5 when no CLI lane exists |
| Executor | per plan: mechanical, well-specified → a CLI lane; taste-sensitive or user-facing diffs → gpt-5.6-sol (taste 8, quota-free) or opus-4.8 / sonnet-5 native |

**Model labeling — every running thing announces its model.** The harness UI shows *its own* model for a wrapper agent and nothing at all for a shell run, so the label is often the only truth about who is actually working. The rule, applied to every dispatch without exception:

- **Agents / subagents / workflow calls**: label (or description) starts with the true worker's model — `gpt-5.6-sol:review-auth`, `glm-5.2:lens-data`, `opus-4.8:manager-billing`. For a wrapper (a native agent that shells out to a CLI lane), the prefix names the *real* worker, not the wrapper — the UI will show the wrapper's Claude model, so the label is the only indication the work is gpt-5.6-sol's.
- **Shell runs**: the run's stated description carries the model — `[gpt-5.6-sol] audit: security lens`, so a background `codex`/`opencode` process is identifiable at a glance.
- **Worktrees & branches**: encode plan and model in the path — worktree `../<repo>-wt/<plan-id>-gpt-5.6-sol/`, generated branches stay `advisor/<plan-id>` (the worktree path carries the model; a branch name outlives the run and shouldn't).
- **Run record / heartbeat log**: every dispatch line states model + effort + lane (`gpt-5.6-sol @ high via codex-MCP`), so the record is reproducible and a stuck run is attributable without archaeology.

**Dispatch transports** — each provider lane is reachable two ways; prefer MCP where registered, shell everywhere else (all shapes below live-verified, codex 0.142.5 / opencode 1.17.13):

| Transport | codex | opencode | Use when |
|---|---|---|---|
| **MCP server** | `codex mcp-server` → tools `codex` (new thread) / `codex-reply` (continue by `threadId`) | vendored `scripts/opencode-mcp.mjs` over `opencode serve` → `opencode_run` / `opencode_fire` / `opencode_status` / `opencode_wait` / `opencode_steer` / `opencode_abort` | orchestrator-side dispatch: structured ids in the result, live progress events, steerable sessions (mid-run on opencode; between turns on codex) |
| **Shell run** | `codex exec --json` | `opencode run --format json` | no MCP registration; a harness without MCP; or dispatch from *inside a subagent* — subagent→MCP calls fail unreliably on some harnesses, shell is the universal fallback |

One-time registration (Claude Code shown; other MCP clients take the same commands):

```bash
claude mcp add --scope user codex -- codex mcp-server
claude mcp add --scope user opencode -- node <explore-repo>/skills/explore/scripts/opencode-mcp.mjs
```

The wrapper auto-starts `opencode serve` (port 4096; `OPENCODE_PORT` overrides) and roots every call at its `directory` argument, so one server drives every repo and worktree. (Broad alternative: the `opencode-mcp` npm package — ~80 tools; the vendored wrapper stays at six on purpose.)

**MCP call shapes** — arguments mirror the shell flags:

- **Worker**: `codex {prompt, sandbox: "read-only", cwd: <repo-root>, approval-policy: "never", config: {model_reasoning_effort: "<effort>"}}` → final text + `threadId`. `opencode_run {prompt, directory: <repo-root>, model: "openrouter/z-ai/glm-5.2", variant: "xhigh"}` → final text + `session_id`.
- **Executor**: the same with `sandbox: "workspace-write", cwd: <worktree>` / `directory: <worktree>`. Installs need network: `config: {sandbox_workspace_write: {network_access: true}}`, stated in the run record. An opencode executor over MCP only works where the host's opencode config already grants writes — on a write-gated config it stalls on permission asks, so the shell `opencode run --auto` form below is the executor default for that lane.
- **REVISE / continue** (the agent finished its turn; you send the next one): `codex-reply {threadId, prompt}` — the live server retains the thread's cwd and sandbox. **The codex thread registry is per-server-process**: if the MCP server restarted since dispatch, fall back to shell `codex exec resume` with confinement restated (below) — thread ids interoperate between the two transports. opencode: `opencode_run {session_id, prompt, directory}`.
- **Mid-run steer** (the agent is still working and heading wrong): `opencode_steer {session_id, prompt}` aborts the in-flight turn and redirects the same session — a true interrupt; `opencode_fire` → `opencode_status` is the async dispatch-plus-heartbeat pair that makes it possible. codex has no mid-turn interrupt over MCP — steer it between turns (`codex-reply`), or kill the shell run and resume.
- **opencode permission gating rides the host's opencode config through both transports.** An async run stuck in `running` with no new output is usually a pending permission ask — steer or abort it, or dispatch that unit as a shell `opencode run --auto` confined to the worktree.

**Shell command shapes** (adjust model ids to the host's config):

Read-only worker — Phase-2 lens, audit category, second-opinion review:

```bash
codex exec --json -s read-only -C <repo-root> -c model_reasoning_effort=<low|medium|high|xhigh> \
  -o <report-file> "<self-contained brief>"
opencode run -m openrouter/z-ai/glm-5.2 --variant xhigh --format json --dir <repo-root> \
  "<self-contained brief>"
```

The read-only guarantees differ by lane: **codex `-s read-only` is an OS-level sandbox** — that worker cannot mutate the tree even if its reasoning goes wrong. **opencode's default-deny permissions are application-level gating**, and config-dependent (a host config that allows edits weakens them) — cheap insurance is the executors' main-tree check (below) after an opencode worker run too. Direct `-o <report-file>` (and any captured stdout) into a scratch directory or a path this skill owns — never into the user's working tree (the analyzers' `--output` rule, applied to runners).

Executor — `--execute-level`, confined to the disposable worktree:

```bash
codex exec --json -s workspace-write -C <worktree> -c model_reasoning_effort=<effort> \
  -o <report-file> "<plan, inlined, + executor preamble>"
opencode run -m openrouter/z-ai/glm-5.2 --variant <high|xhigh> --format json --dir <worktree> --auto \
  "<plan, inlined, + executor preamble>"
```

The two lanes confine differently — know which guarantee you're holding. **codex `workspace-write` rooted at the worktree is an OS-level sandbox** — writes outside it are blocked by construction, so Hard Rules 1–2 hold mechanically; prefer this lane for execution when both exist. (It also blocks *network* by default — a plan whose steps need dependency installs either gets `-c sandbox_workspace_write.network_access=true` on dispatch, stated in the run record since it widens the sandbox to the network, or the orchestrator pre-installs dependencies in the worktree before dispatching.) **opencode `--auto` is permission auto-approval, not filesystem confinement** — the worktree boundary rides on the brief and on review: after any `--auto` run, verify the user's working tree is untouched (`git -C <repo-root> status --porcelain` unchanged) *before* reviewing the worktree diff, and treat any main-tree write as an automatic BLOCK. Keep `-o <report-file>` inside the worktree or scratch. Never `danger-full-access` for workers or executors — the **computer-use verification lane** below is the one sanctioned exception; never `--auto` outside a worktree.

Steering / REVISE — continue the same session instead of re-briefing from zero. **A resumed run inherits no confinement you don't restate**: `codex exec resume` has no `-s`/`-C` flags and re-roots its sandbox at the *invocation cwd* — resuming an executor from the repo root would put the user's tree inside the write scope. Always resume from the same working root and re-pass the dispatch's confinement:

```bash
# executor rounds — run FROM INSIDE the worktree, restate the sandbox:
cd <worktree> && codex exec resume <session-id> -c sandbox_mode="workspace-write" "<review feedback>"
opencode run -s <session-id> --dir <worktree> --auto "<review feedback>"

# read-only rounds — same rule with the read-only scope:
cd <repo-root> && codex exec resume <session-id> -c sandbox_mode="read-only" "<narrowed brief>"
opencode run -s <session-id> --dir <repo-root> "<narrowed brief>"
```

Session ids: the MCP transport returns them structured (`threadId` / `session_id` in the tool result); the shell transport emits them in the JSONL events (`thread.started` carries `thread_id`). `codex exec resume --last` and `opencode run -c` (continue-last) are fallbacks **only when a single dispatch is in flight**. The main-tree check runs after *every* CLI round that can write — not just the first.

**Codex lane quirks** — verified on codex-cli 0.142.5; know these before dispatching:

- **Timeout.** A codex run routinely outlives a harness shell tool's cap (Claude Code Bash: 10 min default). Either pass an explicit generous timeout, or — better for anything non-trivial — run it in the background and poll for the `-o <report-file>` to appear; the report file, not the process exit, is the completion signal.
- **Stdin hang.** `codex exec` reads stdin whenever it isn't a TTY (`Reading additional input from stdin...`) — a background or harness shell leaves the pipe open and the run blocks forever *before doing anything*. Always close it: `codex exec … "<prompt>" </dev/null`. (Hit live on 0.142.5.)
- **`-o <file>`** writes only the *final* agent message — capture stdout separately (`--json` JSONL events) if you need the trail.
- **`--output-schema <file>`** (JSON Schema) forces a structured final response — use it when the orchestrator must parse the result instead of reading prose.
- **`--add-dir <dir>`** grants an extra writable directory alongside the sandbox root — how a read-confined or repo-confined run gets a scratch/artifact directory.
- **`--skip-git-repo-check`** is required whenever `-C` points outside a git repo (scratch dirs, artifact dirs).
- **`--ephemeral`** skips session persistence — no resume possible; don't use it for anything that might need a REVISE round.
- **Model default** rides `~/.codex/config.toml` (gpt-5.6-sol here) — name `-m` only to deviate.
- Resume re-roots and drops confinement — already covered above; it is the sharpest quirk of the lot.

**Computer-use verification lane (codex)** — gpt-5.6-sol through `codex` is also the **local verification agent** for work that needs a real runtime observed: driving a UI flow, browser automation, iOS/Android simulators, launching a desktop app, capturing screenshots, or any independent runtime check outside the orchestrator's own context. Not for ordinary code reading, typecheck, lint, or tests a normal worker can run. In this skill it slots in as an *observer*, mainly at Phase-5 review time (verify an executed diff actually behaves — see `closing-the-loop.md`) and during recon/audit when a finding needs runtime confirmation. The flow (live-verified end-to-end):

```bash
ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-computer-use.XXXXXX")"
REPORT="$ARTIFACT_DIR/report.md"
PROMPT="$ARTIFACT_DIR/prompt.md"

# 1. Write a self-contained prompt to $PROMPT: repo/worktree path, the exact
#    flow to drive, constraints (what NOT to touch), $ARTIFACT_DIR as the only
#    write target, and the report format. Then:
codex exec \
  -C "$PWD" \
  --add-dir "$ARTIFACT_DIR" \
  -s danger-full-access \
  -o "$REPORT" \
  "$(cat "$PROMPT")" </dev/null    # close stdin — see the stdin-hang quirk
# 2. Read $REPORT, inspect/reference the screenshot paths, summarize.
```

Sandbox selection: `-s danger-full-access` **only** for genuine GUI automation, simulators, desktop app launching, screenshots, or access outside the repo — it is unsandboxed, so the brief itself is the only constraint: keep it observe-and-report, never destructive. For non-GUI runtime checks that need only the repo + artifact dir, prefer `-s workspace-write`. Add `--skip-git-repo-check` when `-C` isn't a git repo. Artifacts and report live in `$ARTIFACT_DIR` (scratch), never the user's tree. Launching apps/simulators/browsers to verify the requested work needs no permission ask; anything that would disrupt the user's environment beyond that (closing their apps, changing system settings, acting on real accounts or data) does. Label the run `[gpt-5.6-sol] computer-use: <flow>` per the labeling rule.

**gpt-5.6-sol inside native workflow fan-outs (wrapper pattern).** A harness's workflow/agent `model` parameter takes only native models — it cannot name gpt-5.6-sol. To put codex work inside a native fan-out, spawn a **thin native wrapper** (cheapest native tier, low effort) whose brief is: write the self-contained codex prompt, run `codex exec` via shell, return the report (structured output on the wrapper if the harness supports it). Rules that keep the pattern honest: label the wrapper `gpt-5.6-sol:<task>` (labeling rule above — the UI shows the wrapper's model, the label is the only truth); parallel codex *implementation* wrappers each get an isolated worktree, or their edits collide in the shared checkout; and a harness token budget counts only native tokens — codex work is invisible to it, so budget math must not read "cheap" as "idle".

**Minion platforms — tier-3 nesting.** Both lanes can spawn their *own* native subagents, so one lane dispatch can be a **manager with minions** instead of a single worker:

- **codex**: `multi_agent` (stable and default-on at 0.142.5) — collab tools `spawn_agent` / `wait` / `close_agent`, child threads at depth 1 by default. Codex spawns **only when the brief explicitly asks** ("spawn one worker per X, wait for all, merge").
- **opencode**: task-tool subagents (built-ins `explore` / `general`, or named agents from the host's config); child sessions are inspectable at `GET /session/{id}/children`. A subagent's model is fixed by its agent config, not chooseable per call — pre-declare one agent per role×tier where that matters.

Two rules keep nesting inside the org chart. **The `--depth` caps bound total concurrent agents *including* platform-spawned minions** — the platform's spawns don't report to the harness, so a fan-out brief must carry its own cap ("at most N minions"). And **a platform that fans out is a manager**: its brief carries the end goal and direction, it vets its minions' returns before reporting one merged result up, and Phase-3 vetting of that merged result still happens on your side.

**Effort mapping** — `--execute-level` (and the auto-pick) translated per lane:

| Level | codex `model_reasoning_effort` | opencode glm-5.2 `--variant` | Native Claude |
|---|---|---|---|
| low | `low` | `high` *(clamped — glm-5.2 exposes only `high`/`xhigh`; state the clamp)* | low |
| medium | `medium` | `high` | medium |
| high | `high` | `high` | high |
| max | `xhigh` | `xhigh` | max |

The same values ride both transports: codex takes `-c model_reasoning_effort=<v>` on shell and `config: {model_reasoning_effort: "<v>"}` over MCP; opencode takes `--variant <v>` on shell and `variant: "<v>"` over MCP.

**CLI-runner constraints** — so the org chart holds across lanes:

- **One shell run = one unit.** A shell run emits no mid-run heartbeat; its single terminal return *is* the heartbeat. Keep those briefs one well-specified unit small, and apply spiral detection *across runs* — a resumed run that restates its previous return rather than advancing is a spiral signal. The MCP transport loosens this: `opencode_status` polls are real heartbeats (and codex streams progress events where the harness surfaces them), so longer units are steerable there — the steering protocol below applies to them unchanged.
- **Briefs carry identical obligations:** self-contained (Hard Rule 3), Hard Rules 4 and 6 verbatim, the raise-hand rule verbatim, the report format when executing — and they compress under `--caveman` exactly like native subagent prompts (auto-clarity holds).
- **Returns are vetted like any worker's** — Phase-3 confirmation against the code before anything is recorded. A different provider does not change the trust model: a return is a claim, not a fact, and Rule 6 applies to what the runner read *and* to what it sent back.
- **Preflight before staffing a lane:** run the mandatory probe below and pick the transport while you're there (MCP tools visible → MCP; else shell). A lane failing mid-run is a **reassign** steer — move the unit to the next lane and record it; never route around a failed lane by silently spending the session model.

**Preflight probe — mandatory, once per run**

**When.** At Phase-1 recon, before the first dispatch of any run that will staff a CLI lane. Re-probe a lane only when it later fails, then apply the reassign rule above.

**Probe ladder.** Run cheapest first and stop at the first failure for each lane:

1. **Presence:** `command -v codex opencode`.
2. **Model availability:** for codex, `codex exec -s read-only -c model_reasoning_effort=low "Reply with exactly: OK" </dev/null` (auth + model, ~2k tokens); for opencode, `opencode models | grep -F "<model-id>"` (model listed, free, no API call).
3. **Transport health:** check only the transport the run will use. For MCP, make one minimal MCP call per lane (a codex tool call or `opencode_run`); a shell lane needs no extra check beyond the model ping.

**Stale-transport failure shapes and refresh**

| Transport | Stale symptoms | Refresh |
|---|---|---|
| `codex mcp-server` | API 400 `"The '<model>' model requires a newer version of Codex"` via MCP while `codex exec` in a fresh shell works. | Reconnect/restart the registered `codex` MCP server (on Claude Code: `/mcp` → reconnect). Reconnect loses the per-process thread registry → continue old threads with `codex exec resume <threadId>`. |
| `opencode serve` | Any one: wrapper error `opencode serve did not come up on http://127.0.0.1:4096 within 15s` while `lsof -nP -i :4096` shows a listener; or `curl -s -m 5 http://127.0.0.1:4096/session/status` returning `{"name":"UnknownError",...}`; or serve process start date predating the installed binary's upgrade. | `kill <serve-PID>` — verify the PID's command is `opencode serve` first. The wrapper auto-respawns a fresh serve on the next call. Sessions are not lost (opencode persists sessions on disk). |

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
