# Multi-Tier AI Coding Orchestration: Claude Code → Codex CLI / OpenCode → Minions

## TL;DR
- **This is buildable today with mostly off-the-shelf pieces.** The cleanest architecture makes Claude Code the orchestrator, wraps Codex CLI and OpenCode as stdio MCP servers (Codex has a native `codex mcp-server` mode; OpenCode is exposed via the mature `opencode-mcp` npm package or by shelling out to `opencode run`/`opencode serve`), and lets each tier-2 platform spawn its own tier-3 minions using its *native* multi-agent features (Codex `[agents]`/`spawn_agents`, OpenCode subagents via the Task tool).
- **The single most important constraint:** Claude Code's own subagents (`.claude/agents`, Task tool) **cannot reliably call MCP tools and, until v2.1.172, could not spawn nested subagents** — so you cannot naively make a Claude subagent be the thing that calls the Codex/OpenCode MCP server. Cross-provider fan-out must be driven either from the Claude Code **main thread**, or via **process-spawning** (a subagent runs `Bash` → `codex exec` / `opencode run`), not via MCP-from-subagent.
- **Real-time bidirectional steering is partial, not turnkey.** You get streaming JSON events (`codex exec --json`, `claude -p --output-format stream-json`, OpenCode `/event` SSE) and session resume for mid-course correction, plus MCP elicitation for approval round-trips. True "interrupt and redirect a running minion" requires custom glue (watch the event stream, `session.abort`, then `resume` with a new prompt).

## Key Findings

### Existing working integrations (inventory & maturity)
| Integration | What it does | Maturity |
|---|---|---|
| **Codex native `codex mcp-server`** | Turns Codex CLI into an MCP server exposing `codex` (new session) and `codex-reply` (resume by threadId) tools; per-call `model`, `sandbox`, `cwd`, `base-instructions` params | Official, production-grade (polished by ~v0.117) |
| **`opencode-mcp` (AlaeddineMessadi)** | Wraps OpenCode's headless HTTP API as an MCP server — **79 tools, 10 resources, 6 prompts with multi-project support** (npm v1.10.0); auto-starts `opencode serve`; works with Claude Code | Active npm package, frequently updated |
| **PAL MCP Server (formerly Zen) — `clink` tool** | Lets one CLI spawn another CLI as a subagent — per its README, *"Claude Code can spawn Codex subagents, Codex can spawn Gemini CLI subagents, etc. … Each subagent returns only final results"*; multi-model consensus/planner/codereview workflows | **11.2k stars, 958 forks** (BeehiveInnovations/pal-mcp-server), Apache-2.0 |
| **`cexll/codex-mcp-server`** | Community MCP wrapper around `codex exec` with model/sandbox params, long timeouts | Community, maintained |
| **`claude-code-router` (musistudio)** | Proxy that reroutes Claude Code's Anthropic API calls to any provider (GLM/Gemini/DeepSeek), incl. per-subagent model override via `<CCR-SUBAGENT-MODEL>` tag | Very popular — **35.6k stars, latest release v3.0.7 (03 Jul 2026), MIT** |
| **`opencode-acp` + Codex/OpenCode ACP modes** | Agent Client Protocol adapters (editor↔agent), not directly orchestrator↔minion, but usable for headless drive | Early/experimental |

### Native multi-agent capability of each platform (this is what makes tier-3 possible)
- **Claude Code:** Subagents in `.claude/agents/*.md` with per-agent `model`; Task/Agent tool; **as of v2.1.172 a subagent CAN spawn nested subagents up to a fixed depth of 5** (not configurable). BUT: subagents have documented, inconsistent failures calling **MCP tools** (esp. project-scoped, plugin-defined, and background subagents) — they hallucinate results instead. Model selection per subagent is real but the Task tool's `model` enum is limited to `sonnet/opus/haiku` unless you patch it or route via `ANTHROPIC_DEFAULT_*_MODEL`/CCR.
- **Codex CLI:** Native subagents behind `[features] multi_agent = true`. `[agents]` config with `max_threads` (default 6) and `max_depth` (**default 1** — a child can spawn but no deeper recursion; raising it risks token/latency blowups). Custom agents are per-file TOML in `.codex/agents/*.toml` each with its own `model`, `model_reasoning_effort`, `sandbox_mode`, `developer_instructions`. Codex only spawns subagents when **explicitly asked**. Built-in agents: `default`, `worker`, `explorer`.
- **OpenCode:** `primary` vs `subagent` modes; subagents invoked via Task tool or `@mention`; each agent has its own `model` (`provider/model-id`), `temperature`, `tools`, `prompt`. Built-in subagents: General, Explore, Scout. **Known gap:** a primary agent invoking a subagent via the Task tool **cannot dynamically choose the subagent's model per-call** (open feature request #6651) — the model is fixed in config or inherited; the common workaround is duplicate agent definitions per model tier.

