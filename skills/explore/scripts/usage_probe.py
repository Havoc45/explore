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

The four quota fields are `null` whenever the probe has no trustworthy number
(every ok:false result, and any window the provider did not report) — never a
fabricated 0, which a consumer would read as "full quota remaining". A genuine
0 is only ever emitted under ok:true. If a provider stops sending the quota
headers/fields the probe reads, the result is ok:false with status
"schema_error: missing <names>" — a provider-format change, not a full window.

Exit code: 0 if every polled provider returned ok, else 1. Environmental
failures (no credentials, network, malformed payloads) are reported as
structured JSON with ok:false; the probe never exits with a traceback.

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
import math
import os
import re
import subprocess
import sys
import time
from http.client import HTTPException
from pathlib import Path
from urllib import error, request

# ---------- shared plumbing ----------

# Everything a transport can raise for an environmental reason. HTTPException
# is not an OSError (http.client.IncompleteRead, RemoteDisconnected on a read),
# so catching OSError alone still lets a truncated response traceback.
NETWORK_ERRORS = (error.URLError, TimeoutError, OSError, HTTPException)

# Sentinel returned in place of (storage, blob) when a credential store is
# readable but does not decode to a JSON object.
CREDENTIALS_MALFORMED = "malformed_credentials"


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


def result(provider: str, ok: bool, status: str, session_pct: int | None = None,
           session_reset_min: int | None = None, weekly_pct: int | None = None,
           weekly_reset_min: int | None = None) -> dict:
    """One probe outcome, with the stable field set consumers read.

    The four quota fields default to None (JSON null) so that a result carrying
    no usable quota reading says so, rather than reporting 0 — which a consumer
    computing `remaining = 100 - session_pct` would read as a full window.
    """
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
CLAUDE_CREDENTIALS_RELPATH = (".claude", ".credentials.json")
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
CLAUDE_HDR_STATUS = "anthropic-ratelimit-unified-5h-status"
CLAUDE_HDR_5H_PCT = "anthropic-ratelimit-unified-5h-utilization"
CLAUDE_HDR_5H_RESET = "anthropic-ratelimit-unified-5h-reset"
CLAUDE_HDR_7D_PCT = "anthropic-ratelimit-unified-7d-utilization"
CLAUDE_HDR_7D_RESET = "anthropic-ratelimit-unified-7d-reset"
CLAUDE_OAUTH_TOKEN_URL = "https://platform.claude.com/v1/oauth/token"
CLAUDE_OAUTH_CLIENT_ID = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
CLAUDE_OAUTH_SCOPE = " ".join([
    "user:profile", "user:inference", "user:sessions:claude_code",
    "user:mcp_servers", "user:file_upload",
])


def _claude_credentials_path() -> Path:
    """Resolved lazily, mirroring _codex_home(): Path.home() raises RuntimeError
    when the home directory is unresolvable, and at module scope that would be a
    traceback at import time — before probe()'s catch-all exists to structure it.
    """
    return Path.home().joinpath(*CLAUDE_CREDENTIALS_RELPATH)


def _claude_read_auth() -> tuple[str, dict] | str | None:
    """Return (storage, parsed-blob) from keychain (macOS) or the credentials file.

    A missing file returns None unless a keychain value already decoded to a
    non-null, non-dict value. An unreadable or undecodable file returns
    CREDENTIALS_MALFORMED. A keychain value that decodes to a non-null,
    non-dict value marks that store unusable; one that fails to decode falls
    through without doing so, preserving the existing behavior.
    """
    saw_unusable = False
    if sys.platform == "darwin":
        blob = keychain_read(CLAUDE_KEYCHAIN_SERVICE, getpass.getuser()) \
            or keychain_read(CLAUDE_KEYCHAIN_SERVICE, None)
        if blob:
            try:
                parsed = json.loads(blob)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                return ("keychain", parsed)
            saw_unusable = parsed is not None
    try:
        parsed = json.loads(_claude_credentials_path().read_text())
    except RuntimeError as e:  # home directory unresolvable
        log(f"claude home unresolvable: {type(e).__name__}")
        return CREDENTIALS_MALFORMED if saw_unusable else None
    except FileNotFoundError:
        return CREDENTIALS_MALFORMED if saw_unusable else None
    except (ValueError, OSError):  # ValueError covers JSON and decoding errors
        return CREDENTIALS_MALFORMED
    return ("file", parsed) if isinstance(parsed, dict) else CREDENTIALS_MALFORMED


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
    """Write the refreshed token back. Best effort: a store the probe cannot
    write does not invalidate the token it just obtained."""
    oauth = data.get("claudeAiOauth")
    if not isinstance(oauth, dict):
        oauth = data
    oauth["accessToken"] = refresh_data["access_token"]
    if isinstance(refresh_data.get("refresh_token"), str):
        oauth["refreshToken"] = refresh_data["refresh_token"]
    if isinstance(refresh_data.get("expires_in"), (int, float)):
        oauth["expiresAt"] = int(time.time() * 1000 + refresh_data["expires_in"] * 1000)
    blob = json.dumps(data, indent=2)
    try:
        if storage == "keychain":
            keychain_write(CLAUDE_KEYCHAIN_SERVICE, getpass.getuser(), blob)
        else:
            path = _claude_credentials_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(blob)
            path.chmod(0o600)
    except (OSError, RuntimeError) as e:
        log(f"claude credential write failed: {type(e).__name__}")


