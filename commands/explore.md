---
description: "Explore, understand, and improve a codebase (read-only). Charts a system design reference by default; flags add audit/plan, execution, security, and budget-aware modes."
argument-hint: "[--depth=standard|quick|deep] [--focus=area] [--improve] [--security] [--plan-once \"desc\"] [--review=file] [--execute-level=auto|low|medium|high|max plan] [--reconcile] [--init] [--plan-list|--ls] [--issues] [--sub-continuous] [--reference=path] [--code-mode=no] [--branch=name] [--bypass-pr-create=yes] [--verbosity=low|medium|high] [--caveman=ultra] [--model=...]"
---

Read and follow the `explore` skill at `${CLAUDE_PLUGIN_ROOT}/skills/explore/SKILL.md`, then run it on this codebase.

Invocation: `$ARGUMENTS`

Parse the arguments as feature flags per the skill's **command surface** section — the single source of truth for every flag, its default, and how flags compose. A trailing quoted `"<description>"` feeds `--plan-once`, or augments `--improve` with a described-task plan in addition to the audit plans.

Read the matching file under `${CLAUDE_PLUGIN_ROOT}/skills/explore/references/` before producing each kind of output, and honor every Hard Rule without exception — strictly read-only on source code; writes only to the paths the skill owns.