### Headless / structured-output primitives (the DIY backbone)
- **Codex:** `codex exec "<prompt>"` (non-interactive); `--json` emits JSONL event stream (`thread.started`, `turn.started/completed/failed`, `item.*`); `--output-schema schema.json` enforces structured output; `codex exec resume --last` / `resume <SESSION_ID>` for multi-turn. `--ephemeral` to skip session persistence; `--skip-git-repo-check`; `-m`/`--model`, `-c model_reasoning_effort=xhigh`, `--profile`. **Known bug:** `codex exec --json` does not print the session id, complicating programmatic resume (issue #3817); resume can hang after MCP init (#14470).
- **Claude Code:** `claude -p` (headless); `--output-format text|json|stream-json`; `--input-format stream-json` for bidirectional piping; `--json-schema` for structured output; `--resume <session_id>` / `--continue`; `--allowedTools`, `--permission-mode`, `--max-turns`, `--max-budget-usd`, `--bare` (skip context discovery, requires explicit API key). Programmatic use draws from subscription limits as of June 15 2026.
- **OpenCode:** `opencode serve` (headless HTTP + OpenAPI 3.1 at `/doc`, default `127.0.0.1:4096`); `opencode run "<msg>" -m provider/model --format json -c/--session <id> --agent <name> --attach <url>` (note: `--format json`, not `-f`; `-f`/`--file` attaches files; no `-q`); `@opencode-ai/sdk` (`createOpencodeClient({baseUrl})` → `session.create`, `session.prompt({path,body:{model:{providerID,modelID}, parts, agent}})`, `session.abort`, `event.subscribe`). HTTP: `POST /session`, `POST /session/{id}/message` (sync) or `/prompt_async` (204), `POST /session/{id}/abort`, `GET /event` + `GET /global/event` SSE.

### Real-time steering surface
- **Event streaming:** all three emit structured event streams you can tail (Codex JSONL, Claude stream-json NDJSON, OpenCode SSE). This gives progress monitoring and a basis for "cancel based on what you saw."
- **Interruption:** OpenCode `session.abort`/`POST /abort`; Codex `/agent` to steer/stop a running subagent thread interactively; killing the child process for `codex exec`/`claude -p`.
- **Redirection mid-task:** via session resume (`codex exec resume`, `claude --resume`, OpenCode `--session`/`--continue`) — stop, then re-issue with corrected prompt. This is "checkpoint-and-steer," not live interjection.
- **MCP elicitation/sampling:** Codex's MCP server propagates `on-request` approvals back to the client via MCP **elicitation** (`elicitation/create`); MCP **sampling** (`sampling/createMessage`) lets a server borrow the client's LLM. These are the spec-level bidirectional hooks, but client support is uneven and OpenCode's SSE stream has had reliability bugs (events dropped on reconnect #25657, SyncEvent publishes not delivered in 1.14.42+ #27966, connection leaks #17628).

## Details

### Recommended architecture

```
TIER 1 — ORCHESTRATOR
  Claude Code (main thread), Claude Fable 5 @ high reasoning
  Role: planning, task decomposition, dispatch, result synthesis
  Config: MCP servers for codex + opencode; custom skills for dispatch
        │
        │  (dispatch happens from the MAIN THREAD, not from a Claude subagent)
        ▼
TIER 2 — AGENT PLATFORMS (each an MCP server or spawned process)
  ├─ Codex CLI  via `codex mcp-server`  → GPT-5.5 @ xhigh
  ├─ OpenCode   via `opencode-mcp`/`opencode serve` → GLM-5.2 xhigh / Gemini 3.1 Pro
  └─ Claude Code (2nd instance) via `claude -p` process → Opus 4.8 xhigh
        │
        │  (each tier-2 platform uses its OWN native subagent feature)
        ▼
TIER 3 — MINIONS (cheaper/faster models)
  ├─ Codex subagents ([agents] max_depth≥1): gpt-5.5 high, gpt-5.4-mini
  ├─ OpenCode subagents (Task tool): glm-5.2 high, gemini-3.1-pro, sonnet-5 high
  └─ Claude subagents (.claude/agents, depth≤5): sonnet-5 high, haiku
```

**Why this shape:**
1. **Dispatch from the main thread.** Because Claude Code subagents can't reliably use MCP tools, the orchestrator's *main* conversation holds the Codex/OpenCode MCP tools and calls them directly. Task decomposition still happens in Claude; the "delegate to GPT/GLM" call is a main-thread MCP tool call (or a `Bash` shell-out). If you want Claude subagents to fan work out to other providers, have those subagents shell out via `Bash` to `codex exec`/`opencode run` rather than relying on MCP.
2. **Tier-3 lives inside each tier-2 platform.** Codex spawns Codex subagents natively; OpenCode spawns OpenCode subagents natively; a second Claude Code instance spawns Claude subagents natively. Each platform manages its own minion pool, model routing, and context isolation. This keeps nesting shallow at any single layer and respects each tool's depth limits.

### Concrete setup

**1. Register Codex as an MCP server in Claude Code** (`.mcp.json` or `claude mcp add`):
```json
{
  "mcpServers": {
    "codex": { "command": "codex", "args": ["mcp-server"] }
  }
}
```
The `codex` tool accepts a Codex `Config`-shaped param set: `prompt`, `model`, `sandbox` (`read-only|workspace-write|danger-full-access`), `cwd`, `base-instructions`, `approval-policy`. `codex-reply` continues by `threadId` (from `structuredContent.threadId`). Set `MCP_TOOL_TIMEOUT` high for long tasks; use `approval-policy=never` when the client can't handle elicitation.

**2. Codex model + reasoning per invocation.** Use profile files (`~/.codex/<name>.config.toml`, since v0.134 profiles are separate files, not `[profiles.x]` tables):
```toml
# ~/.codex/deep.config.toml
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
approval_policy = "on-request"
```
Invoke: `codex --profile deep` / `codex exec --profile deep "..."`, or one-off `codex -c model_reasoning_effort="xhigh" -m gpt-5.5 "..."`. **Reserve xhigh** — it can cost 3–5x medium.

**3. Codex tier-3 minions** — enable multi-agent + define custom agents:
```toml
# ~/.codex/config.toml
[features]
multi_agent = true
[agents]
max_threads = 6
max_depth = 1          # keep at 1 unless you truly need recursion
```
```toml
# .codex/agents/refactor-worker.toml
name = "refactor-worker"
description = "Executes a single-file refactor task"
model = "gpt-5.4-mini"
model_reasoning_effort = "low"
sandbox_mode = "workspace-write"
```
Then prompt explicitly: *"Spawn one refactor-worker per file, wait for all, summarize."* Codex does not auto-spawn.

**4. Register OpenCode as an MCP server** — simplest path is the `opencode-mcp` npm package:
```json
{
  "mcpServers": {
    "opencode": { "command": "npx", "args": ["-y", "opencode-mcp"] }
  }
}
```
Per its README, *"Zero setup — the server auto-starts `opencode serve` if it's not already running,"* and it exposes workflow tools such as `opencode_fire({ prompt: "…" }) → returns sessionId immediately` (create session + prompt in one call). Alternatively, DIY: run `opencode serve --port 4096` and shell out from a thin stdio MCP wrapper, or just call `opencode run` via `Bash`.

**5. OpenCode model/provider + agents.** Configure providers in `~/.config/opencode/opencode.json`; GLM via Z.AI:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-opus-4-5",
  "agent": {
    "glm-worker": {
      "mode": "subagent",
      "model": "zai-coding-plan/glm-5.2",
      "reasoning_effort": "high",
      "tools": { "write": true, "edit": true, "bash": true }
    },
    "gemini-explorer": {
      "mode": "subagent",
      "model": "google/gemini-3.1-pro"
    }
  }
}
```
For Z.AI GLM, authenticate with `opencode auth login` (Z.AI provider) using the Coding Plan endpoint (`https://api.z.ai/api/coding/paas/v4` or the BigModel equivalent `https://open.bigmodel.cn/api/coding/paas/v4`) — do **not** use the general endpoint. Reasoning effort is passed through as provider-specific model options (e.g. `reasoning_effort`, or `variant` in some agent frameworks). Per-message model over HTTP: `POST /session/{id}/message` with body `{ "model": {"providerID":"zai-coding-plan","modelID":"glm-5.2"}, "agent":"glm-worker", "parts":[{"type":"text","text":"..."}] }`.

