#!/usr/bin/env bash
if [ "${HERDR_ENV:-}" != "1" ]; then
  exit 0
fi
printf '%s\n' "herdr detected (workspace ${HERDR_WORKSPACE_ID:-?}, pane ${HERDR_PANE_ID:-?}): pane-agent delegation available — read skills/explore/references/delegation.md \"herdr transport\" before dispatching."
