<!--
  Vendored & adapted from the `improve` skill (https://github.com/shadcn/improve),
  MIT © shadcn. Reused here under MIT. See ../../../NOTICE.
  Adaptation: plan output directory is `plans/` at the repo root (not `docs/plans/`).
-->

> **How `explore` uses this.** This is the output spec for plans written by the
> `--improve`, `--plan-once`, and `--security` actions — the analogue of
> `system-design-reference.md` for the planning side. Plans live in
> **`plans/`** at the repo root. The prose density of a plan follows
> `--verbosity` (terse → descriptive), but the *evidence, exact paths, commands,
> and done-criteria are never trimmed* regardless of verbosity — an executor
> needs them in full. When `--improve` runs after exploration, ground each plan
> in the relevant ADR from `docs/system-design-reference/` (cite it in "Why this
> matters").
>
> **A plan is where the execution principles (SKILL.md) are pre-loaded.** The
> "Scope / out of scope" section draws the boundary principle 3 holds; the
> out-of-scope list is also where you forbid weakening existing behaviour
> (principle 2 — e.g. "do not remove the existing validation to simplify");
> "STOP conditions" are how principle 1(a) costly-to-reverse uncertainty halts
> the executor instead of guessing; and any cheap-to-reverse interpretation the
> plan makes is stated as a recorded assumption. Write the plan so a zero-context
> executor following it cannot help but obey those principles.

---

# Handoff Plan Template

Every plan is written for an executor model that has **zero context**: it has not seen the advisor session, the audit, the other plans, or any prior conversation. It may be a smaller/cheaper model. Assume it is competent at following explicit instructions and weak at filling gaps, recovering from ambiguity, or knowing when to stop.

Three properties make a plan executable by a weaker model:

1. **Self-contained context** — everything needed is in the file: paths, code excerpts, conventions, commands.
2. **Verification gates** — every step ends with a command and its expected result. The executor never has to *judge* whether it succeeded.
3. **Hard boundaries and escape hatches** — explicit out-of-scope list, and "STOP and report" conditions instead of letting the model improvise when reality doesn't match the plan.

File naming: `plans/NNN-short-slug.md`, numbered in recommended execution order.

---

## Template

```markdown
# Plan NNN: <Imperative title — what will be true after this plan>

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**: `git diff --stat <planned-at SHA>..HEAD -- <in-scope paths>`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1 | P2 | P3
- **Effort**: S | M | L
- **Risk**: LOW | MED | HIGH
- **Depends on**: plans/NNN-*.md (or "none")
- **Category**: bug | security | perf | tests | tech-debt | migration | dx | docs | direction
- **Planned at**: commit `<short SHA>`, <YYYY-MM-DD>
- **Issue**: <GitHub issue URL — only when published via `--issues`; omit otherwise>

## Why this matters

2–5 sentences. The problem, its concrete cost, and what improves when this
lands. Written so the executor (and a human reviewer) understands the intent —
intent is what lets a correct judgment call happen when a detail is off.

## Current state

The facts the executor needs, inlined — never "as discussed" or "see audit":

- The relevant files, each with one line on its role:
  - `src/orders/api.ts` — order-list endpoint; contains the N+1 (lines 130–160)
- Excerpts of the code as it exists today (short, with `file:line` markers),
  enough that the executor can confirm it's looking at the right thing.
- The repo conventions that apply here, with a pointer to one exemplar file:
  "Error handling follows the Result pattern — see `src/lib/result.ts` and its
  use in `src/users/api.ts:40-60`. Match it."
- Any documented vocabulary or design constraints the plan must honor, inlined
  from the intent/design docs found in recon: the relevant `CONTEXT.md` terms
  the executor should use in names and comments, the `DESIGN.md` tokens/components
  to reuse, or the ADR whose decision this work must stay consistent with. Quote
  the specific lines — the executor has not read those docs.

## Commands you will need

| Purpose   | Command                  | Expected on success |
|-----------|--------------------------|---------------------|
| Install   | `pnpm install`           | exit 0              |
| Typecheck | `pnpm typecheck`         | exit 0, no errors   |
| Tests     | `pnpm test -- <filter>`  | all pass            |
| Lint      | `pnpm lint`              | exit 0              |

(Exact commands from this repo — verified during recon, not guessed.)

## Suggested executor toolkit

(Optional — include only when relevant skills/tools plausibly exist in the
executor's environment. Skip the section otherwise.)

- Skills the executor should invoke if available, and for what:
  "use `vercel-react-best-practices` when writing the memoization in step 3".
- Reference docs worth reading before starting, by path or URL.

## Scope

**In scope** (the only files you should modify):
- `src/orders/api.ts`
- `src/orders/api.test.ts` (create)

**Out of scope** (do NOT touch, even though they look related):
- `src/orders/legacy-api.ts` — deprecated path, scheduled for deletion;
  changing it wastes effort and risks the v1 clients still pinned to it.
- Any change to the public response shape — clients depend on it.

## Git workflow

(Filled from recon — match the repo's observed conventions.)

- Branch: `advisor/NNN-<slug>` (or the repo's branch-naming convention if one is evident)
- Commit per step or per logical unit; message style: <match repo, e.g. conventional commits — include an example from `git log`>
- Do NOT push or open a PR unless the operator instructed it.

## Steps

### Step 1: <imperative title>

What to do, precisely. Reference exact files/symbols. Include the target code
shape when it's load-bearing (the pattern to produce, not necessarily every
line).

**Verify**: `<command>` → <expected output>

### Step 2: ...

(Each step small enough to verify independently. Order steps so the codebase
is never broken between steps when possible — e.g. add new path, switch
callers, then remove old path.)

## Test plan

- New tests to write, in which file, covering which cases (list them:
  happy path, the specific bug/regression this plan fixes, named edge cases).
- Which existing test to use as the structural pattern:
  "model after `src/users/api.test.ts`".
- Verification: `<test command>` → all pass, including N new tests.

## Done criteria

Machine-checkable. ALL must hold:

- [ ] `pnpm typecheck` exits 0
- [ ] `pnpm test` exits 0; new tests for <X> exist and pass
- [ ] `grep -rn "<old pattern>" src/` returns no matches
- [ ] No files outside the in-scope list are modified (`git status`)
- [ ] `plans/README.md` status row updated

## STOP conditions

Stop and report back (do not improvise) if:

- The code at the locations in "Current state" doesn't match the excerpts
  (the codebase has drifted since this plan was written).
- A step's verification fails twice after a reasonable fix attempt.
- The fix appears to require touching an out-of-scope file.
- You discover the assumption "<key assumption>" is false.

## Maintenance notes

For the human/agent who owns this code after the change lands:

- What future changes will interact with this (e.g. "if pagination is added
  to this endpoint, the batching in step 2 must be revisited").
- What a reviewer should scrutinize in the PR.
- Any follow-up explicitly deferred out of this plan (and why).
```

---

## Index file: `plans/README.md`

Written once by the advisor after all plans, updated by executors:

```markdown
# Implementation Plans

Generated by the improve skill on <date>. Execute in the order below unless
dependencies say otherwise. Each executor: read the plan fully before starting,
honor its STOP conditions, and update your row when done.

## Execution order & status

| Plan | Title | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| 001  | ...   | P1       | S      | —          | TODO   |
| 002  | ...   | P1       | M      | 001        | TODO   |

Status values: TODO | IN PROGRESS | DONE | BLOCKED (with one-line reason) | REJECTED (with one-line rationale — finding fixed independently or approach abandoned)

## Dependency notes

- 002 requires 001 because <reason>.

## Findings considered and rejected

- <finding>: not worth doing because <one line>. (So nobody re-audits it.)
```

## Quality bar — check before finishing each plan

- Could a model that has never seen this repo execute this with only the plan file and the repo? If any step requires knowledge from the advisor session, inline that knowledge.
- Is every verification a command with an expected result, not a judgment ("make sure it works")?
- Does every step name exact files and symbols, not "the relevant module"?
- Are the STOP conditions specific to this plan's actual risks, not boilerplate?
- Would a reviewer reading only "Why this matters" + "Done criteria" understand what they're approving?
- No secret values anywhere in the file — locations and credential types only.
- "Planned at" SHA is filled in and the in-scope paths in the drift check match the Scope section.

---

## The backlog index — `plans/README.md`

The human-facing index. However you present the findings, include a **status table** whose columns are a superset of `--plan-list`'s so that flag (and any reader) gets everything at a glance:

```
| #   | Description                         | Severity | Priority | Effort | Depends on | Status |
|-----|-------------------------------------|----------|----------|--------|------------|--------|
| 001 | Add a typecheck script (type gate)  | — (dx)   | P2       | S      | —          | TODO   |
| 002 | Align the Node version contract     | MED      | P2       | S      | —          | TODO   |
```

- **#** is the plan number; **Description** is the plan title in a few words; **Severity** is the severity of the finding/risk the plan addresses (`HIGH`/`MED`/`LOW`, or `—` plus the category for non-risk work like `dx`); **Priority** is the plan's `P0`–`P3`; **Status** is `TODO`/`IN PROGRESS`/`DONE`/`BLOCKED (reason)`/`REJECTED (rationale)`. Effort and Depends-on are extra columns that help sequencing.
- This table is the single source of truth for plan status. When an executor finishes (or `--reconcile` runs), the Status cell here is what changes — keep it and the compressed `plans/agents/README.md` digest in sync so `--plan-list` is correct from either.

---

## The `agents/` digest — `plans/agents/README.md`

Alongside the human backlog index (`plans/README.md`), write a compressed `plans/agents/README.md` for an orchestrator to triage the backlog cheaply. Lead with a status table whose columns match `--plan-list` — **`# · description · severity · priority · status`** — so `--ls` can fill its table from this one small file; follow it, if useful, with the per-plan in-scope paths and dependencies. All in caveman register. It mirrors the index's status table, not the plan bodies.

**The full plan files are never compressed.** A plan is written for the weakest plausible executor, and its precision *is* its body — the inlined excerpts, the ordered steps, the verification commands, the done criteria. An executor always reads the full `plans/NNN-*.md`; the `agents/` digest is only a navigational layer over the backlog, regenerated whenever plans are added or `--reconcile` runs. (This is why the `agents/` mirror compresses the *reference and the index*, never the executable instructions.)
