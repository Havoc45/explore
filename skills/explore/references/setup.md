# First-run setup (`--setup-plugin`) — the wizard

`--setup-plugin` runs an interactive **wizard** that produces one artifact: a persisted **roster** — the host harness, the enabled dispatch lanes and their billing, the eligible models, and each model's Cost/Intelligence/Taste weights — written to a global config home outside every harness's plugin directory. Every later run loads that roster and treats it as **authoritative when it exists and validates**; the shipped defaults in `references/model-roster.md` apply when no valid roster file exists **or when a valid roster leaves no locally usable lane** ("Cross-harness loading" below).

**When it runs.** Only when the user passes `--setup-plugin`. It is a **standalone action** that **bypasses the phased workflow entirely** — no recon, no exploration, no vetting, no documentation or plan output; only the wizard runs. When `--setup-plugin` arrives alongside other action flags, run setup only, then end the run, telling the user in one line to re-invoke the other flags.

## Question mechanics

Asking a question is an **action**, not a tool name (SKILL.md "Platform adaptation") — map it onto the host:

- **A harness with a structured question tool** (Claude Code: `AskUserQuestion` — **max 4 options per question**, multi-select supported, the UI adds its own free-text "Other") → use it.
- **Anywhere else** → ask a plain-text numbered question and read the reply.

Rules that hold on both paths:

