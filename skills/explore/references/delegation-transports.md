# Delegation transports & lane mechanics

The per-lane dispatch doctrine moved out of `references/delegation.md`: verified MCP/shell call shapes, lane quirks, sandbox and confinement rules, effort mapping, hang recovery, chunked dispatch, and the stale-transport failure-shapes table. `references/delegation.md` still governs the org chart, the model roster & routing, and the preflight probe — **when** to staff a lane; this file is **how** to talk to it. Read it per lane, only for lanes that exist on this host: codex installed → the codex sections; opencode → its opencode sections; inside herdr → the herdr transport section; computer-use verification → its section.

**Dispatch transports** — each provider lane is reachable two ways; prefer MCP where registered, shell everywhere else. **Verification is per shape, not blanket**: each shell shape carries its own pin below, and the MCP shapes are verified against the *serve* version, which can trail the CLI. Live today: codex CLI **0.145.0**; opencode CLI **1.18.6**, `opencode serve` **1.18.6**. (Shapes first verified on codex 0.142.5 / opencode 1.17.13.)

For the opencode lane, **MCP is the dispatch default where registered; shell is the fallback**: two 2026-07-11 shell review runs stalled with zero output while the same brief returned over MCP in seconds.

| Transport | codex | opencode | Use when |
|---|---|---|---|
| **MCP server** | `codex mcp-server` → tools `codex` (new thread) / `codex-reply` (continue by `threadId`) | vendored `scripts/opencode-mcp.mjs` over `opencode serve` → `opencode_run` / `opencode_fire` / `opencode_status` / `opencode_wait` / `opencode_steer` / `opencode_abort` / `opencode_health` | orchestrator-side dispatch: structured ids in the result, live progress events, steerable sessions (mid-run on opencode; between turns on codex) |
| **Shell run** | `codex exec --json` | `opencode run --format json` | no MCP registration; a harness without MCP; or dispatch from *inside a subagent* — subagent→MCP calls fail unreliably on some harnesses, shell is the universal fallback |

One-time registration (Claude Code shown; other MCP clients take the same commands):

```bash
claude mcp add --scope user codex -- codex mcp-server
claude mcp add --scope user opencode -- node <explore-repo>/skills/explore/scripts/opencode-mcp.mjs
```

The wrapper auto-starts `opencode serve` (port 4096; `OPENCODE_PORT` overrides) and roots every call at its `directory` argument, so one server drives every repo and worktree. (Broad alternative: the `opencode-mcp` npm package — ~80 tools; the vendored wrapper stays at seven on purpose. `opencode_health` is the report-only seventh: server reachability + version, wrapper version, session counts — it never starts or heals anything.)

**herdr transport** — inside a herdr session (`HERDR_ENV=1`; the plugin's SessionStart hook announces it), pane agents are a third dispatch surface, preferred over bare-shell background runs for interactive agents (visible to the operator, steerable, survive the session). All herdr CLI commands return JSON. Worker dispatch: split an unfocused pane (`herdr pane split --current --direction down --ratio 0.3 --no-focus --cwd <root>` → returns the new `pane_id`), then `herdr agent start <label> --kind <roster-lane-kind> --pane <id> --timeout 60000` (kinds include `opencode`, `codex`, `claude`, `pi`, `gemini`, `cursor`, `cline`, `omp`, `kimi`, `amp`, `grok`, …) → `interactive_ready: true`; then `herdr agent prompt <label> "<brief>" --wait --until idle --until blocked`, then `herdr agent read <label>` (sources `recent` | `screen`). Executor dispatch is the same with `--cwd <worktree>` (herdr also has a `worktree` command group — unverified). Heartbeats: poll `herdr agent get/list` state (`idle` / `working` / `blocked` / `done` / `unknown`), mapped onto the 10-minute watch. Steer: `herdr agent prompt` on idle. `blocked` = a pending approval inside the pane agent — surface to the operator, never auto-answer. Close the panes you opened (`herdr pane close <pane_id>`). Staffing/labeling rules are unchanged (the brief carries model + effort; the effective roster picks the model; `--kind` maps to the lane's CLI). Usage: prefer the `tokens` field from `herdr agent list` when the usagebar plugin is installed — observed live shape `{"context":"⛁ 52% (516k)","limit":"5h 100%","provider":"claude","title":"Explore"}` — else fall back to `usage_probe.py`; record which surface served in the run record. Verified on herdr 0.8.x, 2026-08-16; the `worktree` command group and the usagebar-absent path are unverified.