def _claude_refresh(storage: str, data: dict, refresh_token: str) -> tuple[str | None, str]:
    """(access_token, "") on success, (None, "<reason>") on failure — the reason
    names the failure class only, never a response body or a token."""
    try:
        status, _, body = http("POST", CLAUDE_OAUTH_TOKEN_URL,
                               {"Content-Type": "application/json"},
                               {"grant_type": "refresh_token",
                                "refresh_token": refresh_token,
                                "client_id": CLAUDE_OAUTH_CLIENT_ID,
                                "scope": CLAUDE_OAUTH_SCOPE}, timeout=30.0)
    except NETWORK_ERRORS as e:
        log(f"claude OAuth refresh transport error: {type(e).__name__}")
        return None, type(e).__name__
    if status >= 400:
        log(f"claude OAuth refresh HTTP {status}")
        return None, f"http_{status}"
    try:
        refresh_data = json.loads(body)
    except ValueError:
        return None, "bad_json"
    if not isinstance(refresh_data, dict):
        return None, "bad_json"
    access = refresh_data.get("access_token")
    if not isinstance(access, str) or not access:
        return None, "no_access_token"
    _claude_persist(storage, data, refresh_data)
    log("claude OAuth refresh succeeded")
    return access, ""


def _hdr(headers: dict, name: str) -> str | None:
    """Case-insensitive header lookup.

    HTTP field names are case-insensitive (RFC 9110 §5.1) but urllib hands back
    whatever casing the server sent, so a strict parser must not treat a casing
    change as a missing header.
    """
    value = headers.get(name)
    if value is not None:
        return value
    lowered = name.lower()
    for key, val in headers.items():
        if key.lower() == lowered:
            return val
    return None


def _finite(value: object) -> float | None:
    """value as a finite float, else None.

    Booleans are rejected before the conversion: float(True) is 1.0, so a JSON
    `true` in a quota field would otherwise pass strictness and report 1% used.
    NaN and infinity are not data either.
    """
    if isinstance(value, bool):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    return num if math.isfinite(num) else None


def _hdr_pct(headers: dict, name: str) -> int | None:
    """Percent used (0-100) from a 0-1 utilization header.

    None when the header is absent or non-numeric — absence is a provider
    format change, and must stay distinguishable from a genuine 0% used.
    """
    fraction = _finite(_hdr(headers, name))
    return None if fraction is None else int(round(fraction * 100))


def _hdr_reset_min(headers: dict, name: str) -> int | None:
    """Minutes until the window resets, from a unix-epoch header.

    None when the header is absent or non-numeric; a window already past its
    reset instant is a genuine 0.
    """
    reset_at = _finite(_hdr(headers, name))
    if reset_at is None:
        return None
    mins = (reset_at - time.time()) / 60.0
    return int(round(mins)) if mins > 0 else 0


