#!/usr/bin/env node
/**
 * opencode-mcp.mjs — minimal stdio MCP server wrapping `opencode serve`.
 *
 * Exposes opencode as a minion platform (dispatch / steer / abort / health)
 * with seven lean tools instead of a broad API surface, so the orchestrator's
 * context stays small. Zero dependencies; Node 18+ (global fetch).
 *
 * Register (Claude Code):
 *   claude mcp add --scope user opencode -- node /path/to/opencode-mcp.mjs
 *
 * Env:
 *   OPENCODE_PORT      port for `opencode serve` (default 4096)
 *   OPENCODE_HOST      hostname (default 127.0.0.1)
 *   OPENCODE_API_TIMEOUT_MS  cap on API calls (default 30000 = 30s)
 *   OPENCODE_RUN_TIMEOUT_MS  cap on blocking runs (default 1200000 = 20 min)
 *
 * The wrapper auto-starts `opencode serve` if nothing answers on the port,
 * and leaves it running (an idle server is cheap; kill it manually if
 * unwanted). Sessions are rooted per `directory` via the query param, so one
 * server drives many projects/worktrees.
 */

import { spawn } from "node:child_process";
import {
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { createInterface } from "node:readline";

const VERSION = "1.4.1";
const PORT = Number(process.env.OPENCODE_PORT || 4096);
const DEFAULT_HOST = "127.0.0.1";
const HOST = process.env.OPENCODE_HOST || DEFAULT_HOST;
const BASE = `http://${HOST}:${PORT}`;
const RUN_TIMEOUT_MS = Number(process.env.OPENCODE_RUN_TIMEOUT_MS || 1_200_000);
const DEFAULT_API_TIMEOUT_MS = Number(process.env.OPENCODE_API_TIMEOUT_MS || 30_000);
const HEAL_LOCK_DIR = `${tmpdir()}/opencode-mcp-heal-${PORT}.lock`;
const HEAL_LOCK_OWNER = `${HEAL_LOCK_DIR}/owner.pid`;

const log = (...a) => console.error("[opencode-mcp]", ...a);

// ---------- opencode server management ----------

async function serverHealth(timeoutMs = 500) {
  let res;
  try {
    res = await fetch(`${BASE}/session/status`, {
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    if (err?.name === "TimeoutError" || err?.name === "AbortError") return "busy";
    // Any connection-level failure means nothing usable is answering, whether
    // the port is empty or a crashed serve is still holding the socket open.
    // Calling the latter "busy" made it unhealable: ensureServer returns early
    // on busy, so dispatches failed `fetch failed` forever while health said
    // OK. probeHealth still demands three agreeing probes before acting.
    if (isConnectionDead(err)) return "down";
    return "busy";
  }
  if (!res.ok) return "unhealthy";
  try {
    await res.json();
    return "healthy";
  } catch {
    return "unhealthy";
  }
}

async function globalHealth(timeoutMs = 1500) {
  // GET /global/health -> { healthy, version } (absent on very old serves).
  try {
    const res = await fetch(`${BASE}/global/health`, {
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function probeHealth() {
  const states = [];
  for (const timeoutMs of [500, 1500, 3000]) {
    const health = await serverHealth(timeoutMs);
    if (health === "healthy" || health === "busy") return health;
    states.push(health);
  }
  return states.every((health) => health === states[0]) ? states[0] : "busy";
}

function commandOutput(command, args, timeoutMs = 10_000) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
      const err = new Error(`${command} timed out after ${timeoutMs}ms`);
      err.name = "CommandTimeoutError";
      reject(err);
    }, timeoutMs);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code, signal) => {
      clearTimeout(timer);
      if (!timedOut) resolve({ code, signal, stdout, stderr });
    });
  });
}

