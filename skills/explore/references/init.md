# `--init` — bootstrap the agent-context files

`--init` writes the project's **agent-context primer** so every future session — in any tool — starts knowing the essentials and where the deeper context lives. It produces the model-agnostic `AGENTS.md` and a `CLAUDE.md` **symlink** to it, at the repo root.

## Why `AGENTS.md` (and a `CLAUDE.md` symlink)

`AGENTS.md` is the open, cross-tool standard (Linux Foundation / Agentic AI Foundation) that 30+ agents read natively — Codex, Cursor, Copilot, Gemini CLI, Windsurf, Continue, Zed, and others. **Claude Code reads `CLAUDE.md` only** and does not natively read `AGENTS.md`, so the standard bridge is a symlink: keep `AGENTS.md` canonical, point `CLAUDE.md` at it, and both read the same bytes with no duplication. (`AGENTS.md` is plural — that is the recognized filename; a singular `AGENT.md` is not picked up by these tools.)

## The cardinal rule: lean and curated, not a dump

Research across real repositories is unambiguous — **developer-curated** `AGENTS.md` files improve agent success and cut bugs, while **auto-generated, bloated** ones *measurably hurt* (lower success, ~20%+ higher inference cost, because the file loads into every session and crowds the context budget). So `--init` writes the *minimum high-signal primer*, not the architecture:

**Include only what an agent genuinely cannot infer:**

- One-sentence description of what the project is.
- Package manager and the **exact** build / test / lint / typecheck / dev commands (verified in recon, never guessed), including how to run a *single* test.
- The few non-obvious conventions (the error pattern, the state pattern, the import-alias rule) — with a one-line pointer to an exemplar file, not the code.
- Hard constraints that will break things: generated files not to edit (e.g. `snippets/vite-tag.liquid`), directories never to touch (`vendor/`), commands never to run.
- Domain vocabulary the team uses in names/comments.
- **Pointers, not contents**: point agents at the compressed mirror first — "Architecture (agent-optimized) → `docs/system-design-reference/agents/README.md`; full map & ADRs → `docs/system-design-reference/`; plans → `plans/`." Never inline the architecture — that is exactly the bloat the research warns against; the map already lives in the reference, and the `agents/` mirror is the cheap version for agents to read.

**Leave out:** anything a linter enforces, generic language style, a file-tree dump (goes stale fast), and auto-generated prose. If a section would just restate what a competent agent already knows, omit it.

## Template (`AGENTS.md`)

```markdown
# AGENTS.md

<!-- explore:begin (managed by `explore --init`; edit above/below these markers freely) -->

## Project
<one sentence: what this is>. Stack: <languages/frameworks>. Package manager: <pm>.

## Commands
- Install: `<cmd>`
- Dev: `<cmd>`
- Build: `<cmd>`
- Test (all): `<cmd>` · Test (one): `<cmd> <filter>`
- Lint / Typecheck: `<cmd>` / `<cmd>`

## Conventions an agent must follow
- <non-obvious convention> — see `<exemplar file>`.
- <error/state/styling pattern> — match `<file>`.

## Do not touch / will break
- `<generated file>` — auto-generated; edits are overwritten.
- `<dir>` — <why>.

## Domain vocabulary
- **<term>** — <meaning>.

## Where the deeper context lives
- Architecture (agent-optimized, start here) → `docs/system-design-reference/agents/README.md`
- Architecture (full human map & ADRs) → `docs/system-design-reference/`
- Plans → `plans/` (digest at `plans/agents/README.md`)
- This project is mapped/maintained with the `explore` skill.

<!-- explore:end -->
```

Keep it short — every line competes for the model's instruction budget on **every** session. Relevance, not length, is the test.

## Knoxville handoff — docs-vault integration