def claude_usage(allow_refresh: bool) -> dict:
    auth = _claude_read_auth()
    if auth is None:
        return result("claude", False, "no_credentials")
    if not isinstance(auth, tuple):
        return result("claude", False, "credential_parse_error")
    storage, data = auth
    tokens = _claude_tokens(data)
    if tokens is None:
        return result("claude", False, "no_access_token")
    access, refresh = tokens

    for attempt in range(2):
        headers = dict(CLAUDE_API_HEADERS, Authorization=f"Bearer {access}")
        try:
            status, resp_headers, body = http("POST", CLAUDE_API_URL, headers, CLAUDE_API_BODY)
        except NETWORK_ERRORS as e:
            return result("claude", False, f"network_error: {e}")
        if status == 401 and attempt == 0:
            if not allow_refresh:
                return result("claude", False, "token_expired")
            if not refresh:
                return result("claude", False, "token_expired_no_refresh_token")
            refreshed, reason = _claude_refresh(storage, data, refresh)
            if refreshed is None:
                return result("claude", False, f"refresh_failed: {reason}")
            access = refreshed
            continue
        if status >= 400:
            return result("claude", False, f"http_{status}: {body[:200].decode(errors='replace')}")
        session_pct = _hdr_pct(resp_headers, CLAUDE_HDR_5H_PCT)
        session_reset_min = _hdr_reset_min(resp_headers, CLAUDE_HDR_5H_RESET)
        weekly_pct = _hdr_pct(resp_headers, CLAUDE_HDR_7D_PCT)
        weekly_reset_min = _hdr_reset_min(resp_headers, CLAUDE_HDR_7D_RESET)
        missing = [name for name, value in (
            (CLAUDE_HDR_5H_PCT, session_pct),
            (CLAUDE_HDR_5H_RESET, session_reset_min),
            (CLAUDE_HDR_7D_PCT, weekly_pct),
            (CLAUDE_HDR_7D_RESET, weekly_reset_min),
        ) if value is None]
        if missing:
            return result("claude", False, f"schema_error: missing {', '.join(missing)}")
        return result(
            "claude", True,
            _hdr(resp_headers, CLAUDE_HDR_STATUS) or "unknown",
            session_pct=session_pct,
            session_reset_min=session_reset_min,
            weekly_pct=weekly_pct,
            weekly_reset_min=weekly_reset_min,
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


def _codex_read_auth() -> tuple[str, dict] | str | None:
    """Return parsed credentials from the file or keychain.

    A missing file falls through to the keychain; an unreadable or undecodable
    file marks the result CREDENTIALS_MALFORMED unless the keychain supplies a
    valid dict. A keychain value that decodes to a non-null, non-dict value
    marks that store unusable; one that fails to decode falls through without
    doing so, preserving the existing behavior.
    """
    try:
        auth_path = _codex_home() / "auth.json"
    except RuntimeError as e:  # expanduser() with no resolvable home
        log(f"codex home unresolvable: {type(e).__name__}")
        return None
    saw_unusable = False
    try:
        data = json.loads(auth_path.read_text())
        if isinstance(data, dict):
            return ("file", data)
        saw_unusable = data is not None
    except FileNotFoundError:
        pass
    except (ValueError, OSError):  # ValueError covers JSON and decoding errors
        saw_unusable = True
    if sys.platform == "darwin":
        blob = keychain_read(CODEX_KEYCHAIN_SERVICE, _codex_keychain_account())
        if blob:
            try:
                data = json.loads(blob)
                if isinstance(data, dict):
                    return ("keychain", data)
                saw_unusable = saw_unusable or data is not None
            except ValueError:
                pass
    return CREDENTIALS_MALFORMED if saw_unusable else None


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
    """Write the refreshed token back. Best effort: a store the probe cannot
    write does not invalidate the token it just obtained."""
    tokens = data.setdefault("tokens", {})
    if isinstance(tokens, dict):
        tokens["access_token"] = refresh_data["access_token"]
        if isinstance(refresh_data.get("refresh_token"), str):
            tokens["refresh_token"] = refresh_data["refresh_token"]
        if isinstance(refresh_data.get("id_token"), str):
            tokens["id_token"] = refresh_data["id_token"]
    blob = json.dumps(data, indent=2)
    try:
        if storage == "file":
            path = _codex_home() / "auth.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(blob)
            path.chmod(0o600)
        else:
            keychain_write(CODEX_KEYCHAIN_SERVICE, _codex_keychain_account(), blob)
    except (OSError, RuntimeError) as e:
        log(f"codex credential write failed: {type(e).__name__}")


def _codex_refresh(storage: str, data: dict, refresh_token: str) -> tuple[str | None, str]:
    """(access_token, "") on success, (None, "<reason>") on failure — the reason
    names the failure class only, never a response body or a token."""
    try:
        status, _, body = http("POST", CODEX_REFRESH_TOKEN_URL,
                               {"Content-Type": "application/json"},
                               {"client_id": CODEX_REFRESH_CLIENT_ID,
                                "grant_type": "refresh_token",
                                "refresh_token": refresh_token}, timeout=30.0)
    except NETWORK_ERRORS as e:
        log(f"codex OAuth refresh transport error: {type(e).__name__}")
        return None, type(e).__name__
    if status >= 400:
        log(f"codex OAuth refresh HTTP {status}")
        return None, f"http_{status}"
    try:
        refresh_data = json.loads(body)
    except ValueError:
        return None, "bad_json"
    if not isinstance(refresh_data, dict):
        return None, "bad_json"
    access = refresh_data.get("access_token")
    if not isinstance(access, str) or not access:
        return None, "no_access_token"
    _codex_persist(storage, data, refresh_data)
    log("codex OAuth refresh succeeded")
    return access, ""


def _codex_pct(value: object) -> int | None:
    """Percent used (0-100), clamped; None when the field is absent or non-numeric."""
    pct = _finite(value)
    return None if pct is None else max(0, min(100, int(round(pct))))


def _codex_reset_min(window: dict) -> int | None:
    """Minutes until this window resets, from reset_at (unix) or
    reset_after_seconds; None when neither field carries a usable number."""
    reset_at = _finite(window.get("reset_at"))
    if reset_at is not None:
        return max(0, int(round((reset_at - time.time()) / 60.0)))
    reset_after = _finite(window.get("reset_after_seconds"))
    if reset_after is not None:
        return max(0, int(round(reset_after / 60.0)))
    return None


def codex_usage(allow_refresh: bool) -> dict:
    auth = _codex_read_auth()
    if auth is None:
        return result("codex", False, "no_credentials")
    if not isinstance(auth, tuple):
        return result("codex", False, "credential_parse_error")
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
            except NETWORK_ERRORS as e:
                return result("codex", False, f"network_error: {e}")
            if status == 404:
                last = (status, body)
                continue
            if status == 401 and attempt == 0:
                if not allow_refresh:
                    return result("codex", False, "token_expired")
                if not isinstance(refresh, str):
                    return result("codex", False, "token_expired_no_refresh_token")
                refreshed, reason = _codex_refresh(storage, data, refresh)
                if refreshed is None:
                    return result("codex", False, f"refresh_failed: {reason}")
                access = refreshed
                last = "retry"
                break
            if status >= 400:
                return result("codex", False, f"http_{status}: {body[:200].decode(errors='replace')}")
            try:
                payload = json.loads(body)
            except ValueError:  # JSON and decoding errors both land here
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
        return result("codex", False, "schema_error: missing rate_limit")
    primary = rate_limit.get("primary_window")
    if not isinstance(primary, dict):
        return result("codex", False, "schema_error: missing primary_window")
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
    session_pct = _codex_pct(primary.get("used_percent"))
    session_reset_min = _codex_reset_min(primary)
    weekly_pct = _codex_pct(secondary.get("used_percent"))
    weekly_reset_min = _codex_reset_min(secondary)
    missing = [name for name, value in (
        ("primary_window.used_percent", session_pct),
        ("primary_window.reset_at|reset_after_seconds", session_reset_min),
    ) if value is None]
    if secondary is not primary:  # a mirrored secondary is already covered above
        missing += [name for name, value in (
            ("secondary_window.used_percent", weekly_pct),
            ("secondary_window.reset_at|reset_after_seconds", weekly_reset_min),
        ) if value is None]
    if missing:
        return result("codex", False, f"schema_error: missing {', '.join(missing)}")
    return result(
        "codex", True, status,
        session_pct=session_pct,
        session_reset_min=session_reset_min,
        weekly_pct=weekly_pct,
        weekly_reset_min=weekly_reset_min,
    )


# ---------- main ----------

PROVIDERS = {"claude": claude_usage, "codex": codex_usage}


def probe(provider: str, allow_refresh: bool) -> dict:
    """Run one provider probe, converting anything the targeted handlers missed
    into a structured result. Consumers parse this output, so an unforeseen
    environmental failure has to be JSON, not a traceback. The status carries
    the exception's class only — a message can quote the payload being parsed,
    which on these paths is credential material.
    """
    try:
        return PROVIDERS[provider](allow_refresh)
    except Exception as e:  # last resort: never let the probe die on stdout
        log(f"{provider} probe raised {type(e).__name__}")
        return result(provider, False, f"internal_error: {type(e).__name__}")


def poll(provider: str, allow_refresh: bool) -> tuple[dict, bool]:
    if provider == "both":
        out = {name: probe(name, allow_refresh) for name in PROVIDERS}
        return out, all(v["ok"] for v in out.values())
    out = probe(provider, allow_refresh)
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
