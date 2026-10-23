# P0 Naval evidence gap: user-observed totals vs controlled engine outputs

This document accompanies Issue [#73](https://github.com/hun186/Ikariam-Battle-System/issues/73). The authoritative executable starting point is merged `main` commit `b37881247c25d5429379ef27020ce1a632e1e978` (PRs #69, #74 and #75 are already merged).

## Why this gate matters

A simulator matching **an already-used training/calibration battle** does **not** independently validate its weapon Accuracy, naval focus allocator, overkill behavior or complete Gameforge target distribution.

The new **read-only** tool `tools/research/p0_naval_observed_vs_model.py` runs six previously source-tagged game casualty totals against the current, explicitly **synthetic** controlled simulator setup. It exports JSON and CSV, retaining source type, observed/model totals, inferred/known round, model-only physical slots, missing-game-field diagnostics and the evidence needed to investigate discrepancies. The tool changes **no production combat algorithm**.

Run:

```sh
PYTHONPATH=. python tools/research/p0_naval_observed_vs_model.py \
  --output-json research-output/p0_naval_evidence_gap.json \
  --output-csv research-output/p0_naval_evidence_gap.csv
pytest -q tests/unit/test_p0_naval_observed_vs_model.py
```

## What is observable versus unknown

| Case group | What the user actually supplied | Controlled model / comparison | Not yet assessable |
| --- | --- | --- | --- |
| PvP Fast Boats 30 → player Carrier 6, ATT12/DEF8, ATT20/DEF16, ATT17/DEF18 | **Round 1** aggregate Carrier losses **2, 2, 1**, both sides Forge5 (confirmed later in conversation) | Experimental in-sample candidate yields aggregate **2, 2, 1** with **invented 35 Steam Ram First-line fillers per side** | Which actual Carrier slot lost how many, exact original support fleet and individual hits; no measured Carrier HP bars for these three cases |
| Barbarian Deckwrecker 36 → player Ram 36, DEF14/DEF15 | Excel `野蠻人.xlsx` worksheet `野撞打開爐衝撞`, F4:F19 recorded total **6 → 0**. Separate user chat described one loss per six physical Flank slots at DEF14 and none at DEF15 | Bounded Experimental pooled naval candidate, **invented First-line fillers**, yields aggregate **6 → 0** | Original complete battle setup, independently verifiable per-slot Gameforge battle report, real shot traces and any automatic Round1 timing claim for the Excel observations |
| Ram DEF19/ATT20 | **Separate user-chat case**, **not Excel row**: player deaths **0**, surviving player 63% HP bar, Barbarian 3 deaths per Flank slot and 88% HP bar | Controlled candidate yields player aggregate **0**; model-only slot damage is emitted for separate inspection | Whether the original displayed HP bars mean survivor-averaged HP, aggregated slot HP or another UI convention; true per-slot telemetry and original full fleet |

**Important:** a matching aggregate produces the status `aggregate_match_in_sample_only`, never `validated` or `held_out`. Slot casualty parity, UI HP bars, true original fleet reconstruction and independent holdouts remain explicitly `not_assessable`. The model's physical-slot event trace is **not** a Gameforge hit log. Ram workbook case timing is not silently asserted to be Round 1.

## Next empirical evidence priority

For each new independent battle collect its source date/game version, starting fleet *all* formations and Wave entry batches, both sides' Forge and Workshop grades, specific round, per-physical-slot unit counts and deaths, visible HP bars with screenshot, ammunition and (where available) next-round continuation/Tender support. Preserve missing fields as `unknown` and do not backfill them with simulator predictions.

Once **unseen holdout cases** exist, compare both casualty total **and** per-slot losses / post-round HP (with UI semantics understood) before generalizing any carrier T74 or Ram F(A,N) selector. Until then these remain bounded Experimental candidates on merged main, with Strict's UNKNOWN boundaries intact.

## Review and merge boundary

New Draft PR contains **research report, tests, CI workflow and documentation only**; it does not alter engine, Accuracy, Forge or Tender rules. Require exact-head Hosted CI, Codex Review P1/P2 resolution, and **separate owner authorization** before merge.
