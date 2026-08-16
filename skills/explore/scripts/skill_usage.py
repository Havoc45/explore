#!/usr/bin/env python3
"""skill_usage.py — per-skill invocation census over harness project transcripts.

The plugin manager shows which skills are installed, never which ones earn
their context budget; this script reads the session transcripts under a
~/.claude/projects/<slug> directory and counts Skill-tool invocations, so a
reconcile run (references/closing-the-loop.md "Skill-usage glossary") can
tell skills in active use from installed-but-idle ones.

Method (line shape verified live 2026-08-16): each transcript line is one
JSON object; an assistant message's content may carry a tool_use block with
name "Skill" and input {"skill": "<name>"} — every line is parsed with
json.loads, never regex-scraped. Slash-command invocations are counted
best-effort when a <command-name> marker appears in user-message text.

Join: each invoked name is matched against the installed-plugin inventory at
~/.claude/plugins/installed_plugins.json ({"version": 2, "plugins":
{"<name>@<marketplace>": [{"installPath": ...}]}}) by probing each
installPath for skills/<name>/ and commands/<name>.md. A missing or
unparseable inventory is fail-open: invocation counts stand, source_plugin
fields come back null.

Output (stdout): one JSON object:
  {"generated_at", "project", "skills": {"<skill>": {"count", "last_used",
   "source_plugin" (null when unmatched)}, ...}, "installed_not_invoked":
   [...], "method_notes": [...]}
last_used is an ISO date from the line's timestamp field when present, else
the transcript file's mtime; the census covers the last --days days.
Privacy floor: only tool/command names, dates, and counts are emitted —
never prompt or message text.

Exit code: 0 on success; 1 on a missing/unreadable project directory,
reported as one structured {"ok": false, ...} JSON object; the script never
exits with a traceback.

Flags:
  --project PATH   project transcript directory (~/.claude/projects/<slug>);
                   required
  --days N         count invocations from the last N days (default 90)

Stdlib only; adapted from usage_probe.py's structured-failure conventions.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

INVENTORY_RELPATH = (".claude", "plugins", "installed_plugins.json")
SKILL_TOOL_NAME = "Skill"
COMMAND_MARKER = "<command-name>"
COMMAND_MARKER_END = "</command-name>"


def log(msg: str) -> None:
    print(f"[skill-usage] {msg}", file=sys.stderr, flush=True)


def emit(payload: dict) -> None:
    print(json.dumps(payload), flush=True)


# ---------- line census ----------

def _iso_date(value: object) -> str | None:
    """The YYYY-MM-DD prefix of an ISO-8601 timestamp string; None when the
    value is absent or unparseable. ISO dates compare correctly as strings,
    so the window filter never needs datetime arithmetic on the hot path.
    """
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(timezone.utc).date().isoformat()


def _mtime_date(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()
    except OSError:
        return None


def _message_of(obj: dict) -> dict | None:
    msg = obj.get("message")
    return msg if isinstance(msg, dict) else None


def _content_texts(content: object) -> list[str]:
    """The text strings of a message content field, which may itself be a
    plain string or a list of typed blocks."""
    if isinstance(content, str):
        return [content]
    texts: list[str] = []
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" \
                    and isinstance(block.get("text"), str):
                texts.append(block["text"])
    return texts


def _skill_tool_uses(obj: dict) -> list[str]:
    """Skill names from tool_use blocks in an assistant message."""
    msg = _message_of(obj)
    if msg is None:
        return []
    names: list[str] = []
    content = msg.get("content")
    if not isinstance(content, list):
        return names
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        if block.get("name") != SKILL_TOOL_NAME:
            continue
        tool_input = block.get("input")
        name = tool_input.get("skill") if isinstance(tool_input, dict) else None
        if isinstance(name, str) and name:
            names.append(name)
    return names


def _slash_commands(obj: dict) -> tuple[list[str], int]:
    """(command names, marker-only count) from <command-name> markers in a
    user message's text. Best-effort: a marker with no parseable name (no
    closing tag, empty body) is returned in the count, not the names."""
    msg = _message_of(obj)
    if msg is None:
        return [], 0
    names: list[str] = []
    marker_only = 0
    for text in _content_texts(msg.get("content")):
        start = text.find(COMMAND_MARKER)
        while start != -1:
            body_start = start + len(COMMAND_MARKER)
            end = text.find(COMMAND_MARKER_END, body_start)
            token = text[body_start:end] if end != -1 else ""
            token = token.strip().lstrip("/")
            if token:
                names.append(token)
            else:
                marker_only += 1
            start = text.find(COMMAND_MARKER, body_start)
    return names, marker_only


# ---------- installed inventory ----------

def load_inventory(home: Path) -> tuple[dict, dict, list[str], str]:
    """(skill_source, command_source, installed_skills, status).

    skill_source maps skills/<name>/ to its "<plugin>@<marketplace>" key,
    command_source maps commands/<name>.md likewise; installed_skills lists
    every discovered skill directory. Any failure — missing file, bad JSON,
    wrong shape, unreadable installPath — is one fail-open status string;
    the census does not depend on the inventory.
    """
    try:
        data = json.loads(home.joinpath(*INVENTORY_RELPATH).read_text())
    except (OSError, ValueError, RuntimeError):
        return {}, {}, [], "inventory_unavailable"
    plugins = data.get("plugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return {}, {}, [], "inventory_unavailable"
    skill_source: dict = {}
    command_source: dict = {}
    installed: list[str] = []
    collisions = 0
    for key, installs in plugins.items():
        if not isinstance(installs, list):
            continue
        for inst in installs:
            if not isinstance(inst, dict):
                continue
            install_path = inst.get("installPath")
            if not isinstance(install_path, str) or not install_path:
                continue
            root = Path(install_path).expanduser()
            try:
                skill_dirs = sorted(p for p in (root / "skills").iterdir()
                                    if p.is_dir() and (p / "SKILL.md").is_file())
            except OSError:
                skill_dirs = []
            for skill_dir in skill_dirs:
                installed.append(skill_dir.name)
                if skill_dir.name in skill_source:
                    collisions += 1
                else:
                    skill_source[skill_dir.name] = key
            try:
                command_files = sorted((root / "commands").glob("*.md"))
            except OSError:
                command_files = []
            for command_file in command_files:
                command_source.setdefault(command_file.stem, key)
    status = "inventory_loaded"
    if collisions:
        status = f"inventory_loaded ({collisions} duplicate skill names, first install won)"
    return skill_source, command_source, sorted(set(installed)), status


# ---------- scan ----------

def scan(project: Path, days: int) -> dict:
    """Run the census and assemble the output object. Raised exceptions are
    converted to a structured failure by main(); nothing here prints."""
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(days=days)).date().isoformat()
    files = sorted(p for p in project.glob("*.jsonl") if p.is_file())

    counts: dict[str, int] = {}
    last_used: dict[str, str] = {}
    bad_json = 0
    undated = 0
    unreadable_files = 0

    def record(name: str, date: str) -> None:
        counts[name] = counts.get(name, 0) + 1
        if name not in last_used or date > last_used[name]:
            last_used[name] = date

    for path in files:
        fallback_date = _mtime_date(path)
        try:
            handle = path.open(encoding="utf-8", errors="replace")
        except OSError:
            unreadable_files += 1
            continue
        with handle:
            for raw in handle:
                line = raw.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    bad_json += 1
                    continue
                if not isinstance(obj, dict):
                    continue
                date = _iso_date(obj.get("timestamp")) or fallback_date
                if date is None:
                    undated += 1
                    continue
                if date < cutoff:
                    continue
                is_assistant = obj.get("type") == "assistant" \
                    or (isinstance(_message_of(obj), dict) and _message_of(obj).get("role") == "assistant")
                is_user = obj.get("type") == "user" \
                    or (isinstance(_message_of(obj), dict) and _message_of(obj).get("role") == "user")
                if is_assistant:
                    for name in _skill_tool_uses(obj):
                        record(name, date)
                if is_user:
                    names, _ = _slash_commands(obj)
                    for cmd_name in names:
                        record(cmd_name, date)

    skill_source, command_source, installed, inventory_status = \
        load_inventory(Path.home())

    skills = {
        name: {
            "count": counts[name],
            "last_used": last_used[name],
            "source_plugin": skill_source.get(name) or command_source.get(name),
        }
        for name in sorted(counts)
    }
    installed_not_invoked = [name for name in installed if name not in counts]

    notes = [
        f"window: {days}d ending {now.date().isoformat()}; "
        f"{len(files)} transcript files scanned",
        "skill-tool: assistant tool_use blocks parsed as JSON "
        f"(name={SKILL_TOOL_NAME}, input.skill)",
        "slash-command: best-effort <command-name> markers in user-message text",
        "last_used: line timestamp when present, else transcript file mtime",
        inventory_status,
    ]
    if bad_json:
        notes.append(f"{bad_json} unparseable lines skipped")
    if undated:
        notes.append(f"{undated} lines skipped (no timestamp, no mtime)")
    if unreadable_files:
        notes.append(f"{unreadable_files} transcript files unreadable")
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "project": str(project),
        "skills": skills,
        "installed_not_invoked": installed_not_invoked,
        "method_notes": notes,
    }


# ---------- main ----------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", required=True,
                    help="project transcript directory (~/.claude/projects/<slug>)")
    ap.add_argument("--days", type=int, default=90,
                    help="count invocations from the last N days (default 90)")
    args = ap.parse_args()

    try:
        project = Path(args.project).expanduser()
    except RuntimeError:
        project = None
    if project is None or not project.is_dir():
        emit({"ok": False, "status": "missing_project_dir",
              "project": args.project})
        return 1
    if args.days < 1:
        emit({"ok": False, "status": "invalid_days", "project": str(project)})
        return 1
    try:
        out = scan(project, args.days)
    except Exception as e:  # last resort: consumers parse stdout, so an
        # unforeseen environmental failure has to be JSON, not a traceback.
        # The status carries the exception's class only — a message can quote
        # the line being parsed, which on these paths is transcript content.
        log(f"scan raised {type(e).__name__}")
        emit({"ok": False, "status": f"internal_error: {type(e).__name__}",
              "project": str(project)})
        return 1
    emit(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