**6. OpenCode tier-3 minions.** Because OpenCode can't pick a subagent's model per Task call, pre-declare one subagent per (role × model tier) — e.g. `glm-worker-high`, `glm-worker-fast`, `gemini-explorer` — and let the primary agent pick by name. Restrict tools per role (readers get `write:false`).

**7. Second Claude Code instance as a tier-2 minion platform.** Spawn headlessly:
```bash
claude -p "Implement plan section 3" \
  --model opus-4.8 \
  --output-format stream-json --verbose \
  --allowedTools "Bash,Read,Edit,Agent" \
  --permission-mode acceptEdits --max-turns 40
```
Capture `session_id` from the JSON envelope for later `--resume`. This instance can then spawn its own `.claude/agents` subagents (depth ≤5). If you need it to route those subagents to non-Claude models, launch it through `claude-code-router` (`ccr code`) and use `<CCR-SUBAGENT-MODEL>provider,model</CCR-SUBAGENT-MODEL>` in subagent prompts.

**8. Cross-provider routing for the whole fleet (optional).** `claude-code-router` gives Claude Code an Anthropic-compatible proxy that routes `background`, `think`, `longContext`, and per-subagent traffic to cheaper providers (GLM via Z.AI, Gemini, DeepSeek). This is the lowest-effort way to cut token cost without changing your Claude Code workflow, and complements (rather than replaces) the MCP-based delegation to Codex/OpenCode.