**MCP call shapes** — arguments mirror the shell flags:

- **Worker**: `codex {prompt, sandbox: "read-only", cwd: <repo-root>, approval-policy: "never", config: {model_reasoning_effort: "<effort>"}}` → final text + `threadId`. `opencode_run {prompt, directory: <repo-root>, model: "openrouter/z-ai/glm-5.2", variant: "xhigh"}` → final text + `session_id`.
- **Executor**: the same with `sandbox: "workspace-write", cwd: <worktree>` / `directory: <worktree>`. For codex in a linked worktree, the worktree-commit executor shape (verified 0.144.1, re-verified 0.144.5, and re-verified on 0.145.0 over **both transports** 2026-07-27 — shell `-c` and, after an MCP reconnect, the MCP transport itself, including a `codex-reply` continuation that retained the thread's cwd and sandbox with no restated confinement. A registered `codex mcp-server` keeps its at-spawn binary, so after any CLI upgrade its MCP shapes count as re-pinned only once the server is reconnected) also passes `config: {sandbox_workspace_write: {writable_roots: ["<main-repo>/.git/worktrees/<wt-name>", "<main-repo>/.git/objects", "<main-repo>/.git/refs", "<main-repo>/.git/logs"]}}`. Installs need network: `config: {sandbox_workspace_write: {network_access: true}}`, stated in the run record. An opencode executor over MCP works where the host's opencode config grants writes; otherwise a write-gated config stalls on permission asks, and shell `opencode run --auto` is the executor default **only** for that config.
- **REVISE / continue** (the agent finished its turn; you send the next one): `codex-reply {threadId, prompt}` — the live server retains the thread's cwd and sandbox. **The codex thread registry is per-server-process**: if the MCP server restarted since dispatch, fall back to shell `codex exec resume` with confinement restated (below) — thread ids interoperate between the two transports. opencode: `opencode_run {session_id, prompt, directory}`.
- **Mid-run steer** (the agent is still working and heading wrong): `opencode_steer {session_id, prompt}` aborts the in-flight turn and redirects the same session — a true interrupt; `opencode_fire` → `opencode_status` is the async dispatch-plus-heartbeat pair that makes it possible. codex has no mid-turn interrupt over MCP — steer it between turns (`codex-reply`), or kill the shell run and resume.
- **opencode permission gating rides the host's opencode config through both transports.** An async run stuck in `running` with no new output is usually a pending permission ask — steer or abort it, or dispatch that unit as a shell `opencode run --auto` confined to the worktree.
- **`stalled: true` from `opencode_wait` is a dead prompt, not a slow one.** The session sat ~30s with no running signal and no assistant record for the prompt: it died server-side after the 204 (log fingerprint `prompt_async failed` — bad model id, provider/stream error such as an OpenRouter 502 or socket close, or a pending permission ask). Waiting longer never flips it: run `opencode_health`, fix what it shows (model id, stale wrapper), re-fire the same session once, then reassign the lane if it stalls again. A turn that has *started* (in-flight assistant record) never reads as stalled, however long it thinks.
- **1.18.3+ `/session/status` regression — wrapper ≥ v1.3.0 required.** On opencode 1.18.3 `GET /session/status` returns `{}` even while a session is actively generating (re-probed on serve 1.18.6, 2026-07-27: still `{}` mid-generation — not fixed upstream), and the assistant message record is created at turn start (`info.time.completed` unset while streaming, stamped with `finish` on completion). Wrapper v1.3.0 tracks running/replied from the completed stamp; a wrapper ≤ v1.2.0 against 1.18.3 misreads every async dispatch — `opencode_wait` returns instantly with empty text, and a follow-up prompt then aborts the still-running turn (log fingerprint: paired `error=Aborted` on one session). After any opencode upgrade, reconnect the MCP wrapper and confirm `opencode_health` → `wrapper_version` ≥ 1.3.0.

**Shell command shapes** (adjust model ids to the host's config):

Read-only worker — Phase-2 lens, audit category, second-opinion review (the codex shape here is verified on codex CLI **0.145.0**, 2026-07-27):

```bash
codex exec --json -s read-only -C <repo-root> -c model_reasoning_effort=<low|medium|high|xhigh> \
  -o <report-file> "<self-contained brief>" </dev/null
opencode run -m openrouter/z-ai/glm-5.2 --variant xhigh --format json --dir <repo-root> \
  "<self-contained brief>"
```

The read-only guarantees differ by lane: **codex `-s read-only` is an OS-level sandbox** — that worker cannot mutate the tree even if its reasoning goes wrong. **opencode's default-deny permissions are application-level gating**, and config-dependent (a host config that allows edits weakens them) — cheap insurance is the executors' main-tree check (below) after an opencode worker run too. Direct `-o <report-file>` (and any captured stdout) into a scratch directory or a path this skill owns — never into the user's working tree (the analyzers' `--output` rule, applied to runners). Output beyond the brief's stated budget is **spilled**, not inlined: persisted to a scratch file behind an opaque locator plus a one-line retrieval hint in the report (`references/context-architecture.md` "Spill").

Executor — `--execute-level`, confined to the disposable worktree:

```bash
codex exec --json -s workspace-write -C <worktree> \
  --add-dir <main-repo>/.git/worktrees/<wt-name> \
  --add-dir <main-repo>/.git/objects \
  --add-dir <main-repo>/.git/refs \
  --add-dir <main-repo>/.git/logs \
  -c model_reasoning_effort=<effort> \
  -o <report-file> "<plan, inlined, + executor preamble>" </dev/null
opencode run -m openrouter/z-ai/glm-5.2 --variant <high|xhigh> --format json --dir <worktree> --auto \
  "<plan, inlined, + executor preamble>"
```

The two lanes confine differently — know which guarantee you're holding. **codex `workspace-write` rooted at the worktree is an OS-level sandbox** — writes outside it are blocked by construction, so Hard Rules 1–2 hold mechanically; prefer this lane for execution when both exist. (It also blocks *network* by default — a plan whose steps need dependency installs either gets `-c sandbox_workspace_write.network_access=true` on dispatch, stated in the run record since it widens the sandbox to the network, or the orchestrator pre-installs dependencies in the worktree before dispatching.) **opencode `--auto` is permission auto-approval, not filesystem confinement** — the worktree boundary rides on the brief and on review: after any `--auto` run, verify the user's working tree is untouched (`git -C <repo-root> status --porcelain` unchanged) *before* reviewing the worktree diff, and treat any main-tree write as an automatic BLOCK. Keep `-o <report-file>` inside the worktree or scratch. Never `danger-full-access` for workers or executors — the **computer-use verification lane** below is the one sanctioned exception; never `--auto` outside a worktree.

**Linked-worktree git metadata.** A linked worktree keeps its index and refs under the main repo's `.git/worktrees/<name>/`, outside the worktree-rooted sandbox; without the extra roots, `git add` and `git commit` fail (verified on 0.144.1, re-verified on 0.144.5 and again on 0.145.0, 2026-07-27 — both the failure repro and the extra-roots commit success) with `fatal: Unable to create '<main-repo>/.git/worktrees/<wt-name>/index.lock': Operation not permitted`. The executor shape grants the narrow set required for normal commits and leaves top-level `<main-repo>/.git/config`, `hooks/`, and `packed-refs` read-only, so the executor cannot install main-repo git hooks or rewrite core config. If an operation needs a top-level path the set misses — for example `packed-refs` after `git gc` — the live-verified fallback is one broad `--add-dir <main-repo>/.git`, accepting that hooks/config write exposure (verified on codex-cli 0.145.0, 2026-07-29 — the narrow set reproduced the `packed-refs.lock` failure, exit 128; the broad root succeeded, exit 0, with the main tree untouched). Re-test outside `/tmp`: codex includes `/tmp` in `workspace-write` by default, masking the failure.

Steering / REVISE — continue the same session instead of re-briefing from zero. **A resumed run inherits no confinement you don't restate**: `codex exec resume` has no `-s`/`-C` flags and re-roots its sandbox at the *invocation cwd* — resuming an executor from the repo root would put the user's tree inside the write scope. Always resume from the same working root and re-pass the dispatch's confinement:

```bash
# executor rounds — run FROM INSIDE the worktree, restate the sandbox and roots
# (extra-roots resume shape verified on codex-cli 0.144.1; re-verified on 0.145.0, 2026-07-27):
cd <worktree> && codex exec resume <session-id> -c sandbox_mode="workspace-write" \
  -c 'sandbox_workspace_write.writable_roots=["<main-repo>/.git/worktrees/<wt-name>","<main-repo>/.git/objects","<main-repo>/.git/refs","<main-repo>/.git/logs"]' \
  "<review feedback>" </dev/null
opencode run -s <session-id> --dir <worktree> --auto "<review feedback>"

# read-only rounds — same rule with the read-only scope:
cd <repo-root> && codex exec resume <session-id> -c sandbox_mode="read-only" "<narrowed brief>" </dev/null
opencode run -s <session-id> --dir <repo-root> "<narrowed brief>"
```

Session ids: the MCP transport returns them structured (`threadId` / `session_id` in the tool result); the shell transport emits them in the JSONL events (`thread.started` carries `thread_id`). `codex exec resume --last` and `opencode run -c` (continue-last) are fallbacks **only when a single dispatch is in flight**. The main-tree check runs after *every* CLI round that can write — not just the first.

**Codex lane quirks** — shell and MCP shapes verified through codex-cli 0.145.0 (read-only, worktree-commit, extra-roots resume, stdin-hang, and the MCP executor + `codex-reply` shapes all re-verified 2026-07-27); know these before dispatching:

- **Timeout.** A codex run routinely outlives a harness shell tool's cap (Claude Code Bash: 10 min default) — a foreground run killed at the cap surfaces as **`failed with exit code 144`** and loses everything it did. Either pass an explicit generous timeout, or — better for anything non-trivial — run it in the background and poll for the `-o <report-file>` to appear; the report file, not the process exit, is the completion signal. Cadence and chunking: "Chunked dispatch & the 10-minute watch" below.
- **Stdin hang.** `codex exec` reads stdin whenever it isn't a TTY (`Reading additional input from stdin...`) — a background or harness shell leaves the pipe open and the run blocks forever *before doing anything*. Always close it: `codex exec … "<prompt>" </dev/null`. (Hit live on 0.142.5; re-tested and still present on 0.144.5 and on 0.145.0 — a 0.145.0 run with the pipe held open blocked indefinitely at the stdin message, 2026-07-27. A pipe that delivers EOF proceeds normally; the hang needs the pipe *held open*, so the closure stays mandatory.)
- **`-o <file>`** writes only the *final* agent message — capture stdout separately (`--json` JSONL events) if you need the trail.
- **`--output-schema <file>`** (JSON Schema) forces a structured final response — use it when the orchestrator must parse the result instead of reading prose.
- **`--add-dir <dir>`** grants an extra writable directory alongside the sandbox root — how a read-confined or repo-confined run gets a scratch/artifact directory.
- **Worktree git metadata.** Linked-worktree dispatch needs the extra writable roots; covered in the executor shape above.
- **`--skip-git-repo-check`** is required whenever `-C` points outside a git repo (scratch dirs, artifact dirs).
- **`--ephemeral`** skips session persistence — no resume possible; don't use it for anything that might need a REVISE round.
- **Model default** rides `~/.codex/config.toml` (gpt-5.6-sol here) — name `-m` only to deviate.
- Resume re-roots and drops confinement — already covered above; it is the sharpest quirk of the lot.

**opencode lane quirks** — verified on opencode 1.17.18 (2026-07-11/12 runs); lane re-verified on serve **1.18.6** (2026-07-27: stale-serve kill → wrapper v1.4.0 self-heal respawn on the 1.18.6 binary, then sync `opencode_run` and async `opencode_fire`/`opencode_wait` glm-5.2 dispatches, all clean); know these before shell dispatch:

- **Shell-run lifetime.** macOS has no `timeout(1)`: `timeout 90 opencode run …` fails with `command not found: timeout`; harness shell caps kill long runs (Claude Code Bash: 2 min default, 10 min max — the kill surfaces as **`failed with exit code 144`**); and raw `&` runs die orphaned when the parent shell exits. Dispatch with an explicit generous timeout or harness-managed background; output, never the process, is the completion signal. Cadence and chunking: "Chunked dispatch & the 10-minute watch" below.
- **Host-plugin junk.** The host opencode plugin `oh-my-openagent` (`~/.config/opencode/opencode.json` `plugin: ["oh-my-openagent@latest"]`) drops the `.codegraph` symlink and `.omo/` directory at the session root on every dispatch and regenerates them on the next run. Sweep them after every opencode run before diff review, or remove the plugin from the config used for dispatch.
- **Node 24/undici crash (observed once, 2026-07-27; not reproducible on demand).** A TCP RST during connection establishment surfaced as an uncatchable `setTypeOfService EINVAL` process crash that can kill the lane mid-run; recovery is a wrapper respawn (client auto-restart where the harness supports it, otherwise a manual `/mcp` reconnect), and sessions persist on disk. Upstream: nodejs/undici#5544 (unconditional `setTypeOfService` in writeH1), fixed by undici PR #5547 — the crash class ends when the host Node bundles that fix; nothing left to file.
- **Gateway capacity-limit outage vs stale serve — the shell run is the discriminator.** An upstream provider capacity outage surfaces over MCP as `opencode_run` → `{"error":"APIError","text":""}` at cost 0 with no detail; the same model over shell `opencode run -m <model>` prints the real reason (`Service Unavailable: … provider capacity limits`). It is model-specific — sibling models on the same gateway keep working in the same window — where the stale-serve config-snapshot fingerprint (transport table below) fails dispatches regardless of model. Capacity outage → reassign or drop the model; killing the serve fixes nothing.
- **Out-of-root reads hang forever.** A minion brief requiring a read outside its session `directory` (vault paths, `/private/tmp`) trips an `external_directory` permission ask with no approver: the turn hangs permanently at `read:running`, cost 0, while `opencode_health` stays healthy (verified serve 1.18.15, 2026-08-16 — nothing in the health surface or `GET /session/{id}` shows the ask; only `GET /permission?directory=<session root>` does, and it returns `[]` without that query param). Inline the needed content into the brief instead; minion citations of out-of-root sources are marked "unverifiable here" for the orchestrator to verify. Wrapper ≥ v1.5.0 surfaces `possible_hang` / `in_flight_age_s` / `pending_permission` on `opencode_status` and `opencode_wait` once an in-flight turn has been silent past `OPENCODE_STALL_WARN_S` (default 300s) — report-only; it never answers the ask.

**Hang recovery ladder.** When a session is hung, spend nothing on the hung one until the healthy ones are safe. (1) **Harvest finished zombies first** — `opencode_wait` every *other* live session and collect its completed work before any process-level action; a serve restart discards in-flight turns across all sessions, so harvesting is not optional politeness, it is the only chance to keep that work. (2) **Abort the stuck session** (`opencode_abort`) — or fail it fast by denying the pending ask via `POST /permission/{requestID}/reply`; the wrapper stays report-only, so a deny is a deliberate operator action, not something a poll does for you. (3) **Restart the serve ONLY if a fresh in-root probe dispatch also hangs** — that is the session-level vs server-level discriminator: a hang confined to one session is the permission ask and a restart is pure loss, while a hang that reproduces on a clean in-root dispatch is the server. Cross-reference: the stale-transport table row for `opencode serve` covers config-snapshot staleness — different failure, different fix (there the dispatch *errors* rather than hanging, and killing the serve is the remedy rather than the last resort).

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

**Browser/devtools work rarely needs the unsandboxed lane anymore:** the codex host config ships `chrome-devtools` (chrome-devtools-mcp) and `playwright` MCP servers enabled, so web-runtime verification — driving pages, console/network reads, performance traces, screenshots of web flows — rides those MCP tools under plain `-s workspace-write`; state in the brief that the worker should use them. Sandbox selection: `-s danger-full-access` **only** for genuine OS-level GUI automation, simulators, desktop app launching, or access outside the repo — it is unsandboxed, so the brief itself is the only constraint: keep it observe-and-report, never destructive. For non-GUI runtime checks that need only the repo + artifact dir, prefer `-s workspace-write`. Add `--skip-git-repo-check` when `-C` isn't a git repo. Artifacts and report live in `$ARTIFACT_DIR` (scratch), never the user's tree. Launching apps/simulators/browsers to verify the requested work needs no permission ask; anything that would disrupt the user's environment beyond that (closing their apps, changing system settings, acting on real accounts or data) does. Label the run `[gpt-5.6-sol] computer-use: <flow>` per the labeling rule.

(Workspace-write variant of this flow re-verified on codex-cli 0.145.0, 2026-07-29: the artifact-dir observe-and-report dispatch completed, wrote `report.md`, and left the scratch repo clean; the host config entries for `chrome-devtools` and `playwright` were present with no disable flags, and both servers exposed tools in-session.)

**Effort mapping** — `--execute-level` (and the auto-pick) translated per lane:

| Level | codex `model_reasoning_effort` | opencode glm-5.2 `--variant` | Native Claude |
|---|---|---|---|
| low | `low` | `high` *(clamped — glm-5.2 exposes only `high`/`xhigh`; state the clamp)* | low |
| medium | `medium` | `high` | medium |
| high | `high` | `high` | high |
| max | `xhigh` | `xhigh` | max |

The same values ride both transports: codex takes `-c model_reasoning_effort=<v>` on shell and `config: {model_reasoning_effort: "<v>"}` over MCP; opencode takes `--variant <v>` on shell and `variant: "<v>"` over MCP.

**Chunked dispatch & the 10-minute watch** — how long work survives harness caps:

- **Chunk the brief, keep the session.** Any unit projected past ~10 minutes of wall-clock (a deep audit category, a multi-file execution, a whole-repo sweep) dispatches as **sections continued on one session**, never one monolithic brief: send section 1, read its return, send section 2 via `codex-reply` / `session_id` — the session retains context, so each later section carries only the delta, and a section is sized to finish inside the harness shell cap. A monolithic brief killed mid-run (exit 144) loses everything; a chunked session loses at most its current section. Section boundaries are the unit boundaries the org chart already uses — one lens, one category, one plan step.
- **The 10-minute watch.** Every dispatched agent, workflow, and shell run is checked **at least every 10 minutes until completion** — shell runs: poll for the report file (the completion signal); MCP sessions: `opencode_status` / `opencode_wait` rounds (`timeout_s: 600` *is* the cadence) / codex progress events — and on wrapper ≥ v1.5.0 each opencode check also reads `possible_hang` / `in_flight_age_s` / `pending_permission`, which answer "advancing?" directly and route a flagged session to the hang recovery ladder above rather than another patient wait; native agents and workflows: the harness's task-status surface. Each check answers the three heartbeat questions (advancing? aimed? needed?); two consecutive checks with no movement = the spiral ladder. Foreground waits past the cap are how exit-144 kills happen — background the run and watch it instead.

**Stale-transport failure shapes and refresh**

| Transport | Stale symptoms | Refresh |
|---|---|---|
| `codex mcp-server` | API 400 `"The '<model>' model requires a newer version of Codex"` via MCP while `codex exec` in a fresh shell works. | Reconnect/restart the registered `codex` MCP server (on Claude Code: `/mcp` → reconnect). Reconnect loses the per-process thread registry → continue old threads with `codex exec resume <threadId>`. |
| `opencode serve` | Any one: wrapper error `opencode serve did not come up on http://127.0.0.1:4096 within 15s` while `lsof -nP -i :4096` shows a listener; or `curl -s -m 5 http://127.0.0.1:4096/session/status` returning `{"name":"UnknownError",...}`; or serve process start date predating the installed binary's upgrade; or **config-snapshot staleness** — every dispatch to a model added to `~/.config/opencode/opencode.jsonc` *after* the serve spawned returns HTTP 500 `{"name":"UnknownError"}` while `opencode_health` still reads healthy (serve reads config at spawn; four live hits through 2026-08-16). | `kill <serve-PID>` — verify the PID's command is `opencode serve` first. The wrapper auto-respawns a fresh serve on the next call. Sessions are not lost (opencode persists sessions on disk). |
| `opencode-mcp.mjs` wrapper (registered MCP process) | Definitive check: `opencode_health` reports `wrapper_version` — compare against the on-disk `VERSION` in `scripts/opencode-mcp.mjs` (also logged at startup: `ready — opencode-mcp v<X>`); a mismatch is a stale wrapper. Legacy fingerprints: bare `fetch failed` error text (pre-self-heal — this fingerprint and the stale-wrapper row are documented in the 2.14.0 entry of `CHANGELOG.md`; the named errors that replaced bare `fetch failed` landed in 2.13.0), or behavior missing post-upgrade features while the on-disk wrapper is current. The long-lived process keeps executing pre-upgrade code until refreshed. | Reconnect the MCP server (Claude Code: `/mcp` → reconnect) or restart the session. Reconnect is drain-safe on wrapper ≥ v1.4.0 — the outgoing process drains in-flight calls up to 10s on stdin close instead of dropping them. opencode sessions persist on disk, so nothing is lost. |
