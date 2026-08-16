#!/usr/bin/env bash
# companion-detect.sh — SessionStart hook.
# Reads the harness plugin registry ($HOME/.claude/plugins/installed_plugins.json)
# and emits AT MOST ONE compact line naming detected explore companion plugins.
# Absent/unparseable registry -> `claude plugin list` fallback -> silent exit 0.
# SessionStart stdout becomes session context (additionalContext).

set -u

REGISTRY="${HOME:-}/.claude/plugins/installed_plugins.json"

# ---------------------------------------------------------------------------
# 1. Collect "plugin-name installPath" pairs.
#    Registry shape (verified 2026-08-16):
#      {"version": 2, "plugins": {"<name>@<marketplace>": [ {..., "installPath": ...}, ... ]}}
#    The newest install is the LAST element of each array.
# ---------------------------------------------------------------------------
PAIRS=""

if [ -f "$REGISTRY" ]; then
  PAIRS="$(REGISTRY="$REGISTRY" python3 - <<'PYEOF' 2>/dev/null
import json, os, sys
try:
    with open(os.environ["REGISTRY"], "r", encoding="utf-8") as fh:
        data = json.load(fh)
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        sys.exit(1)
    for key, installs in plugins.items():
        name = key.split("@", 1)[0]
        path = ""
        if isinstance(installs, list) and installs:
            last = installs[-1]
            if isinstance(last, dict):
                path = last.get("installPath") or ""
        sys.stdout.write("%s %s\n" % (name, path))
except Exception:
    sys.exit(1)
PYEOF
)"
fi

# ---------------------------------------------------------------------------
# 2. Fallback: `claude plugin list` (names only, no install paths).
#    Output lines look like: "  ❯ caveman@caveman"
# ---------------------------------------------------------------------------
if [ -z "$PAIRS" ]; then
  if command -v claude >/dev/null 2>&1; then
    PAIRS="$(claude plugin list 2>/dev/null \
      | sed -n 's/^[^A-Za-z0-9_-]*\([A-Za-z0-9_-][A-Za-z0-9_-]*\)@.*/\1/p' \
      | while IFS= read -r name; do printf '%s \n' "$name"; done)"
  fi
fi

# Both sources failed -> silently emit nothing.
[ -z "$PAIRS" ] && exit 0

# ---------------------------------------------------------------------------
# 3. Filter to known companions; annotate mattpocock-skills with shipped skills
#    whose SKILL.md exists under the (newest) installPath.
# ---------------------------------------------------------------------------
has() { printf '%s\n' "$PAIRS" | cut -d' ' -f1 | grep -qx "$1"; }
pathof() { printf '%s\n' "$PAIRS" | awk -v n="$1" '$1 == n {print $2; exit}'; }

# Entries are newline-terminated (never space-separated), so annotations like
# "(wayfinder)" survive word-splitting on the newline-delimited list.
OUT=""

if has i-have-adhd;    then OUT="${OUT}i-have-adhd
"; fi
if has caveman;        then OUT="${OUT}caveman
"; fi
if has mattpocock-skills; then
  entry="mattpocock-skills"
  mp="$(pathof mattpocock-skills)"
  if [ -n "$mp" ]; then
    [ -f "$mp/skills/engineering/wayfinder/SKILL.md" ]  && entry="$entry (wayfinder)"
    [ -f "$mp/skills/productivity/handoff/SKILL.md" ]   && entry="$entry (handoff)"
  fi
  OUT="${OUT}${entry}
"
fi
# knoxville: a Node CLI + MCP server, NOT a Claude Code plugin, so it never
# appears in the plugin registry. Cheap reliable check: the known local clone.
if [ -f "$HOME/Documents/Projects/Knoxville/dist/cli.js" ]; then
  OUT="${OUT}knoxville
"
fi

LIST="$(printf '%s' "$OUT" | awk 'NF { printf "%s%s", (seen ? ", " : ""), $0; seen=1 }')"
[ -z "$LIST" ] && exit 0

LINE="explore companions: $LIST — boosts active per SKILL.md \"Companion plugins\""
if has i-have-adhd; then
  # SKILL.md sets disable-model-invocation: true — the model can never invoke it.
  # Activation is user-owned: /i-have-adhd per session, or the always-on flag
  # file ~/.claude/.i-have-adhd-always (read by the plugin's own SessionStart hook).
  LINE="$LINE; i-have-adhd present (user-invoked: /i-have-adhd, or always-on via ~/.claude/.i-have-adhd-always)."
fi
printf '%s\n' "$LINE"
exit 0