### Real-time steering for critical tasks
For a high-priority task where you want to watch and redirect:
- Drive the minion in **streaming mode** and tee the stream: `codex exec --json ... | tee run.jsonl`, `claude -p --output-format stream-json`, or subscribe to OpenCode `client.event.subscribe()` / `GET /event`.
- Build a small monitor (a Claude Code hook, an OpenCode plugin `event` handler, or an external script) that parses events and decides to continue or abort.
- To redirect: **abort** (`session.abort` / kill child / Codex `/agent` stop) then **resume with a corrected prompt** (`codex exec resume`, `claude --resume`, `opencode run --session`). This is checkpoint-steering; there is no fully-supported "inject a message into a mid-flight turn" across all three (Claude's `--input-format stream-json` is the closest but is under-documented).
- MCP **elicitation** gives you human-in-the-loop approval gates when Codex runs `approval-policy=on-request` under an elicitation-capable client.

### Token/cost & concurrency considerations
- Each tier multiplies token spend: an orchestrator turn that fans out to N tier-2 platforms, each fanning to M minions, is O(N×M) sessions, each with its own context + reasoning tokens. Codex explicitly warns subagents "consume more tokens than comparable single-agent runs."
- **Effort tiering is the main lever:** orchestrator at high/xhigh, minions at low/minimal. Model tiering matters too (a mixed Opus-orchestrator + Sonnet/Haiku-worker team is markedly cheaper than all-Opus).
- **Concurrency caps:** Codex `max_threads` default 6; Claude Code ~3–5 concurrent subagents is the practical sweet spot (up to 10 technically), with Dynamic Workflows pushing higher for clean fan-out; OpenCode has no hard cap but providers rate-limit (GLM/Gemini free tiers especially).
- **Review is the real bottleneck.** More parallel minions means more output to verify; plan for it.

## Recommendations

**Stage 1 — Prove the two-tier path (1–2 hrs).** Add the `codex` MCP server and the `opencode-mcp` server to Claude Code. From the Claude *main thread*, delegate a self-contained task to each ("use codex with model gpt-5.5 xhigh to…", "use opencode with glm-worker to…"). Confirm you get structured results back. Benchmark: does a delegated task complete without you having to babysit approvals? If elicitation stalls, set `approval-policy=never` + a tight sandbox.

**Stage 2 — Add tier-3 within each platform (half day).** Enable Codex `multi_agent` + one custom `[agents]` worker; declare 2–3 OpenCode subagents per model tier; stand up the second Claude Code instance via `claude -p`. Test each platform's own fan-out in isolation before nesting.

**Stage 3 — Wire the hierarchy + cost controls (1 day).** Write a Claude Code **skill** (you already build these) that encodes the dispatch policy: which task classes go to Codex vs OpenCode vs Claude-minion, with model+effort per class. Add `--max-budget-usd`/`max_threads` ceilings and log `total_cost_usd` per run. Put `claude-code-router` in front if you want cheap background/subagent routing globally.

**Stage 4 — Add steering only for critical tasks.** For the subset of high-stakes jobs, add a stream monitor + abort/resume loop. Don't build this for everything — it's the highest-effort, lowest-maturity piece.

**Thresholds that change the plan:**
- If Claude Code ships reliable **MCP-in-subagents**, collapse Stage 1's "main-thread dispatch" rule and let subagents delegate directly (simpler fan-out).
- If OpenCode ships **per-Task model selection** (#6651), drop the duplicate-agent-per-tier workaround.
- If token spend from fan-out exceeds the value of parallelism on a given workflow, **downgrade to sequential single-agent** for that workflow — subagents only pay off when they remove context noise or genuinely parallelize.
- If your minions run untrusted code, never raise Codex `max_depth` above 1 or grant `danger-full-access`.

## Caveats
- **Model/version naming (Fable 5, GPT-5.5, GLM-5.2, Opus 4.8, Gemini 3.1) reflects the mid-2026 landscape in the sources; treat exact model IDs as fast-moving** and verify against each provider's current catalog before wiring configs. Notably, sources indicate Claude Fable 5 was subject to a June 2026 US export-control restriction — confirm its availability for your account.
- **Claude Code subagent limitations are the biggest architectural risk.** Multiple open GitHub issues (#13898, #13605, #13254, #34935, #30280) document subagents (project-scoped, plugin-defined, and background) silently failing to call MCP tools and hallucinating results. Design around this: dispatch from the main thread or via process spawns.
- **Codex `--json` session-id omission** (#3817) and resume hangs (#14470) mean programmatic multi-turn Codex needs a fallback (read `~/.codex/sessions/`), which is racy under concurrency. Prefer `codex-reply` via the MCP server (which returns `threadId`) over `codex exec --json … resume`.
- **OpenCode SSE reliability:** several 2026 issues report the `/event` stream dropping events on reconnect (#25657), not delivering certain event types after v1.14.42 (#27966), and server hangs/leaks under abrupt client disconnects (#15149, #17628). If you depend on live event monitoring, pin/verify your OpenCode version and add reconnect + snapshot-reconciliation.
- **Nested MCP depth:** MCP does not "nest" cleanly — a Claude subagent calling an MCP server that itself is Codex, which spawns Codex subagents, is several fragile layers. The recommended design deliberately keeps MCP at one hop (orchestrator→platform) and uses each platform's *native* subagents below that.
- **Auth & rate limits:** each platform needs its own credentials (Codex OAuth/`OPENAI_API_KEY`, OpenCode `~/.local/share/opencode/auth.json`, Z.AI/BigModel keys, Gemini keys). Programmatic Claude Code usage draws from subscription limits (as of June 15 2026), and free GLM/Gemini tiers rate-limit aggressively under fan-out.
- The maturity assessments for community projects (`opencode-mcp` v1.10.0; PAL/Zen at 11.2k stars; `claude-code-router` at 35.6k stars, v3.0.7 dated 03 Jul 2026) are snapshots as of early July 2026; verify current status before depending on them.