async function listenerCommand() {
  const found = await commandOutput("lsof", ["-ti", ":" + PORT]);
  if (found.code === 1 && found.stderr.trim()) {
    throw new Error(`lsof failed while checking port ${PORT}: ${found.stderr.trim()}`);
  }
  if (found.code !== 0 && found.code !== 1) {
    throw new Error(`lsof failed while checking port ${PORT}: ${found.stderr.trim()}`);
  }
  const candidatePids = [...new Set(found.stdout.split(/\s+/).filter(Boolean).map(Number))]
    .filter((pid) => Number.isInteger(pid) && pid > 0 && pid !== process.pid);
  const pids = [];
  for (const pid of candidatePids) {
    const listening = await commandOutput("lsof", [
      "-nP",
      "-a",
      "-p",
      String(pid),
      `-iTCP:${PORT}`,
      "-sTCP:LISTEN",
      "-t",
    ]);
    if (listening.code === 0) pids.push(pid);
    else if (listening.code === 1 && listening.stderr.trim()) {
      throw new Error(`lsof failed while checking listener pid ${pid}: ${listening.stderr.trim()}`);
    }
    else if (listening.code !== 1) {
      throw new Error(`lsof failed while checking listener pid ${pid}: ${listening.stderr.trim()}`);
    }
  }
  if (pids.length === 0) {
    if ((await serverHealth()) === "down") return null;
    throw new Error(`could not identify the process listening on port ${PORT}`);
  }

  const processes = [];
  for (const pid of pids) {
    const inspected = await commandOutput("ps", ["-o", "command=", "-p", String(pid)]);
    processes.push({ pid, command: inspected.stdout.trim() || "<unknown>" });
  }
  if (processes.length !== 1) {
    const details = processes.map(({ pid, command }) => `${pid} (${command})`).join(", ");
    throw new Error(`could not safely identify one listener on port ${PORT}: ${details}`);
  }
  return processes[0];
}

function isExpectedServeCommand(command) {
  const servePattern = /(?:^|[\/\s])opencode\s+serve(?:\s|$)/;
  const portPattern = new RegExp(`(?:^|\\s)--port(?:\\s+|=)${PORT}(?:\\s|$)`);
  const escapedHost = HOST.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const hostPattern = new RegExp(`(?:^|\\s)--hostname(?:\\s+|=)${escapedHost}(?:\\s|$)`);
  return servePattern.test(command)
    && portPattern.test(command)
    && (HOST === DEFAULT_HOST || hostPattern.test(command));
}

function processExists(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (err) {
    if (err?.code === "ESRCH") return false;
    if (err?.code === "EPERM") return true;
    throw err;
  }
}

async function waitForProcessExit(pid, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (!processExists(pid)) return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return !processExists(pid);
}