- **One decision per question.** A question that bundles two decisions gets split into two.
- **Overflow rule.** When a choice has more options than the tool can hold (more than 4 supplied options on Claude Code — the UI's own "Other" is added on top and never consumes a slot), either split it into consecutive questions with "more choices…" as the last option, or drop that one question to a plain-text numbered list. **Never silently truncate the option set** — the user must be able to reach every option.
- **Single-candidate rule** (the overflow rule's mirror). Structured question tools can require **at least 2 supplied options** (AskUserQuestion rejects a 1-option question outright — live-hit 2026-07-27). A choice with exactly one known-good candidate still gets a selector: pair the candidate with the second option **"choose a different id from the inventory shown above"** (free-text entry) — a real alternative action, never a padded or invented model id. Only when there is no inventory to choose from either is the choice stated as the taken path in the response and confirmed at the summary (Step 7).
- **Consent and cost are plain full sentences** (auto-clarity), on every harness, even where the surrounding prose is terse.
- **Render-before-ask.** Any list or table the user needs in order to answer — a lane's model inventory, the C/I/T table, the Step-7 summary — is rendered in the assistant's **own response text**, never left inside a raw tool result (harness UIs collapse those) and never only *referenced* ("see above"). **Harness reality (live-hit three rounds): response text sandwiched between tool calls in one turn may never be shown** — a render followed by a structured question call in the same turn loses the render. So a render and its question are split **across the turn boundary, never across a tool call**: the response **ends** with the render plus the inviting line — worded exactly: *reply with your picks directly, or reply anything (e.g. "ask") to open the selectors* — if the reply already carries the answer, accept it (fast path); otherwise open the **structured selector as the next turn's first action**, directly under the render in the transcript. **No exceptions — settled by experiment (2026-07-27, four live failures including a dedicated attempt on both the first and last gates): a selector called in the same turn as a render always loses the render**, wherever it sits in the turn. Auto-opening a selector under a visible render is impossible on this harness; the turn boundary is the only mechanism that guarantees the render displays. Every render-dependent question therefore uses the invite flow above, first and last included. Self-contained questions (billing, consent) use the structured tool directly. Plain-text numbered questions remain the no-structured-tool fallback.

## Wizard Step 1 — Detect

**State the host harness first.** You know which harness you are running in — name it (`claude-code`, `codex`, `opencode`, `pi`, …); do not probe for it.

Then probe the machine's lane inventory. Every probe is read-only and free:

| Target | Probe | Meaning |
|---|---|---|
| codex CLI | `command -v codex` + `test -f ~/.codex/config.toml` | binary + configured |
| opencode CLI | `command -v opencode` + `test -d ~/.config/opencode` | binary + configured |
| Claude Code | `command -v claude` + `test -d ~/.claude` | installed on this machine |
| Gemini CLI | `command -v gemini` | binary present |
| Copilot CLI | `command -v copilot` | binary present |
| Factory Droid | `command -v droid` | binary present |
| Pi | `command -v pi` | binary present |
| Cline / Cursor / anything else | no verified probe — **ask the user** | unknown |

Hard Rule 5's honesty discipline binds here: a target with no verified probe is reported **unknown — tell me**, never guessed and never inferred from an unrelated marker.

**Completion criterion:** a detection table in which **every row reads found / absent / unknown**, rendered as the turn's final response text with the inviting line — *reply with mode and lanes directly, or reply anything (e.g. "ask") to open the selectors*; the mode + lanes selectors open on the reply.

## Wizard Step 2 — Mode

One question:

- **native-only** — this harness's own models; no CLI lanes.
- **multi-lane** — other installed CLIs/harnesses also serve as dispatch lanes.

**The host lane is always enabled in either mode.** native-only skips Step 3's *lane-selection* question (the roster then holds only the host lane); it does **not** skip Step 3's billing question.

**Completion criterion:** the mode is recorded.

## Wizard Step 3 — Lanes + billing

**Lanes (multi-lane only).** Multi-select the additional lanes from the *detected* set, **excluding the host harness itself** — on Claude Code offer codex / opencode / pi / …; on Codex offer claude / opencode / … — plus an option to name a lane the probes did not detect. Apply the overflow rule when the detected set exceeds the tool's option limit.

**Billing (both modes, every enabled lane, host lane included).** One question per lane:

- **subscription / included quota** — usage already paid for by a plan.
- **API pay-per-token** — usage billed per call.

Record every answer. Billing feeds two things: the Cost axis (`references/roster-calibration.md`) and the `--sub-continuous` credits guard, which must never silently drain a paid-credit lane (`references/sub-continuous.md`).

**Completion criterion:** every enabled lane, host included, has a recorded billing value.

## Wizard Step 4 — Token optimization (OMP-style roles)

An optional optimization profile that pins three **roles** onto the roster the wizard is building — a `plan` model for architectural planning, a `slow` model for thorough analysis, and a `smol` model for cheap mechanical execution, with two dispatch doctrines (`prewalk`, `plan-yolo`) on top — ported from OMP's role-based model routing (OMP v17.3.4). It changes only which *saved* model each rung resolves to by default; every routing rule, floor, and the escalation ladder in `references/delegation.md` bind unchanged.

One self-contained consent question opens the step — **enable the optimization profile, or skip it** (self-contained, so the structured tool is used directly, no render needed):

- **skip** — record nothing; the step is over and the roster saves exactly as it would have without this step. The default.
- **enable** — ask the three questions below, then write the `optimizations` block at save time ("Persistence" below).

**Re-run prefill (this step's one exception to the generic rule).** When the existing roster already carries `optimizations.omp_roles`, this step's question does **not** default to the saved answers. Its text shows *"optimization profile applied on `<applied_at>` — re-apply?"* with **re-apply** / **leave as-is** / **remove**; **leave as-is** is the default, and the wizard **never silently re-applies**. Only an explicit re-apply refreshes `applied_at` and the answers.

**1. The role mapping** (enable path only). Three independent decisions — **one per question, per the one-decision rule** — each offered as a selector over the lane/model inventory already detected and recorded in Steps 1–3, applied to the shipped defaults (the wizard renders that mapping as response text before asking):

- **`plan` →** the **highest-Intelligence enabled model** — breaks a tie on the higher Taste, then the higher Cost.
- **`slow` →** the same model as `plan`, or the **next tier down** — the user's pick.
- **`smol` →** the **cheapest enabled lane model** — the highest-Cost row across the enabled lanes. **Never Haiku — that floor is hard**, no matter what the operator's inventory holds (`references/delegation.md` routing rule 8 binds here exactly as it binds staffing).

Where the mapping leaves a single candidate, the single-candidate rule applies ("Question mechanics"); never pad a selector with invented ids.

**2. `prewalk`** (enable path only). One consent question, in plain full sentences: with `prewalk` on, plans are **authored at the `plan`-role tier** and executors **default to the `smol`-role tier** unless the plan is taste-sensitive — the expensive model plans, the cheap model executes.

**3. `plan-yolo`** (enable path only). One consent question, in plain full sentences: on `--plan-once`, **and only with explicit per-run consent at that run**, the harness auto-approves the plan the moment the planning model resolves it and auto-dispatches the `smol`-role executor. Enabling the toggle here only *permits* that per-run consent to be asked; it never grants it in advance.

**Completion criterion:** the step is recorded as skipped, or three role answers (a lane + dispatchable model id each) plus the two boolean toggles are recorded, carrying the user's explicit enable consent.

## Wizard Step 5 — Models per lane

Take the inventory for each enabled lane with **verified commands only**:

| Lane | Inventory | Verified note |
|---|---|---|
| Claude Code native | static aliases `sonnet` / `opus` / `fable` | offer the non-Haiku aliases; add `haiku` only when the user names it — `references/delegation.md` routing rule 8 stays the standing default |
| codex | **no inventory subcommand** (verified on codex-cli 0.145.0) — read the `model` key from `~/.codex/config.toml` for the lane's configured default, and offer it alongside the known-good codex-lane ids in the shipped roster | never invent model ids |
| opencode | `opencode models` — hundreds of ids (346 on opencode 1.18.6). **No verified command reads opencode's configured default; do not claim one.** | the long-list case below |
| any other / unknown | ask the user to paste their model list | — |

**Render one model tree for all enabled lanes, then ask across the turn boundary.** One response ends with the tree — one branch per enabled lane, its available models as leaves: the native lane's aliases; codex's known-good set (the `model` key just read from `~/.codex/config.toml` plus the shipped-roster codex ids — there is no inventory subcommand to list more); opencode's inventory per the long-list rule below — plus the inviting line — *reply with your picks per lane directly, or reply anything (e.g. "ask") to open the selectors*. A reply carrying picks is accepted directly; otherwise the next turn opens **one multi-select selector per lane as its first action** (defaults marked, "add a different id" as the free-text arm), sitting directly under the tree in the transcript. Never a tool call between the tree and the ask.

**Every lane's selection is a set** — multi-valued on every lane, not just the native one; a lane with one known-good entry still shows it as a marked default the user can keep, replace, or extend with any id from the tree. The selection never silently collapses into a statement.

**The long-list rule** — a generic mechanism; opencode is today's instance. When an inventory exceeds ~8 entries:

1. Show the list as plain response text first — **the full list when it has ≤40 entries; otherwise the first 40, the total count, and the exact command the user can run to see the rest**.
2. Then ask a question whose options are **up to 3 best-known defaults for that lane**: the lane's *verified* configured default first where one exists (codex only, today), then that lane's models from the shipped roster. Offer fewer than 3 when fewer exist — **never pad with guesses**.
3. Add free text: "type any further model ids, comma-separated".

The chosen set per lane is that lane's **roster candidates**. Record each candidate by its **dispatchable id** — the exact string the lane accepts (`openrouter/z-ai/glm-5.2`, a `~/.codex/config.toml` model id, a native alias) — not a display name.

**Completion criterion:** every enabled lane has at least one candidate recorded by dispatchable id.

## Wizard Step 6 — C/I/T values

One question, three paths.

**defaults** — score each candidate from the shipped table in `references/model-roster.md`, read there at run time.

- **Alias mapping rule:** match candidates to shipped rows **by model family, not string equality** — the shipped rows are display names (`fable-5`, `glm-5.2 xhigh`) while candidates are dispatchable ids (`fable`, `openrouter/z-ai/glm-5.2`). When a mapping is ambiguous, **ask the user** rather than guess.
- An unmatched candidate gets **all three axes `null`** and provenance `unscored`, with a one-line warning that routing staffs unscored models conservatively — worker rung only, never user-facing work.

**manual** — the user supplies the values. Render the candidate list, then read back one `model: C/I/T` line per candidate for confirmation.

**calibrate** — **read `references/roster-calibration.md` before offering calibration**, then run the protocol there. **Consent gate first, in plain sentences:** state that calibration dispatches real prompts to the chosen models, spends their quota or credits (including one ~1-token Claude API call when the quota probe runs) and takes minutes; give a per-model estimate; proceed only on an explicit yes. Calibration is offered **only for lanes with verified dispatch shapes** — codex, opencode, and the host's native models; every other lane takes the defaults or manual path.

After any path: one response ends with the rendered table — **model / lane / C / I / T / provenance**, with `null` axes rendered `—` — plus the inviting line — *reply with adjustments directly (e.g. "opus cost 7"), or reply anything (e.g. "ask") to open the selector*. A reply carrying adjustments is applied directly; any other reply opens the **confirm / adjust** selector as the next turn's first action, under the table in the transcript. Adjust loops **per value**, not per wizard, re-rendering the table after each change.

**Completion criterion:** every candidate carries three axis values (integer or `null`) plus a provenance, and the user has confirmed the table.

## Wizard Step 7 — Summary, confirm, persist

One response ends with the full setup rendered — host, mode, lanes with billing, the complete roster table with provenance, and the config path that will be written — plus the inviting line: *reply save / redo <step> / discard directly, or reply anything (e.g. "ask") to open the selector*. The selector opens on a non-answer reply, sitting under the render; the user decides against the roster they can actually see.

- **save** — persist per "Persistence" below, then confirm the written path back to the user in one line.
- **redo** — the user names the step to jump back to. Steps are re-runnable in place; any later answer that depended on the redone step is re-asked.
- **discard** — delete the staging directory; the config home is left untouched.

**Nothing is written to the config home before "save".** Calibration transcripts and every other run artifact are staged in a scratch/temp directory during the wizard and moved in at save time.

**Completion criterion:** either the written config path is confirmed back to the user, or the staging directory is deleted and the config home is unchanged.

## Persistence

**Config home:** `${XDG_CONFIG_HOME:-$HOME/.config}/explore/` (`~/.config/explore/` by default). It sits deliberately **outside every harness's plugin directory**, because plugin installs are version-suffixed and wiped on update, and because one roster must serve every harness on the machine. It is machine-global **user config**: never routed to a Knoxville vault, never written into any repo. Writes here are sanctioned by Hard Rule 1 in `--setup-plugin` mode.

**File:** `roster.json`, schema v1. Example — **synthetic values**; the shipped scores live only in `references/delegation.md`:

```json
{
  "schema": 1,
  "created": "<ISO-8601 timestamp>",
  "host": "claude-code",
  "mode": "multi-lane",
  "lanes": [
    { "id": "codex", "billing": "subscription" },
    { "id": "opencode", "billing": "api" },
    { "id": "claude-code", "billing": "subscription" }
  ],
  "roster": [
    { "model": "<dispatchable-id>", "display": "<shipped-row name, when mapped>", "lane": "codex", "cost": 5, "intelligence": 5, "taste": 5, "provenance": "default" },
    { "model": "<dispatchable-id>", "lane": "claude-code", "cost": null, "intelligence": 5, "taste": 5, "provenance": "calibrated" }
  ]
}
```

**Field types.** `cost`, `intelligence`, and `taste` are each an **integer 1–10 or `null`**. `null` means that axis is unscored — an unmatched default, or a failed calibration probe. A model with any `null` axis is **staffed conservatively — worker rung only, never user-facing work** — until the user fills it in (a manual edit, or a `--setup-plugin` re-run). `provenance` is one of `default` | `manual` | `calibrated` | `unscored`, per row: `unscored` when all three axes are `null`, otherwise the path that produced the values.

**The `optimizations` key is OPTIONAL — the schema stays v1.** Written only when the user explicitly enables the profile in Step 4, it is one additive top-level key beside `roster`:

```json
"optimizations": {
  "omp_roles": {
    "applied_at": "<ISO-8601 timestamp>",
    "roles": { "plan": "<model>", "slow": "<model>", "smol": "<model>" },
    "prewalk": true,
    "plan_yolo": false
  }
}
```

Each role value is a **dispatchable model id from the roster just saved**, resolving to its lane + model at run time (`references/delegation.md` "Role profile"). **Readers must ignore unknown keys, this one included**: a reader that pre-dates the profile treats the file as an ordinary v1 roster, and a roster without `optimizations` is unchanged-valid — nothing about loading, validation, or cross-harness fallback differs. `applied_at` is what Step 4's re-run prefill shows ("optimization profile applied on `<applied_at>` — re-apply?").

**Lane ids are harness-qualified** — `claude-code`, `codex`, `opencode`, `pi`, … — never a bare `native`. At load time the lane whose `id` equals the current host dispatches natively; other lanes dispatch through their CLI when it is present; a lane whose CLI is absent on this machine is skipped with a one-line note.

**Cross-harness loading.** `host` records which harness ran the wizard; the file serves every harness. A harness loading a roster it did not write resolves lanes by id per the rule above. If that leaves **no usable lane** — e.g. a native-only roster written on a different harness, whose id matches nothing local — fall back to the shipped defaults for the run, say so in one line, and suggest re-running `--setup-plugin` here.

**A saved, schema-valid roster is authoritative.** It defines the enabled lanes and the eligible models; deliberately unselected lanes and models do not creep back in. The shipped `delegation.md` table applies when no valid roster file exists **or when a valid roster leaves no locally usable lane** ("Cross-harness loading" above). A file that exists but **fails validation** — unparseable, wrong types, or an unknown `schema` at or below the current version — is **treated as absent for the run**: note it in one line and suggest `--setup-plugin`, which offers the backup-and-redo below.

**Write safety.**

- Write **atomically**: a temp file in the same directory, then rename.
- Before overwriting a malformed or unreadable existing file, back it up beside itself under a collision-proof name — `roster.json.bak-<UTC timestamp>`, e.g. `roster.json.bak-20260727T120000Z`.
- A `schema` **greater** than this reference's known version → **do not rewrite the file**; tell the user to re-run setup on the newer plugin.
- **Unknown keys are preserved on rewrite.**

**Re-run prefill.** When a valid roster already exists, every wizard question defaults to the saved answer — with one deliberate exception: Step 4's optimization-profile question shows the applied-on date and asks *re-apply?* rather than silently re-applying (Step 4).

**Calibration transcripts** land beside the roster under `calibration/` (see `references/roster-calibration.md`), moved in from the staging directory at save time.
