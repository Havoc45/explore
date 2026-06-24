<!--
  The convention described here follows the `caveman` skill
  (https://github.com/JuliusBrussee/caveman), MIT © Julius Brussee.
  Described in explore's own words and adapted to subagent communication;
  see ../../../NOTICE for attribution.
-->

# Caveman mode — compress the talk, not the truth

`--caveman` applies the **caveman** convention — "why use many token when few do trick" — to the *internal* communication of an exploration: subagent prompts, the findings subagents send back, and the head-doc / blackboard scratch in `sub-continuous` mode. It cuts roughly three-quarters of the tokens spent on that traffic by dropping fluff while keeping every piece of technical substance, so a fixed budget buys more exploration and subagents stay sharp instead of drowning in prose.

**It does not touch the human deliverable.** The ADRs in `docs/system-design-reference/` and the plans in `plans/` are written at `--verbosity` for people, in full. Caveman governs the *cheap, ephemeral channel between agents*; verbosity governs the *durable channel to humans*. That split is the whole point: spend tokens where a human reads, save them where only an agent reads.

## Levels (`--caveman=<level>`, default `full` when bare)

| Level | What changes |
|---|---|
| `lite` | Drop filler, hedging, and pleasantries. Keep articles and full sentences. Professional but tight. |
| `full` *(default)* | Drop articles; fragments OK; short synonyms (big not extensive, fix not "implement a solution for"). No tool-call narration, no decorative tables/emoji, no dumping long raw logs. Classic caveman. |
| `ultra` | Also abbreviate **prose** words (DB, auth, config, req/res, fn, impl), strip conjunctions, use arrows for causality (`X → Y`), one word when one word will do. |
| `wenyan-lite` / `wenyan-full` / `wenyan-ultra` | Classical-Chinese register for maximum character reduction; only when the operator asks for it. |

The example `--caveman=ultra` means subagents report in the most compressed prose register while exploring.

## Inviolable rules (these override compression)

1. **Evidence stays verbatim.** `file:line` references, symbol names, function/API names, CLI commands, config keys, and exact error strings are **never** abbreviated or paraphrased — they are the payload. Caveman shortens the *connective prose around* the evidence, never the evidence. (This is why caveman composes cleanly with the evidence rule: both insist the citable facts stay exact.)
2. **Preserve the operator's language.** Compress the *style*, not the language — if the working language is Portuguese, subagents grunt Portuguese. Code, commands, and errors stay as-is.
3. **Auto-clarity — drop caveman where terseness is dangerous.** Write in plain, full language for: security findings and their handling, irreversible-action notes, any multi-step sequence where dropped conjunctions could be misread (e.g. "migrate table drop column backup first" — order unclear), and anything where compression introduces real ambiguity. Resume caveman after the risky part. A saved token is never worth a misread security finding or a corrupted instruction.
4. **No self-reference.** Subagents don't announce the mode or tag their output ("me caveman think"); they just report compressed.

## Where it plugs into the workflow

- **Subagent prompts** (Phase 2 fan-out): write the scoping instructions caveman-style, but keep the verbatim Hard Rules 4 & 6 block and any by-design carve-outs in plain language (auto-clarity — these must not be misread).
- **Subagent reports**: instruct each subagent to reply in the active caveman level, evidence verbatim, in the Finding format (for audits) or the observation format (for exploration).
- **`sub-continuous` head-doc / blackboard**: the progress map, ledger, and findings-so-far are written caveman-style to keep the continuation state small (it is re-read every resume, so its size is paid repeatedly). The front-matter, handles, and status legend stay literal so resume parsing is unambiguous.
- **Promotion to the deliverable**: when findings graduate into an ADR or a plan, the orchestrator **expands** them from caveman to `--verbosity`. Caveman is the transport; it never reaches the reader.

## Net effect

`--caveman` lowers the token cost of the parts of a run that scale worst — many subagents, long fan-outs, and the repeatedly-re-read continuation state — without lowering the quality of either the exploration (evidence is preserved exactly) or the deliverable (rebuilt at full verbosity for humans). It pairs naturally with `--sub-continuous` (more exploration per budget window) and with large `--depth=deep` runs (more subagents, each cheaper to hear from).