async function waitForPortFree(timeoutMs = 2000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const found = await commandOutput("lsof", [
      "-nP",
      `-iTCP:${PORT}`,
      "-sTCP:LISTEN",
      "-t",
    ]);
    if (found.code === 1 && !found.stdout.trim()) return;
    if (found.code !== 0 && found.code !== 1) {
      throw new Error(`lsof failed while waiting for port ${PORT}: ${found.stderr.trim()}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`port ${PORT} did not become free within ${timeoutMs}ms`);
}

async function acquireHealLock(timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    try {
      mkdirSync(HEAL_LOCK_DIR, { recursive: false });
      try {
        writeFileSync(HEAL_LOCK_OWNER, String(process.pid));
      } catch (err) {
        rmSync(HEAL_LOCK_DIR, { recursive: true, force: true });
        throw err;
      }
      return;
    } catch (err) {
      if (err?.code !== "EEXIST") throw err;
    }

    try {
      const ageMs = Date.now() - statSync(HEAL_LOCK_DIR).mtimeMs;
      if (ageMs > 60_000) {
        const staleDir = `${HEAL_LOCK_DIR}.stale-${process.pid}-${Date.now()}`;
        try {
          renameSync(HEAL_LOCK_DIR, staleDir);
          log(`taking over stale heal lock for port ${PORT} (${Math.round(ageMs)}ms old)`);
          rmSync(staleDir, { recursive: true, force: true });
        } catch (err) {
          if (err?.code !== "ENOENT") throw err;
        }
        continue;
      }
    } catch (err) {
      if (err?.code === "ENOENT") continue;
      throw err;
    }

    if (Date.now() >= deadline) {
      throw new Error(`timed out waiting ${timeoutMs}ms for heal lock ${HEAL_LOCK_DIR}`);
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
}

function releaseHealLock() {
  let ownerPid;
  try {
    ownerPid = readFileSync(HEAL_LOCK_OWNER, "utf8").trim();
  } catch {
    return;
  }
  if (ownerPid !== String(process.pid)) return;
  rmSync(HEAL_LOCK_DIR, { recursive: true, force: true });
}

function signalProcess(pid, signal) {
  try {
    process.kill(pid, signal);
    return true;
  } catch (err) {
    if (err?.code === "ESRCH") return false;
    throw err;
  }
}

// Frees the port so a fresh serve can bind: refuses outright if a foreign
// process holds it, otherwise stops the stale serve and waits for the socket
// to clear. `reason` only shapes the log line.
async function clearPortListener(reason) {
  const listener = await listenerCommand();
  if (!listener) return;
  const { pid, command } = listener;
  if (!isExpectedServeCommand(command)) {
    throw new Error(
      `port ${PORT} listener pid ${pid} is not opencode serve --port ${PORT}: ${command}`,
    );
  }

  const inspectedBeforeTerm = await commandOutput("ps", ["-o", "command=", "-p", String(pid)]);
  const currentCommand = inspectedBeforeTerm.stdout.trim();
  if (!isExpectedServeCommand(currentCommand)) {
    throw new Error(`refusing to SIGTERM pid ${pid}; command changed to: ${currentCommand}`);
  }
  log(`stale opencode serve pid ${pid} (${reason}) — replacing`);
  signalProcess(pid, "SIGTERM");
  if (!(await waitForProcessExit(pid, 2000))) {
    const inspected = await commandOutput("ps", ["-o", "command=", "-p", String(pid)]);
    const commandBeforeKill = inspected.stdout.trim();
    if (!isExpectedServeCommand(commandBeforeKill)) {
      throw new Error(`refusing to SIGKILL pid ${pid}; command changed to: ${commandBeforeKill}`);
    }
    log(`stale opencode serve pid ${pid} ignored SIGTERM — sending SIGKILL`);
    signalProcess(pid, "SIGKILL");
  }
  await waitForPortFree();
}

async function replaceUnhealthyServer() {
  if ((await probeHealth()) !== "unhealthy") return false;
  await clearPortListener("unhealthy /session/status");
  return true;
}

let serverStarting = null; // memoized so concurrent first calls spawn one server

async function ensureServer() {
  const initialHealth = await probeHealth();
  if (initialHealth === "healthy" || initialHealth === "busy") return;
  const starting = (serverStarting ??= (async () => {
    await acquireHealLock();
    try {
      const health = await probeHealth();
      if (health === "healthy" || health === "busy") return;
      if (health === "unhealthy") {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        if ((await probeHealth()) !== "unhealthy") return;
        if (!(await replaceUnhealthyServer())) return;
      } else {
        // "down" is usually an empty port, but it also covers a serve that
        // crashed while keeping its socket bound. Check for a listener before
        // spawning: a foreign one gets the clear collision error instead of a
        // mystery 15s bind timeout, and a dead serve gets replaced.
        await clearPortListener("connection-level failure with the port still bound");
      }
      log(`starting opencode serve on ${BASE}`);
      const child = spawn(
        "opencode",
        ["serve", "--port", String(PORT), "--hostname", HOST],
        { detached: true, stdio: ["ignore", "ignore", "pipe"] },
      );
      let childError = null;
      let childExit = null;
      let stderrTail = "";
      child.stderr.setEncoding("utf8");
      child.stderr.on("data", (chunk) => {
        stderrTail = (stderrTail + chunk).slice(-2048);
      });
      child.on("error", (err) => {
        childError = err;
      });
      child.on("exit", (code, signal) => {
        childExit = { code, signal };
      });
      child.unref();
      try {
        for (let i = 0; i < 30; i++) {
          await new Promise((r) => setTimeout(r, 500));
          if ((await serverHealth()) === "healthy") return;
          if (childError || childExit) break;
        }
        const details = [];
        if (childError) details.push(`spawn error: ${childError.message}`);
        if (childExit) {
          details.push(`exit: ${childExit.signal ? `signal ${childExit.signal}` : `code ${childExit.code}`}`);
        }
        if (stderrTail.trim()) details.push(`stderr: ${stderrTail.trim()}`);
        const suffix = details.length ? ` (${details.join("; ")})` : "";
        throw new Error(`opencode serve did not come up on ${BASE} within 15s${suffix}`);
      } finally {
        child.stderr.destroy();
      }
    } finally {
      releaseHealLock();
    }
  })());
  try {
    await starting;
  } finally {
    if (serverStarting === starting) serverStarting = null;
  }
}

// Node 24 + undici known issue (observed once, 2026-07-27; not reproducible on
// demand): a TCP RST during connection establishment surfaced as an uncatchable
// `setTypeOfService EINVAL` process crash. No in-process handler can trap it;
// recovery is a wrapper respawn — the MCP client's auto-restart where the
// harness does that, otherwise a manual reconnect (e.g. /mcp). Persisted
// sessions remain on disk. Upstream issue candidate.
async function api(method, path, { directory, body, timeoutMs } = {}) {
  const url = new URL(BASE + path);
  if (directory) url.searchParams.set("directory", directory);
  const requestTimeoutMs = timeoutMs ?? DEFAULT_API_TIMEOUT_MS;
  try {
    const res = await fetch(url, {
      method,
      headers: body ? { "content-type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: AbortSignal.timeout(requestTimeoutMs),
    });
    if (!res.ok) {
      let text = "";
      try {
        text = await res.text();
      } catch (err) {
        if (err?.name === "TimeoutError" || err?.name === "AbortError") throw err;
      }
      const httpErr = new Error(`${method} ${path} -> HTTP ${res.status} ${text.slice(0, 300)}`);
      httpErr.endpointLabelled = true; // already carries the endpoint; do not wrap twice
      throw httpErr;
    }
    if (res.status === 204) return null;
    const ct = res.headers.get("content-type") || "";
    return ct.includes("json") ? await res.json() : await res.text();
  } catch (err) {
    if (err?.name === "TimeoutError" || err?.name === "AbortError") {
      throw new Error(`${method} ${path} timed out after ${requestTimeoutMs}ms`, { cause: err });
    }
    if (err?.endpointLabelled) throw err;
    // Everything else used to re-throw raw, so a "fetch failed" or a JSON
    // SyntaxError on a truncated body reached the operator with no clue which
    // endpoint produced it. Keep `cause` set: isConnectionFailure() and
    // isConnectionRefused() walk the chain to decide whether to retry.
    throw new Error(`${method} ${path} -> ${err?.message || err}`, { cause: err });
  }
}

function errorChainHas(err, predicate) {
  const seen = new Set();
  for (let current = err; current && !seen.has(current); current = current.cause) {
    seen.add(current);
    if (predicate(current)) return true;
  }
  return false;
}

function isConnectionFailure(err) {
  if (errorChainHas(err, (current) =>
    current?.name === "TimeoutError" || current?.name === "AbortError")) return false;
  return errorChainHas(err, (current) =>
    current?.message === "fetch failed"
      || current?.code === "ECONNREFUSED"
      || current?.cause?.code === "ECONNREFUSED");
}

// Connection-level failure codes: the socket was refused, never established,
// or torn down mid-exchange. Distinct from a timeout, where the server did
// accept the connection and is merely slow (= busy, never "down").
// Handled here:
//   ECONNREFUSED  nothing is listening
//   ECONNRESET    listener accepted then died — the crashed-serve fingerprint
//   ECONNABORTED  connection aborted locally
//   EPIPE         wrote to a socket the peer had already closed
//   UND_ERR_SOCKET  undici's "other side closed" socket error
//   ENOTFOUND / EAI_AGAIN            host does not resolve
//   EHOSTUNREACH / EHOSTDOWN         host is gone
//   ENETUNREACH / ENETDOWN           route is gone
// undici surfaces all of these as a TypeError("fetch failed") whose `cause`
// carries the real code, so match on the cause chain rather than the message.
const CONNECTION_DEAD_CODES = new Set([
  "ECONNREFUSED",
  "ECONNRESET",
  "ECONNABORTED",
  "EPIPE",
  "UND_ERR_SOCKET",
  "ENOTFOUND",
  "EAI_AGAIN",
  "EHOSTUNREACH",
  "EHOSTDOWN",
  "ENETUNREACH",
  "ENETDOWN",
]);

function isConnectionDead(err) {
  if (errorChainHas(err, (current) =>
    current?.name === "TimeoutError" || current?.name === "AbortError")) return false;
  return errorChainHas(err, (current) => CONNECTION_DEAD_CODES.has(current?.code));
}

// Deliberately strict: this one gates the session-creation retry, where the
// question is "did the request definitely never reach the server?". Only a
// refused connection answers yes — a reset may have been received and acted
// on, and retrying it would create a duplicate session.
function isConnectionRefused(err) {
  return errorChainHas(err, (current) => current?.code === "ECONNREFUSED");
}

async function retryFirstApiCall(action, { sessionCreation = false } = {}) {
  try {
    return await action();
  } catch (err) {
    if (!isConnectionFailure(err) || (sessionCreation && !isConnectionRefused(err))) throw err;
    await ensureServer();
    return action();
  }
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

async function readMessages(sessionID, directory, timeoutMs) {
  // `|| []`: a null/204 body would otherwise TypeError on .length below.
  const msgs = (await api("GET", `/session/${sessionID}/message`, { directory, timeoutMs })) || [];
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
  // Terminal vs in-flight (verified on opencode 1.18.3, still present on
  // 1.18.6 (latest verified)): the assistant message record is created at turn
  // start with `info.time.completed` unset while it streams, and stamped (plus
  // `finish`) when the turn ends. So newest-is-assistant alone is NOT
  // "answered" — the completed stamp is. An erroring turn also terminates
  // with `info.error` set.
  const newest = msgs[msgs.length - 1];
  const newestInfo = newest?.info || {};
  const isAssistant = newestInfo.role === "assistant";
  const done = Boolean(newestInfo.time?.completed) || Boolean(newestInfo.error);
  const replied = isAssistant && done;
  // streaming: the turn has an in-flight assistant record — the session is
  // working even when /session/status claims idle (the status endpoint reports
  // {} for busy sessions — verified on opencode 1.18.3, still present on
  // 1.18.6 (latest verified); this is the reliable running signal).
  const streaming = isAssistant && !done;
  return { last, replied, streaming };
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
  {
    name: "opencode_health",
    description:
      "Report-only health dashboard: server reachability (down/healthy/busy/unhealthy), opencode server version, wrapper version (stale-wrapper detection), and running-session counts. Pass session_id for that session's live status. Never starts or heals the server — dispatch tools do that on their next call.",
    inputSchema: {
      type: "object",
      properties: {
        session_id: { type: "string", description: "Also report this session's status." },
        ...COMMON_PROPS,
      },
    },
  },
];

async function isRunning(sessionID, directory, timeoutMs) {
  const statuses = await api("GET", "/session/status", { directory, timeoutMs });
  const s = statuses?.[sessionID];
  if (s?.type) return s.type !== "idle";
  return false;
}

const ABORT_SETTLE_MS = 5000;
// Per-request cap for the settle poll only. Without it the poll inherits the
// 30s api() default, so two reads per iteration could stretch a nominal 5s
// cap past a minute -- the deadline is only testable between awaits.
const ABORT_SETTLE_READ_TIMEOUT_MS = 2000;

// POST /session/{id}/abort returns before the turn has actually stopped.
// Prompting into that gap can queue or reject the corrective turn, which only
// shows up ~30s later as a misattributed `stalled: true`. Poll until the
// session is neither status-busy nor streaming. Returns false if the cap
// expires, so the caller can say so rather than pretend the steer was clean.
async function waitForAbortSettled(sessionID, directory, capMs = ABORT_SETTLE_MS) {
  const deadline = Date.now() + capMs;
  const readTimeout = ABORT_SETTLE_READ_TIMEOUT_MS;
  for (;;) {
    try {
      const statusBusy = await isRunning(sessionID, directory, readTimeout);
      if (!statusBusy) {
        if (Date.now() >= deadline) return false;
        const { streaming } = await readMessages(sessionID, directory, readTimeout);
        if (!streaming) return true;
      }
    } catch (err) {
      // Best effort only: a read failure -- including this poll's own short
      // timeout -- must not turn a steer into an error, so fall through to
      // the prompt exactly as v1.3.0 did.
      log(`steer: abort-settle poll failed — ${String(err?.message || err)}`);
      return true;
    }
    if (Date.now() >= deadline) return false;
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
}

async function healthReport(args) {
  const report = { wrapper_version: VERSION, base: BASE, server: await probeHealth() };
  if (report.server === "down") return report;
  const g = await globalHealth();
  if (g) {
    report.server_version = g.version;
    report.server_healthy = g.healthy;
  }
  try {
    const statuses = await api("GET", "/session/status", {
      directory: args.directory,
      timeoutMs: 5000,
    });
    const entries = Object.entries(statuses || {});
    report.sessions_total = entries.length;
    report.sessions_running = entries.filter(([, s]) => s?.type && s.type !== "idle").length;
    if (entries.length === 0) {
      // The server answered but listed nothing. Verified on opencode 1.18.3,
      // still present on 1.18.6 (latest verified): that also happens while
      // sessions are generating, so these counts are a floor, not a truth.
      // opencode_status/opencode_wait do not rely on them (they read the message
      // stream), but the dashboard would otherwise read as a confident zero.
      report.sessions_note =
        "session counts may under-report while sessions are generating (/session/status returns {} for busy sessions — verified on opencode 1.18.3, still present on 1.18.6)";
    }
    if (args.session_id) report.session = statuses?.[args.session_id] ?? null;
  } catch (err) {
    report.session_status_error = String(err?.message || err);
  }
  return report;
}

async function callTool(name, args) {
  if (name === "opencode_health") return healthReport(args); // report-only: no ensureServer
  await ensureServer();
  const directory = args.directory || process.cwd();
  const common = { directory };

  switch (name) {
    case "opencode_run": {
      const session_id =
        args.session_id || (await retryFirstApiCall(
          () => createSession({ directory, title: args.title }),
          { sessionCreation: true },
        ));
      const r = await promptSync(session_id, { ...args, directory });
      return { session_id, directory, ...r };
    }
    case "opencode_fire": {
      const session_id =
        args.session_id || (await retryFirstApiCall(
          () => createSession({ directory, title: args.title }),
          { sessionCreation: true },
        ));
      await promptAsync(session_id, { ...args, directory });
      return { session_id, directory, dispatched: true };
    }
    case "opencode_status": {
      const statusBusy = await retryFirstApiCall(() => isRunning(args.session_id, directory));
      const { last, replied, streaming } = await readMessages(args.session_id, directory);
      return {
        session_id: args.session_id,
        running: statusBusy || streaming,
        replied,
        last,
        ...common,
      };
    }
    case "opencode_wait": {
      const cap = (args.timeout_s ?? 600) * 1000;
      const deadline = Date.now() + cap;
      let firstStatus = true;
      let idleUnreplied = 0;
      // done = the last prompt answered (completed stamp) and nothing running.
      // running = /session/status busy OR an in-flight assistant record
      // (`streaming`) — the status endpoint reports {} for busy sessions
      // (verified on opencode 1.18.3, still present on 1.18.6 (latest verified)),
      // so streaming is the signal that actually tracks work.
      for (;;) {
        const statusBusy = firstStatus
          ? await retryFirstApiCall(() => isRunning(args.session_id, directory))
          : await isRunning(args.session_id, directory);
        firstStatus = false;
        const { last, replied, streaming } = await readMessages(args.session_id, directory);
        const running = statusBusy || streaming;
        if (!running && replied) {
          return { session_id: args.session_id, running: false, replied, last, ...common };
        }
        // Stall: no running signal AND no assistant record for the prompt.
        // Right after dispatch that state is normal for a beat or two, but
        // persisting means the prompt died server-side without ever starting
        // a turn (log shape: `prompt_async failed` — bad model id,
        // provider/stream error) and no amount of waiting will flip it.
        // An in-flight assistant record (`streaming`) is progress, never a
        // stall — long thinking gaps must not trip this.
        idleUnreplied = !running && !replied ? idleUnreplied + 1 : 0;
        if (idleUnreplied >= 15) {
          return {
            session_id: args.session_id,
            running: false,
            replied: false,
            stalled: true,
            last,
            hint: "session idle ~30s with the prompt unanswered — the prompt died server-side (bad model id, provider/stream error, or a pending permission ask). Run opencode_health, then re-fire or steer this session.",
            ...common,
          };
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
      await retryFirstApiCall(
        () => api("POST", `/session/${args.session_id}/abort`, { directory }),
      );
      const settled = await waitForAbortSettled(args.session_id, directory);
      await promptAsync(args.session_id, { ...args, directory });
      const result = { session_id: args.session_id, steered: true, ...common };
      if (!settled) result.steer_note = "abort still settling";
      return result;
    }
    case "opencode_abort": {
      await retryFirstApiCall(
        () => api("POST", `/session/${args.session_id}/abort`, { directory }),
      );
      return { session_id: args.session_id, aborted: true, ...common };
    }
    default:
      throw new Error(`unknown tool: ${name}`);
  }
}

// ---------- stdio MCP plumbing (NDJSON JSON-RPC) ----------

const out = (obj) => process.stdout.write(JSON.stringify(obj) + "\n");

const DRAIN_TIMEOUT_MS = 10_000;
const FLUSH_TIMEOUT_MS = 2000;
// In-flight requests, so shutdown can drain them instead of killing the
// client's call mid-await. key -> { id, promise }; entries delete themselves
// when their handler settles, so whatever is left is genuinely unanswered.
const pending = new Map();
let pendingKey = 0;
let shuttingDown = false;
let signalsSeen = 0;

// Exactly one response per request id. shutdown() marks an entry answered when
// it emits the drain-timeout error, so a handler that settles afterwards --
// during the flush window, or any time before the process actually goes -- is
// silently dropped instead of writing a second response for the same id.
function respond(entry, obj) {
  if (entry.answered) return;
  entry.answered = true;
  out(obj);
}

async function handleLine(line, entry) {
  line = line.trim();
  if (!line) return;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch {
    log("unparseable line:", Buffer.byteLength(line), "bytes");
    return respond(entry, {
      jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" },
    });
  }
  // `JSON.parse("null")` succeeds and destructuring null throws — outside both
  // try blocks below, so it used to take the whole wrapper down. Scalars are
  // the same shape of problem; arrays (JSON-RPC batches) are not part of the
  // MCP stdio transport and would silently hang the client on the notification
  // path below.
  if (msg === null || typeof msg !== "object" || Array.isArray(msg)) {
    return respond(entry, {
      jsonrpc: "2.0", id: null, error: { code: -32600, message: "Invalid Request" },
    });
  }
  const { id, method, params } = msg;
  if (id === undefined) return; // notification — nothing to answer
  entry.id = id; // recorded before the first await, so shutdown can answer it

  try {
    if (method === "initialize") {
      const SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"];
      respond(entry, {
        jsonrpc: "2.0",
        id,
        result: {
          protocolVersion: SUPPORTED.includes(params?.protocolVersion)
            ? params.protocolVersion
            : "2025-03-26",
          capabilities: { tools: {} },
          serverInfo: { name: "opencode-mcp", version: VERSION },
        },
      });
    } else if (method === "ping") {
      respond(entry, { jsonrpc: "2.0", id, result: {} });
    } else if (method === "tools/list") {
      respond(entry, { jsonrpc: "2.0", id, result: { tools: TOOLS } });
    } else if (method === "tools/call") {
      const known = TOOLS.some((t) => t.name === params?.name);
      if (!known) {
        return respond(entry, {
          jsonrpc: "2.0",
          id,
          error: { code: -32602, message: `Unknown tool: ${params?.name}` },
        });
      }
      const result = await callTool(params.name, params.arguments || {});
      respond(entry, {
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result) }],
          structuredContent: result,
        },
      });
    } else {
      respond(entry, {
        jsonrpc: "2.0", id, error: { code: -32601, message: `unknown method: ${method}` },
      });
    }
  } catch (err) {
    respond(entry, {
      jsonrpc: "2.0",
      id,
      result: {
        content: [{ type: "text", text: `[opencode-mcp v${VERSION}] ${String(err?.message || err)}` }],
        isError: true,
      },
    });
  }
}

const rl = createInterface({ input: process.stdin });
rl.on("line", (line) => {
  if (shuttingDown) return; // draining: no new work
  const key = pendingKey++;
  const entry = { id: undefined, promise: null, answered: false };
  entry.promise = handleLine(line, entry).catch((err) => {
    // A rejecting handler used to be an unhandled rejection, i.e. a dead
    // wrapper. Answer the call if we know its id, and stay up either way.
    log("line handler failed:", String(err?.message || err));
    if (entry.id === undefined || entry.id === null) return;
    try {
      respond(entry, {
        jsonrpc: "2.0",
        id: entry.id,
        error: { code: -32603, message: `internal error: ${String(err?.message || err)}` },
      });
    } catch { /* stdout is gone — nothing left to report on */ }
  });
  pending.set(key, entry);
  entry.promise.finally(() => pending.delete(key));
});

function flushStdout(timeoutMs = FLUSH_TIMEOUT_MS) {
  // A zero-length write's callback fires only after every queued write has
  // been handed to the OS. Without this barrier process.exit() truncates the
  // responses we just wrote, which over a pipe is the same hang we are fixing.
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, timeoutMs);
    const done = () => {
      clearTimeout(timer);
      resolve();
    };
    try {
      process.stdout.write("", done);
    } catch {
      done();
    }
  });
}

async function shutdown(reason) {
  if (shuttingDown) return;
  shuttingDown = true;
  try {
    rl.close(); // stop accepting lines; no-op when the close event got us here
    const inFlight = [...pending.values()];
    if (inFlight.length) {
      log(`${reason} — draining ${inFlight.length} in-flight call(s), up to ${DRAIN_TIMEOUT_MS}ms`);
      await Promise.race([
        Promise.allSettled(inFlight.map((e) => e.promise)),
        new Promise((resolve) => setTimeout(resolve, DRAIN_TIMEOUT_MS)),
      ]);
    } else {
      log(`${reason} — no in-flight calls`);
    }
    // Whatever outlived the drain budget never answered its client. Say so
    // rather than exiting silently and leaving the call hanging forever.
    // Marking the entry answered first means a handler that settles later --
    // during the flush below -- cannot emit a second response for this id.
    for (const entry of pending.values()) {
      if (entry.id === undefined || entry.id === null || entry.answered) continue;
      entry.answered = true;
      log(`drain timed out for request ${entry.id}`);
      try {
        out({
          jsonrpc: "2.0",
          id: entry.id,
          error: { code: -32603, message: "wrapper shutting down" },
        });
      } catch { /* stdout is gone */ }
    }
    releaseHealLock(); // process.exit() skips the `finally` that normally does this
    await flushStdout();
  } catch (err) {
    log("shutdown failed:", String(err?.message || err));
  } finally {
    process.exit(0);
  }
}

rl.on("close", () => shutdown("stdin closed"));

function onSignal(signal) {
  signalsSeen++;
  // Only a second signal means "stop waiting". A supervisor normally closes
  // stdin and then sends SIGTERM, so treating that first signal as an
  // impatient repeat would abandon the very drain it just triggered.
  if (signalsSeen >= 2) {
    log(`received ${signal} again — abandoning the drain`);
    try { releaseHealLock(); } catch { /* best effort */ }
    process.exit(0);
  }
  if (shuttingDown) {
    log(`received ${signal} while draining — letting the drain finish`);
    return;
  }
  shutdown(`received ${signal}`);
}
// SIGKILL is uncatchable by design. SIGHUP is handled: the client's pipe or
// terminal going away is the same class of event as stdin EOF, so drain
// rather than take Node's default (terminate immediately).
for (const signal of ["SIGTERM", "SIGINT", "SIGHUP"]) {
  process.on(signal, () => onSignal(signal));
}

log(`ready — opencode-mcp v${VERSION}, opencode target ${BASE}`);
