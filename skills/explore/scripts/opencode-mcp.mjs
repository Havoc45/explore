#!/usr/bin/env node
/**
 * opencode-mcp.mjs — minimal stdio MCP server wrapping `opencode serve`.
 *
 * Exposes opencode as a minion platform (dispatch / steer / abort) with six
 * lean tools instead of a broad API surface, so the orchestrator's context
 * stays small. Zero dependencies; Node 18+ (global fetch).
 *
 * Register (Claude Code):
 *   claude mcp add --scope user opencode -- node /path/to/opencode-mcp.mjs
 *
 * Env:
 *   OPENCODE_PORT      port for `opencode serve` (default 4096)
 *   OPENCODE_HOST      hostname (default 127.0.0.1)
 *   OPENCODE_RUN_TIMEOUT_MS  cap on blocking runs (default 1200000 = 20 min)
 *
 * The wrapper auto-starts `opencode serve` if nothing answers on the port,
 * and leaves it running (an idle server is cheap; kill it manually if
 * unwanted). Sessions are rooted per `directory` via the query param, so one
 * server drives many projects/worktrees.
 */

import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const PORT = Number(process.env.OPENCODE_PORT || 4096);
const HOST = process.env.OPENCODE_HOST || "127.0.0.1";
const BASE = `http://${HOST}:${PORT}`;
const RUN_TIMEOUT_MS = Number(process.env.OPENCODE_RUN_TIMEOUT_MS || 1_200_000);

const log = (...a) => console.error("[opencode-mcp]", ...a);

// ---------- opencode server management ----------

async function serverHealth(timeoutMs = 500) {
  try {
    const res = await fetch(`${BASE}/session/status`, {
      signal: AbortSignal.timeout(timeoutMs),
    });
    return res.ok ? "healthy" : "unhealthy";
  } catch {
    return "down";
  }
}

let serverStarting = null; // memoized so concurrent first calls spawn one server

async function ensureServer() {
  if ((await serverHealth()) === "healthy") return;
  serverStarting ??= (async () => {
    log(`starting opencode serve on ${BASE}`);
    const child = spawn(
      "opencode",
      ["serve", "--port", String(PORT), "--hostname", HOST],
      { detached: true, stdio: "ignore" },
    );
    child.unref();
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 500));
      if ((await serverHealth()) === "healthy") return;
    }
    throw new Error(`opencode serve did not come up on ${BASE} within 15s`);
  })();
  try {
    await serverStarting;
  } catch (err) {
    serverStarting = null; // allow a retry after a failed start
    throw err;
  }
}