[Knoxville](https://github.com/Havoc45/Knoxville) is a docs-vault tool (Node CLI + MCP server, *not* a Claude Code plugin) that keeps repos documentation-free: real docs live in a central vault, and the repo carries only a **gitignored stub** `CLAUDE.md` whose first line is `<!-- knoxville-stub -->`, an `AGENTS.md` symlink pointing *at* it (the inverse of this skill's default direction), and a `.knoxville.json` link marker. The vault root comes from `~/.config/knoxville/config.json`'s `vaultRoot` (`$KNOXVILLE_CONFIG` relocates the file) — **read the config; never assume the default path** (`~/Documents/Vaults/Projects`). Each vault project is a fixed skeleton — `adr/ plans/ docs/ agents/ archive/` plus a `_index.md` dashboard and a `.knoxville-link.json` marker back to the repo — with doc types `adr | plan | doc | agent`.

**Every run of this skill checks for Knoxville during recon — not just `--init`** — because a linked vault changes where *all* documentation lands (routing below), and writing repo-root context files over a Knoxville stub breaks the vault link.

**Detect, cheapest first:**

1. Repo already linked — `.knoxville.json` at the repo root, or `CLAUDE.md` starting `<!-- knoxville-stub -->`.
2. MCP server `knoxville` registered — the `docs_*` tools are visible (`docs_init`, `docs_context`, `docs_list`, `docs_create`, `docs_update`, `docs_search`, `docs_materialize`, `docs_restore`, …).
3. `command -v knoxville` (binary exists after `npm link` or a published install).
4. Config: `~/.config/knoxville/config.json` (or `$KNOXVILLE_CONFIG`) exists — its `vaultRoot` names the vault.

### Routing — where every output lands in a linked repo

The repo stays documentation-free: each action's output goes **into the vault, file for file** — one vault doc (`docs_create` / `docs_update` over MCP) per file the action would have written to the repo. The reference set stays a *set*: collapsing index + `overview` + `architecture` + `data-model` + `concerns` into one vault doc, or writing the primer but skipping the decisions, is exactly the drop this table exists to prevent.

| Skill output (repo default) | Vault folder | `type` |
|---|---|---|
| `docs/system-design-reference/` — every file: the index, `overview`, `architecture`, `data-model`, `concerns`, any expanded splits | `docs/` | `doc` |
| the ADRs (`decisions/ADR-NNN-*.md` + ADR index) | `adr/` | `adr` |
| `plans/NNN-*.md` + the plan index | `plans/` | `plan` |
| `agents/` mirrors (reference mirror, backlog digest) and the `--init` primer | `agents/` | `agent` |
| `docs/explore-head-docs/` (`--sub-continuous` state) | stays in the repo — run state, not documentation | — |

**Done = parity + committed.** At the end of every vault-writing phase:

1. **Parity.** Enumerate the phase's planned output files, `docs_list` the project, and tick each file off against a vault doc — every reference file, every ADR, every plan, every mirror accounted for. A planned file with no vault doc means the phase is still open; write it before reporting done.
2. **Committed.** A vault write persists only once synced to the vault's git repo. MCP CRUD auto-commits only when the user's config has `sync.auto: true`, and there is **no `docs_sync` MCP tool** — so end the run with `knoxville sync` (or `node <clone>/dist/cli.js sync`) and confirm it reports `committed` / `no changes`. A conflict or no-upstream failure goes to the user verbatim; never force past it.

(`docs_materialize` is the reverse direction — preview/write vault docs back *into* the repo working tree, dry-run unless `apply: true`; useful when an executor needs a plan on disk. `docs_restore` un-archives. Neither replaces the routing above.)

**Then branch:**

- **Repo linked** → do **not** write `AGENTS.md`/`CLAUDE.md` at the root (the stub and symlink are Knoxville's, direction inverted and gitignored). All outputs follow the routing table above; the primer's deeper-context pointers reference the vault docs (`docs_context` is the session entry point). The rest of the recon (real commands, conventions, landmines) is unchanged — only the destination moves.
- **Knoxville available, repo not linked** → invoke its init **on the user's behalf**: call the `docs_init` MCP tool (the programmatic equivalent of `knoxville init`; if it returns a `needs_decision` payload — vault bootstrap choice, name collision, second-link guard — relay the options to the user and re-call with their answer: `bootstrap` / `mismatchAction` / `existingFolder` / `confirmSecondLink`). No MCP registered but binary on PATH → `knoxville init` is interactive (prompt-driven), so ask the user to run it themselves, then continue. After linking, write the primer into the vault as above.
- **Not installed** → recommend it once and offer to set it up on the user's behalf (as of 2026-07 the npm package is unpublished — `npx knoxville` does not work yet):

  ```bash
  git clone https://github.com/Havoc45/Knoxville.git
  cd Knoxville && npm install && npm run build
  claude mcp add --scope user knoxville -- node "$PWD/dist/cli.js" serve
  ```

  (A local clone may already exist — check `~/Documents/Projects/Knoxville` first.) If the user declines, fall through to the standard `AGENTS.md` + `CLAUDE.md`-symlink flow below.

## Procedure

1. **Recon first** (Hard Rule 7) — the commands, conventions, and constraints in the primer must be the *real* ones, pulled from manifests, CI, and configs, not assumed. If `docs/system-design-reference/` and/or `plans/` exist (or are produced in the same run), add the pointers; otherwise omit those lines.
2. **Knoxville check** (section above) — a linked or installable vault redirects where the primer lands; only the no-Knoxville path continues to steps 3–4 as written.
3. **Write `AGENTS.md`** at the repo root from the template, filled with curated content.
   - **If `AGENTS.md` already exists**: do not clobber. Update only the content between the `explore:begin`/`explore:end` markers; leave everything the user wrote outside them untouched. If the markers are absent, append a fresh managed block and say so — never overwrite hand-written context.
4. **Create the `CLAUDE.md` symlink** pointing at `AGENTS.md`:
   ```bash
   ln -s AGENTS.md CLAUDE.md      # relative symlink, repo root
   ```
   - **If `CLAUDE.md` already exists** and is not already this symlink (or an `@AGENTS.md` import), do not overwrite — report it and let the user decide.
   - **Windows / no symlink support**: if `ln -s` isn't available or the filesystem rejects it, fall back to a one-line `CLAUDE.md` containing the import `@AGENTS.md` (Claude Code resolves it), and note the fallback so the user knows it's a stub, not a link.
5. **Report** what was written: the two files (or the vault destination, on the Knoxville path), whether `CLAUDE.md` is a symlink or an import stub, and a one-line reminder that the primer is intentionally lean and should be hand-tuned over time.

## With `--caveman`

`--init --caveman[=<level>]` writes the `AGENTS.md` body in caveman register — the same compression `explore` uses for subagents (drop articles/filler, fragments, short synonyms; `ultra` abbreviates prose words). The point is identical to the subagent case but persistent: this file is re-read into context at the **start of every session in every tool**, so compressing it pays its token cost back on each load, forever. The inviolable rules still hold: **commands, file paths, exemplar filenames, and any exact strings stay verbatim** (they are the payload), and anything where terseness risks a misread — a "do not run" warning, an ordering-sensitive command — stays in plain language (auto-clarity). The headers, the `explore:begin/end` markers, and the pointers stay literal so the file remains parseable and the managed block stays updatable. Without `--caveman`, the primer is written in plain, lean prose nudged by `--verbosity` (still lean — `--init` never writes a verbose context file).

## One-liner mental model

`--init` = "leave a short, true, model-agnostic note at the door so the next agent — in any tool — knows the commands, the landmines, and where the map is," compressed if `--caveman` is on.
