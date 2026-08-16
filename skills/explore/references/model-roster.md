# Model roster — shipped defaults & per-model calibration

The score table and per-model behavioural notes behind `references/delegation.md` "The model roster & routing". The routing rules, lane mechanics, and the user-roster override live there; this file is only *which models, at what scores, with what observed habits*. A valid saved roster (`${XDG_CONFIG_HOME:-$HOME/.config}/explore/roster.json`) is authoritative over everything below — read the file, not this table, whenever it exists (`delegation.md` "User roster override"). A saved roster may also carry an optional **role profile** (`optimizations.omp_roles`): named `plan` / `slow` / `smol` roles that staffing resolves through instead of raw C/I/T (`delegation.md` "Role profile"). It is configured by the "Token optimization (OMP-style roles)" step of the `--setup-plugin` wizard (`setup.md`).

**Haiku is never staffed** — routing rule 8 in `delegation.md` binds regardless of what any table or saved roster says; do not add Haiku to a roster.

## Shipped defaults

Treat cost as *what the operator actually pays* (subscriptions, included limits), not list price; re-rank to your own billing, and re-score a model after a few real runs. Higher = better on every axis (cost higher = cheaper). Intelligence = how hard a problem the model takes unsupervised; taste = UI/UX, code quality, API design, copy.

| Model | Lane | Cost | Intelligence | Taste |
|---|---|---|---|---|
| gpt-5.6-sol | `codex` CLI | 9 | 8 | 8 |
| glm-5.2 xhigh | `opencode` CLI | 8 | 7 | 7 |
| sonnet-5 | native | 6 | 6 | 7 |
| opus-5 | native | 6 | 8 | 8 |
| fable-5 | native / the session itself | 2 | 9 | 9 |

*(gpt-5.6-sol — the codex lane's current default, superseding gpt-5.5 — and glm-5.2 are validated on real coding work: gpt-5.6-sol leads across most areas, and its included quota runs **~30× any Claude tier's** (Fable included) — treat it as effectively free, route coding volume there first, and commission it liberally for extra independent reviews. With taste now 8/7, the CLI lanes clear the user-facing bar (rule 6), not just the bulk lane. glm-5.2 sits slightly below gpt-5.6-sol — a notch lower on every axis — and is the standing coding fallback for **both** gpt-5.6-sol (lane absent/exhausted) and opus-5 (native quota worth preserving). The native-tier scores remain provisional — calibrated only against the 2026-07-04 three-executor bake-off (execution fidelity, not coding/design/debugging) — re-score them as real runs land. On a harness whose native models differ, substitute its own tiers at the same rungs. opus-5 replaced opus-4.8 in the native slot on 2026-07-27 — operator re-rank 6/8/8; first live run (plan-011 executor @ max) approved on first pass plus one review round.)*

## Per-model calibration

Observed profiles; fold the brief requirements in at dispatch:

- **gpt-5.6-sol** — strict literalist, best protocol fidelity: honors STOP conditions exactly, raises its hand with a precise diagnosis when the plan contradicts itself, never improvises. The cost is one extra round-trip whenever the plan holds a wrinkle a bolder model would resolve itself — budget for it. Best default where deviation must never be silent. Effectively free (quota note above): the default coding workhorse, the standing second-opinion reviewer, and the computer-use verification agent (`delegation-transports.md`). *(Profile observed on gpt-5.5; the taste-8 re-rank is operator-validated, the behavioural notes carry over until a 5.6-sol run contradicts them.)*
- **glm-5.2 xhigh** — the proven coding alternate: slightly below gpt-5.6-sol on capability, cheaper per token, and the model the codex lane fails over to. Best bounded judgment and accounting: self-adjudicates within scope and defends the reasoning openly in ASSUMPTIONS rather than stopping or going silent; also the best finder of adjacent issues. Weaknesses: verbose reports, slowest wall-clock, and a host-plugin junk risk — see **opencode lane quirks** in `delegation-transports.md`.
- **sonnet-5** — fastest, cheapest path to a correct result on well-specified mechanical work (one pass, byte-parity with an approved original). Weakness: **silent deviation** — applies pre-adjudicated amendments without surfacing them and leaves the thinnest deviation trail; on a plan where the amendment *hadn't* been adjudicated, that same silence is a REVISE. Its briefs restate the reporting contract explicitly: *record every deviation, however small*.

## Tried but unrostered

Models exercised on a real machine but not in the shipped defaults — record each with the scores it earned and why it isn't (or is no longer) staffed, so the next `--setup-plugin` run starts from evidence instead of zero:

| Model | Lane tried | Scores (C/I/T) | Status / why |
|---|---|---|---|
| gpt-5.6-sol (via `myprovider` gateway) | `opencode` | — (never calibrated there) | Attempted 2026-08-16; gateway returned capacity-limit unavailability on both transports (model-specific — sibling models fine). Dropped from the saved roster; re-add via a `--setup-plugin` re-run if the gateway recovers. The codex-lane row above is unaffected. |
| opus-4.8 | native | 6/8/8 (operator) | Superseded by opus-5 in the native slot 2026-07-27. |
| gpt-5.5 | `codex` | (profile basis for gpt-5.6-sol) | Superseded by gpt-5.6-sol as the codex-lane default; behavioural notes carried over. |

Add a row here whenever a new model is trialed and not (or no longer) rostered — score it even when the trial fails, and say why.
