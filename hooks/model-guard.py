#!/usr/bin/env python3
"""model-guard PreToolUse hook — block Fable-class / Haiku subagent dispatch.

Reads a Claude Code PreToolUse event on stdin and enforces the model-roster
doctrine from skills/explore/references/delegation.md:

  - non-Agent/non-Task tools pass through silently;
  - a Fable-class dispatch is blocked (exit 2) unless the brief carries the
    explicit operator override token MODEL_GUARD_OK;
  - Haiku is never staffed (delegation.md rule 8) — blocked, no override;
  - a discovery unit (Explore / general-purpose) with no model gets an
    allow-with-note nudging the orchestrator toward a roster lane or sonnet.

Fail-open by design: any internal error exits 0 silently so a broken guard can
never block work. No tracebacks are written to stderr.
"""

import json
import sys

FABLE_REASON = (
    "model-guard: Fable-class subagent blocked — worker-tier units go to roster "
    "lanes (references/delegation.md rule 1; scores in references/model-roster.md). "
    "If the operator explicitly approved, resend with MODEL_GUARD_OK in the prompt."
)

HAIKU_REASON = "model-guard: Haiku is never staffed (delegation.md rule 8)."

DISCOVERY_NOTE = (
    "model-guard note: discovery unit — prefer a roster lane or sonnet at low "
    "effort (delegation.md rule 1)."
)

DISCOVERY_TYPES = {"Explore", "general-purpose"}


def allow(system_message=None):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }
    }
    if system_message is not None:
        out["hookSpecificOutput"]["systemMessage"] = system_message
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


def block(reason):
    sys.stderr.write(reason)
    sys.exit(2)


def main():
    try:
        raw = sys.stdin.read()
        event = json.loads(raw)
    except Exception:
        sys.exit(0)

    try:
        tool_name = event.get("tool_name", "")
        if tool_name not in ("Agent", "Task"):
            sys.exit(0)

        tool_input = event.get("tool_input", {})
        if not isinstance(tool_input, dict):
            sys.exit(0)

        prompt = tool_input.get("prompt", "") or ""
        model = (tool_input.get("model", "") or "").lower()

        if "MODEL_GUARD_OK" in prompt:
            allow("model-guard: override accepted — record it in the run record.")

        if "fable" in model:
            block(FABLE_REASON)

        if "haiku" in model:
            block(HAIKU_REASON)

        if model == "":
            subagent_type = tool_input.get("subagent_type", "") or ""
            if subagent_type in DISCOVERY_TYPES:
                allow(DISCOVERY_NOTE)

        sys.exit(0)
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