async function api(method, path, { directory, body, timeoutMs } = {}) {
  const url = new URL(BASE + path);
  if (directory) url.searchParams.set("directory", directory);
  const res = await fetch(url, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal: timeoutMs ? AbortSignal.timeout(timeoutMs) : undefined,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${method} ${path} -> HTTP ${res.status} ${text.slice(0, 300)}`);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.text();
}

// ---------- session helpers ----------

function modelBody(model) {
  // "openrouter/z-ai/glm-5.2" -> { providerID: "openrouter", modelID: "z-ai/glm-5.2" }
  if (!model) return undefined;
  const [providerID, ...rest] = model.split("/");
  return { providerID, modelID: rest.join("/") };
}

function parts(text) {
  return [{ type: "text", text }];
}

async function createSession({ directory, title, parent_session_id }) {
  const body = {};
  if (title) body.title = title;
  if (parent_session_id) body.parentID = parent_session_id;
  const s = await api("POST", "/session", { directory, body });
  return s.id;
}

async function readMessages(sessionID, directory) {
  const msgs = await api("GET", `/session/${sessionID}/message`, { directory });
  let last = null;
  for (let i = msgs.length - 1; i >= 0; i--) {
    const m = msgs[i];
    if (m.info?.role !== "assistant") continue;
    const text = (m.parts || [])
      .filter((p) => p.type === "text")
      .map((p) => p.text)
      .join("\n");
    const error = m.info?.error?.name;
    const tools = (m.parts || [])
      .filter((p) => p.type === "tool")
      .map((p) => `${p.tool}:${p.state?.status}`);
    last = { text, error, tools, cost: m.info?.cost };
    break;
  }
  // replied: the newest message is an assistant reply — i.e. the last prompt has
  // been answered. Right after prompt_async the newest message is the user
  // prompt (or status hasn't flipped to busy yet), so `!running` alone is a
  // false idle; terminal state is !running && replied.
  const newest = msgs[msgs.length - 1];
  const replied = newest?.info?.role === "assistant";
  return { last, replied };
}

async function promptSync(sessionID, { directory, prompt, model, agent, variant }) {
  const body = { parts: parts(prompt) };
  const m = modelBody(model);
  if (m) body.model = m;
  if (agent) body.agent = agent;
  if (variant) body.variant = variant;
  const r = await api("POST", `/session/${sessionID}/message`, {
    directory,
    body,
    timeoutMs: RUN_TIMEOUT_MS,
  });
  const text = (r.parts || [])
    .filter((p) => p.type === "text")
    .map((p) => p.text)
    .join("\n");
  return { text, error: r.info?.error?.name, cost: r.info?.cost };
}

async function promptAsync(sessionID, { directory, prompt, model, agent, variant }) {
  const body = { parts: parts(prompt) };
  const m = modelBody(model);
  if (m) body.model = m;
  if (agent) body.agent = agent;
  if (variant) body.variant = variant;
  await api("POST", `/session/${sessionID}/prompt_async`, { directory, body });
}

// ---------- tools ----------

const COMMON_PROPS = {
  directory: {
    type: "string",
    description:
      "Absolute path the session is rooted at (repo root or worktree). Defaults to the server process cwd — always pass it explicitly for dispatch.",
  },
};

const TOOLS = [
  {
    name: "opencode_run",
    description:
      "Run an opencode minion and block until it finishes; returns the final text and session_id. Pass session_id to continue an existing session (REVISE/steer rounds).",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string", description: "The self-contained brief." },
        model: {
          type: "string",
          description: "provider/model, e.g. openrouter/z-ai/glm-5.2. Omit for the server default.",
        },
        agent: { type: "string", description: "Named opencode agent to run as (optional)." },
        variant: { type: "string", description: "Reasoning-effort variant, e.g. high | xhigh (model-specific)." },
        session_id: { type: "string", description: "Existing session to continue instead of creating one." },
        title: { type: "string", description: "Session title (new sessions only)." },
        ...COMMON_PROPS,
      },
      required: ["prompt"],
    },
  },
  {
    name: "opencode_fire",
    description:
      "Dispatch an opencode minion asynchronously; returns session_id immediately. Poll with opencode_status, redirect with opencode_steer, stop with opencode_abort.",
    inputSchema: {
      type: "object",
      properties: {
        prompt: { type: "string", description: "The self-contained brief." },
        model: { type: "string", description: "provider/model. Omit for the server default." },
        agent: { type: "string" },
        variant: { type: "string" },
        session_id: { type: "string", description: "Existing session to continue instead of creating one." },
        title: { type: "string" },
        ...COMMON_PROPS,
      },
      required: ["prompt"],
    },
  },
  {
    name: "opencode_status",
    description:
      "Heartbeat for a fired session: whether it is still running, the last assistant text so far, tool calls, and any error.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string" },
        ...COMMON_PROPS,
      },
      required: ["session_id"],
    },
  },
  {
    name: "opencode_wait",
    description:
      "Block until a fired session has answered its last prompt (idle + replied), then return the final assistant text. timeout_s caps the wait (default 600); on timeout it reports the live state instead of failing.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string" },
        timeout_s: { type: "number", description: "Max seconds to wait (default 600)." },
        ...COMMON_PROPS,
      },
      required: ["session_id"],
    },
  },
  {
    name: "opencode_steer",
    description:
      "Mid-run redirect: abort the session's in-flight turn, then send a corrective prompt on the same session (async). Follow with opencode_status / opencode_wait.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string" },
        prompt: { type: "string", description: "The corrective instruction." },
        model: { type: "string" },
        agent: { type: "string" },
        variant: { type: "string" },
        ...COMMON_PROPS,
      },
      required: ["session_id", "prompt"],
    },
  },
  {
    name: "opencode_abort",
    description: "Stop a session's in-flight turn. The session remains resumable via opencode_run/opencode_fire with session_id.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string" },
        ...COMMON_PROPS,
      },
      required: ["session_id"],
    },
  },
];

async function isRunning(sessionID, directory) {
  const statuses = await api("GET", "/session/status", { directory });
  const s = statuses?.[sessionID];
  if (s?.type) return s.type !== "idle";
  return false;
}

async function callTool(name, args) {
  await ensureServer();
  const directory = args.directory || process.cwd();
  const common = { directory };

  switch (name) {
    case "opencode_run": {
      const session_id =
        args.session_id || (await createSession({ directory, title: args.title }));
      const r = await promptSync(session_id, { ...args, directory });
      return { session_id, directory, ...r };
    }
    case "opencode_fire": {
      const session_id =
        args.session_id || (await createSession({ directory, title: args.title }));
      await promptAsync(session_id, { ...args, directory });
      return { session_id, directory, dispatched: true };
    }
    case "opencode_status": {
      const running = await isRunning(args.session_id, directory);
      const { last, replied } = await readMessages(args.session_id, directory);
      return { session_id: args.session_id, running, replied, last, ...common };
    }
    case "opencode_wait": {
      const cap = (args.timeout_s ?? 600) * 1000;
      const deadline = Date.now() + cap;
      // done = idle AND the last prompt answered; `!running` alone races the
      // async fork (still-starting sessions read as idle).
      for (;;) {
        const running = await isRunning(args.session_id, directory);
        const { last, replied } = await readMessages(args.session_id, directory);
        if (!running && replied) {
          return { session_id: args.session_id, running: false, replied, last, ...common };
        }
        if (Date.now() >= deadline) {
          return {
            session_id: args.session_id,
            running,
            replied,
            timed_out: true,
            last,
            ...common,
          };
        }
        await new Promise((r) => setTimeout(r, 2000));
      }
    }
    case "opencode_steer": {
      await api("POST", `/session/${args.session_id}/abort`, { directory });
      await promptAsync(args.session_id, { ...args, directory });
      return { session_id: args.session_id, steered: true, ...common };
    }
    case "opencode_abort": {
      await api("POST", `/session/${args.session_id}/abort`, { directory });
      return { session_id: args.session_id, aborted: true, ...common };
    }
    default:
      throw new Error(`unknown tool: ${name}`);
  }
}

// ---------- stdio MCP plumbing (NDJSON JSON-RPC) ----------

const out = (obj) => process.stdout.write(JSON.stringify(obj) + "\n");

const rl = createInterface({ input: process.stdin });
rl.on("line", async (line) => {
  line = line.trim();
  if (!line) return;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    log("unparseable line:", line.slice(0, 120));
    return out({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } });
  }
  const { id, method, params } = msg;
  if (id === undefined) return; // notification — nothing to answer

  try {
    if (method === "initialize") {
      const SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"];
      out({
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: SUPPORTED.includes(params?.protocolVersion)
            ? params.protocolVersion
            : "2025-03-26",
          capabilities: { tools: {} },
          serverInfo: { name: "opencode-mcp", version: "1.0.0" },
        },
      });
    } else if (method === "ping") {
      out({ jsonrpc: "2.0", id, result: {} });
    } else if (method === "tools/list") {
      out({ jsonrpc: "2.0", id, result: { tools: TOOLS } });
    } else if (method === "tools/call") {
      const known = TOOLS.some((t) => t.name === params?.name);
      if (!known) {
        return out({
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: `Unknown tool: ${params?.name}` },
        });
      }
      const result = await callTool(params.name, params.arguments || {});
      out({
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result) }],
          structuredContent: result,
        },
      });
    } else {
      out({ jsonrpc: "2.0", id, error: { code: -32601, message: `unknown method: ${method}` } });
    }
  } catch (err) {
    out({
      jsonrpc: "2.0",
      id,
      result: {
        content: [{ type: "text", text: String(err?.message || err) }],
        isError: true,
      },
    });
  }
});

rl.on("close", () => process.exit(0));
log(`ready — opencode target ${BASE}`);
