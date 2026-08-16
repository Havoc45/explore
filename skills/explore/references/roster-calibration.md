# Roster calibration — probing C/I/T for the user's own models

Reached from `references/setup.md` Wizard Step 6, the **calibrate** path, and only after its consent gate.

## What calibration is

A short, consent-gated **probe** run that *suggests* Cost/Intelligence/Taste values for the models the user chose. The suggestions are advisory, never verdicts — the user confirms every value back in `setup.md` Step 6 before anything is saved.

**Supported lanes only:** codex, opencode, and the host's own native dispatch. A lane with no verified dispatch shape cannot be probed; its models take the **defaults** or **manual** path in `setup.md` instead.

**Dispatch invocations are cited by pointer, never invented.** Use the verified shapes for the model's lane in `references/delegation.md` — "Shell command shapes" for the shell transport, "MCP call shapes" for MCP. A lane whose shape is not written there is not calibratable.

## The axes, honestly

### Cost — computed, not benchmarked

Deterministic, in three moves:

1. **Base from the lane's billing answer** (`setup.md` Step 3): subscription / included quota → **7**; API pay-per-token → **4**.
2. **Headroom adjustment**, for a lane that supports the live read. Run it read-only — no `--allow-refresh`:

   ```bash
   python3 skills/explore/scripts/usage_probe.py --provider both
   ```

   It covers the claude and codex lanes today; the Claude read spends one ~1-token API call, so count it in the consent estimate. The probe reports percent **used** (0–100), so the lane's remaining-quota fraction is `r = 1 − pct/100`:

   | `r` (remaining) | Adjustment |
   |---|---|
   | `r ≥ 0.6` | +2 |
   | `0.3 ≤ r < 0.6` | +1 |
   | `0.1 ≤ r < 0.3` | +0 |
   | `r < 0.1` | −1 |

   A lane the probe does not support, or a probe that fails → **+0**.
3. **Clamp to [1, 10].**

Cost is relative to *what this operator actually pays* — the same definition `delegation.md` gives the shipped table, so mixed rosters stay comparable.

### Intelligence — probed

**2 bounded reasoning probes per model**, each with a machine-checkable answer, dispatched through the model's own lane at **medium** effort.

**Probe authorship rule.** The session model writes the probes **fresh each run**, and **writes the answer key before dispatching anything** — a probe whose answer the author cannot state in advance is not sent. (Fixed shipped probe sets were considered and rejected: they go stale and leak into training data, which hollows out the signal.)

Probe shapes: one **multi-step constraint puzzle**, and one **small code-comprehension task with exactly one right answer**.

Mapping, deterministic:

| Correct | Score |
|---|---|
| 2 of 2 | 8 |
| 1 of 2 | 6 |
| 0 of 2 | 4 |

The session model may then adjust **±1 for solution quality** — shown reasoning, not just the answer — stating why.

A probe that errors, stalls, or runs past **5 minutes** (inside the lane doctrine's 10-minute watch) leaves **that axis `null`**, never a guessed number.

### Taste — probed

**1 small design probe per model** — name and shape a tiny API, or a small set of error messages — scored 1–10 by the session model against a short rubric on naming, shape, and copy quality.

The rubric is **anchored to the shipped roster by pointer**. Its anchors are `fable-5` (high), `gpt-5.6-sol` (upper-middle), and `glm-5.2 xhigh` (middle), and the judge **reads their current scores from `references/model-roster.md` at run time** — the numbers are never copied into this file. Say which anchor the result sits nearest, and why.

A failed, stalled, or over-cap probe leaves the axis `null`, by the same rule as above.

## Scale + normalization

All three axes run **1–10, higher = better** (cost higher = cheaper), anchored to the shipped table so a roster mixing `default` and `calibrated` rows stays comparable. What a `null` axis means, and how such a model is staffed, is defined once — in `setup.md` "Persistence"; read it there.

## Consent + budget

State the following in plain full sentences before anything is dispatched, and proceed **only on an explicit yes**:

- Calibration **dispatches real prompts to the user's own models** and spends their quota or credits.
- **Per model: about 3 dispatches** — 2 intelligence probes and 1 taste probe — and minutes of wall-clock.
- When the quota probe runs, it adds **one ~1-token Claude API call**.
- Show the **per-model estimate and the total** before the yes/no question.

The lane doctrine binds every probe dispatch: label it with its **true model and effort** (`delegation.md` "Model labeling"), close stdin with `</dev/null` on codex shell runs, and hold the 10-minute watch.

## Output

Per model: the suggested values — any failed axis as `null` — with provenance `calibrated`.

**Transcripts**, one per probe, are written **first to the wizard's staging directory** (`setup.md` Step 7 — nothing touches the config home before save), then moved on save to:

```
${XDG_CONFIG_HOME:-$HOME/.config}/explore/calibration/<model-slug>-<UTC timestamp>.md
```

`<model-slug>` is the dispatchable id lowercased with every character outside `[a-z0-9.-]` replaced by `-`; the UTC timestamp (e.g. `20260727T120000Z`) keeps same-day re-runs collision-proof.

**The honesty line, said to the user:** three probes are a **coarse signal**. The user's own re-ranking after real runs — which `delegation.md` already mandates — outranks anything measured here.
