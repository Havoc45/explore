#!/usr/bin/env python3
"""usage_probe.py — machine-readable quota meter for the Claude Code and Codex lanes.

Neither harness exposes its /usage meter to an agent; this probe reads the same
rate-limit surfaces the vendors' own UIs read and prints JSON, so a budget-aware
run (`explore --sub-continuous`) can read remaining quota without a human.

Providers:
  claude  POST one 1-token message to api.anthropic.com with the Claude Code
          OAuth token (macOS keychain "Claude Code-credentials", else
          ~/.claude/.credentials.json) and read the
          anthropic-ratelimit-unified-{5h,7d}-* response headers.
  codex   GET https://chatgpt.com/backend-api/wham/usage (fallback
          .../codex/usage) with the Codex CLI OAuth token
          ($CODEX_HOME/auth.json, else macOS keychain "Codex Auth") and read
          rate_limit.{primary,secondary}_window.

Output (stdout): one JSON object per poll. Single provider prints the provider
object; --provider both nests {"claude": {...}, "codex": {...}}. Fields:
  provider, ok, status, session_pct, session_reset_min, weekly_pct,
  weekly_reset_min, checked_at
`session_*` is the rolling window (Claude 5h / Codex primary), `weekly_*` the
long window (Claude 7d / Codex secondary). pct = percent USED, 0-100.

Exit code: 0 if every polled provider returned ok, else 1.

Flags:
  --provider claude|codex|both   default claude
  --interval SECONDS             poll forever, one JSON line per poll
                                 (default: single shot)
  --allow-refresh                on HTTP 401, refresh the OAuth token AND
                                 persist it back to the credential store.
                                 Off by default: a probe should not rewrite
                                 credentials it doesn't own (the CLI refreshes
                                 its own token on next use). Without it a 401
                                 reports status "token_expired".

Cost note: the claude probe spends one max_tokens=1 haiku call per poll
(the only authenticated surface that returns the unified headers); codex is a
free GET. Adapted from JeongJaeSoon/DeskPulse daemon providers; stdlib only.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

# ---------- shared plumbing ----------


def log(msg: str) -> None:
    print(f"[usage-probe] {msg}", file=sys.stderr, flush=True)


def http(method: str, url: str, headers: dict, body: dict | None = None,
         timeout: float = 20.0) -> tuple[int, dict, bytes]:
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


def keychain_read(service: str, account: str | None) -> str | None:
    cmd = ["security", "find-generic-password", "-s", service]
    if account:
        cmd += ["-a", account]
    cmd.append("-w")
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=10)
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip()


def keychain_write(service: str, account: str, blob: str) -> bool:
    try:
        subprocess.run(
            ["security", "add-generic-password", "-U", "-s", service, "-a", account, "-w", blob],
            check=True, capture_output=True, text=True, timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        log(f"keychain write failed: {e}")
        return False
    return True


def result(provider: str, ok: bool, status: str, session_pct: int = 0,
           session_reset_min: int = 0, weekly_pct: int = 0,
           weekly_reset_min: int = 0) -> dict:
    return {
        "provider": provider,
        "ok": ok,
        "status": status,
        "session_pct": session_pct,
        "session_reset_min": session_reset_min,
        "weekly_pct": weekly_pct,
        "weekly_reset_min": weekly_reset_min,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


# ---------- claude provider ----------

CLAUDE_KEYCHAIN_SERVICE = "Claude Code-credentials"
CLAUDE_CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_API_HEADERS = {
    "anthropic-version": "2023-06-01",
    "anthropic-beta": "oauth-2025-04-20",
    "Content-Type": "application/json",
    "User-Agent": "claude-code/2.1.5",
}
CLAUDE_API_BODY = {
    "model": "claude-haiku-4-5-20251001",
    "max_tokens": 1,
    "messages": [{"role": "user", "content": "hi"}],
}
CLAUDE_OAUTH_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CLAUDE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_OAUTH_SCOPE = " ".join([
    "user:profile", "user:inference", "user:sessions:claude_code",
    "user:mcp_servers", "user:file_upload",
])


def _claude_read_auth() -> tuple[str, dict] | None:
    """Return (storage, parsed-blob) from keychain (macOS) or the credentials file."""
    if sys.platform == "darwin":
        blob = keychain_read(CLAUDE_KEYCHAIN_SERVICE, getpass.getuser()) \
            or keychain_read(CLAUDE_KEYCHAIN_SERVICE, None)
        if blob:
            try:
                return ("keychain", json.loads(blob))
            except json.JSONDecodeError:
                pass
    try:
        return ("file", json.loads(CLAUDE_CREDENTIALS_PATH.read_text()))
    except (OSError, json.JSONDecodeError):
        return None


def _claude_tokens(data: dict) -> tuple[str, str | None] | None:
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        oauth = data
    access = oauth.get("accessToken")
    if isinstance(access, str) and access:
        refresh = oauth.get("refreshToken")
        return access, refresh if isinstance(refresh, str) else None
    return None


def _claude_persist(storage: str, data: dict, refresh_data: dict) -> None:
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        oauth = data
    oauth["accessToken"] = refresh_data["access_token"]
    if isinstance(refresh_data.get("refresh_token"), str):
        oauth["refreshToken"] = refresh_data["refresh_token"]
    if isinstance(refresh_data.get("expires_in"), (int, float)):
        oauth["expiresAt"] = int(time.time() * 1000 + refresh_data["expires_in"] * 1000)
    blob = json.dumps(data, indent=2)
    if storage == "keychain":
        keychain_write(CLAUDE_KEYCHAIN_SERVICE, getpass.getuser(), blob)
    else:
        CLAUDE_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLAUDE_CREDENTIALS_PATH.write_text(blob)
        CLAUDE_CREDENTIALS_PATH.chmod(0o600)


def _claude_refresh(storage: str, data: dict, refresh_token: str) -> str | None:
    status, _, body = http("POST", CLAUDE_OAUTH_TOKEN_URL,
                           {"Content-Type": "application/json"},
                           {"grant_type": "refresh_token",
                            "refresh_token": refresh_token,
                            "client_id": CLAUDE_OAUTH_CLIENT_ID,
                            "scope": CLAUDE_OAUTH_SCOPE}, timeout=30.0)
    if status >= 400:
        log(f"claude OAuth refresh HTTP {status}")
        return None
    try:
        refresh_data = json.loads(body)
    except json.JSONDecodeError:
        return None
    access = refresh_data.get("access_token")
    if not isinstance(access, str):
        return None
    _claude_persist(storage, data, refresh_data)
    log("claude OAuth refresh succeeded")
    return access


def _hdr_pct(headers: dict, name: str) -> int:
    try:
        return int(round(float(headers.get(name, "0")) * 100))
    except ValueError:
        return 0


def _hdr_reset_min(headers: dict, name: str) -> int:
    try:
        mins = (float(headers.get(name, "0")) - time.time()) / 60.0
    except ValueError:
        return 0
    return int(round(mins)) if mins > 0 else 0


def claude_usage(allow_refresh: bool) -> dict:
    auth = _claude_read_auth()
    if auth is None:
        return result("claude", False, "no_credentials")
    storage, data = auth
    tokens = _claude_tokens(data)
    if tokens is None:
        return result("claude", False, "no_access_token")
    access, refresh = tokens

    for attempt in range(2):
        headers = dict(CLAUDE_API_HEADERS, Authorization=f"Bearer {access}")
        try:
            status, resp_headers, body = http("POST", CLAUDE_API_URL, headers, CLAUDE_API_BODY)
        except (error.URLError, TimeoutError, OSError) as e:
            return result("claude", False, f"network_error: {e}")
        if status == 401 and attempt == 0:
            if not allow_refresh:
                return result("claude", False, "token_expired")
            if not refresh:
                return result("claude", False, "token_expired_no_refresh_token")
            refreshed = _claude_refresh(storage, data, refresh)
            if refreshed is None:
                return result("claude", False, "refresh_failed")
            access = refreshed
            continue
        if status >= 400:
            return result("claude", False, f"http_{status}: {body[:200].decode(errors='replace')}")
        return result(
            "claude", True,
            resp_headers.get("anthropic-ratelimit-unified-5h-status", "unknown"),
            session_pct=_hdr_pct(resp_headers, "anthropic-ratelimit-unified-5h-utilization"),
            session_reset_min=_hdr_reset_min(resp_headers, "anthropic-ratelimit-unified-5h-reset"),
            weekly_pct=_hdr_pct(resp_headers, "anthropic-ratelimit-unified-7d-utilization"),
            weekly_reset_min=_hdr_reset_min(resp_headers, "anthropic-ratelimit-unified-7d-reset"),
        )
    return result("claude", False, "unreachable")


# ---------- codex provider ----------

CODEX_KEYCHAIN_SERVICE = "Codex Auth"
CODEX_REFRESH_TOKEN_URL = "https://auth.openai.com/oauth/token"
CODEX_REFRESH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
CODEX_USAGE_URLS = (
    "https://chatgpt.com/backend-api/wham/usage",
    "https://chatgpt.com/backend-api/codex/usage",
)


def _codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def _codex_keychain_account() -> str:
    digest = hashlib.sha256(str(_codex_home().resolve(strict=False)).encode()).hexdigest()
    return f"cli|{digest[:16]}"


def _codex_read_auth() -> tuple[str, dict] | None:
    auth_path = _codex_home() / "auth.json"
    try:
        data = json.loads(auth_path.read_text())
        if isinstance(data, dict):
            return ("file", data)
    except (OSError, json.JSONDecodeError):
        pass
    if sys.platform == "darwin":
        blob = keychain_read(CODEX_KEYCHAIN_SERVICE, _codex_keychain_account())
        if blob:
            try:
                data = json.loads(blob)
                if isinstance(data, dict):
                    return ("keychain", data)
            except json.JSONDecodeError:
                pass
    return None


def _codex_account_id(tokens: dict) -> str | None:
    account_id = tokens.get("account_id")
    if isinstance(account_id, str):
        return account_id
    id_token = tokens.get("id_token")
    if not isinstance(id_token, str):
        return None
    parts = id_token.split(".")
    if len(parts) < 2:
        return None
    payload = parts[1]
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (ValueError, json.JSONDecodeError):
        return None
    auth = claims.get("https://api.openai.com/auth") if isinstance(claims, dict) else None
    account_id = auth.get("chatgpt_account_id") if isinstance(auth, dict) else None
    return account_id if isinstance(account_id, str) else None


def _codex_persist(storage: str, data: dict, refresh_data: dict) -> None:
    tokens = data.setdefault("tokens", {})
    if isinstance(tokens, dict):
        tokens["access_token"] = refresh_data["access_token"]
        if isinstance(refresh_data.get("refresh_token"), str):
            tokens["refresh_token"] = refresh_data["refresh_token"]
        if isinstance(refresh_data.get("id_token"), str):
            tokens["id_token"] = refresh_data["id_token"]
    blob = json.dumps(data, indent=2)
    if storage == "file":
        path = _codex_home() / "auth.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(blob)
        path.chmod(0o600)
    else:
        keychain_write(CODEX_KEYCHAIN_SERVICE, _codex_keychain_account(), blob)


def _codex_refresh(storage: str, data: dict, refresh_token: str) -> str | None:
    status, _, body = http("POST", CODEX_REFRESH_TOKEN_URL,
                           {"Content-Type": "application/json"},
                           {"client_id": CODEX_REFRESH_CLIENT_ID,
                            "grant_type": "refresh_token",
                            "refresh_token": refresh_token}, timeout=30.0)
    if status >= 400:
        log(f"codex OAuth refresh HTTP {status}")
        return None
    try:
        refresh_data = json.loads(body)
    except json.JSONDecodeError:
        return None
    access = refresh_data.get("access_token")
    if not isinstance(access, str):
        return None
    _codex_persist(storage, data, refresh_data)
    log("codex OAuth refresh succeeded")
    return access


def _codex_pct(value: object) -> int:
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _codex_reset_min(window: dict) -> int:
    reset_at = window.get("reset_at")
    if reset_at is not None:
        try:
            return max(0, int(round((float(reset_at) - time.time()) / 60.0)))
        except (TypeError, ValueError):
            pass
    try:
        return max(0, int(round(float(window.get("reset_after_seconds")) / 60.0)))
    except (TypeError, ValueError):
        return 0


def codex_usage(allow_refresh: bool) -> dict:
    auth = _codex_read_auth()
    if auth is None:
        return result("codex", False, "no_credentials")
    storage, data = auth
    tokens = data.get("tokens")
    if not isinstance(tokens, dict) or not isinstance(tokens.get("access_token"), str):
        status = "api_key_only" if isinstance(data.get("OPENAI_API_KEY"), str) else "no_chatgpt_tokens"
        return result("codex", False, status)
    access = tokens["access_token"]
    refresh = tokens.get("refresh_token")
    account_id = _codex_account_id(tokens)

    for attempt in range(2):
        headers = {"Accept": "application/json", "Authorization": f"Bearer {access}",
                   "User-Agent": "codex-cli"}
        if account_id:
            headers["ChatGPT-Account-Id"] = account_id
        last = None
        for url in CODEX_USAGE_URLS:
            try:
                status, _, body = http("GET", url, headers)
            except (error.URLError, TimeoutError, OSError) as e:
                return result("codex", False, f"network_error: {e}")
            if status == 404:
                last = (status, body)
                continue
            if status == 401 and attempt == 0:
                if not allow_refresh:
                    return result("codex", False, "token_expired")
                if not isinstance(refresh, str):
                    return result("codex", False, "token_expired_no_refresh_token")
                refreshed = _codex_refresh(storage, data, refresh)
                if refreshed is None:
                    return result("codex", False, "refresh_failed")
                access = refreshed
                last = "retry"
                break
            if status >= 400:
                return result("codex", False, f"http_{status}: {body[:200].decode(errors='replace')}")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return result("codex", False, "bad_json")
            return _codex_parse(payload)
        if last == "retry":
            continue
        return result("codex", False, "usage_endpoint_unavailable")
    return result("codex", False, "unreachable")


def _codex_parse(payload: object) -> dict:
    if not isinstance(payload, dict):
        return result("codex", False, "bad_usage_payload")
    rate_limit = payload.get("rate_limit")
    if not isinstance(rate_limit, dict):
        return result("codex", False, "no_rate_limit")
    primary = rate_limit.get("primary_window")
    if not isinstance(primary, dict):
        return result("codex", False, "no_windows")
    # Some plans (e.g. prolite) expose a single window: secondary is null.
    # Mirror primary into the weekly fields so consumers always see the budget.
    secondary = rate_limit.get("secondary_window")
    if not isinstance(secondary, dict):
        secondary = primary
    reached_type = payload.get("rate_limit_reached_type")
    if rate_limit.get("allowed") is True:
        status = "allowed"
    elif isinstance(reached_type, str):
        status = reached_type
    elif rate_limit.get("limit_reached") is True:
        status = "limited"
    else:
        status = "unknown"
    return result(
        "codex", True, status,
        session_pct=_codex_pct(primary.get("used_percent")),
        session_reset_min=_codex_reset_min(primary),
        weekly_pct=_codex_pct(secondary.get("used_percent")),
        weekly_reset_min=_codex_reset_min(secondary),
    )


# ---------- main ----------

PROVIDERS = {"claude": claude_usage, "codex": codex_usage}


def poll(provider: str, allow_refresh: bool) -> tuple[dict, bool]:
    if provider == "both":
        out = {name: fn(allow_refresh) for name, fn in PROVIDERS.items()}
        return out, all(v["ok"] for v in out.values())
    out = PROVIDERS[provider](allow_refresh)
    return out, out["ok"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--provider", choices=["claude", "codex", "both"], default="claude")
    ap.add_argument("--interval", type=float, default=0,
                    help="poll every N seconds forever (default: single shot)")
    ap.add_argument("--allow-refresh", action="store_true",
                    help="on 401, refresh the OAuth token and persist it back")
    args = ap.parse_args()

    while True:
        out, ok = poll(args.provider, args.allow_refresh)
        print(json.dumps(out), flush=True)
        if args.interval <= 0:
            return 0 if ok else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
