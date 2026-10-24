# P0 — Naval 53/65% vs 57/69% HP bars: exact integer rounding/overkill inverse bounds

**Status:** research-only conditional falsification, following owner-merged PR #81 (`main` `4213123def24fbdd7b39f11096e7a7c840ccaaa0`). **No production formulas, Gameforge UI assumptions or historical source records have been modified.**

## What the owner actually reported

The existing 2026-10-13 user-chat-source fixture `tests/fixtures/reverse_engineering/naval_air_counterparts_20261013.json` reports a reverse ATT14/Forge5 30 Paddle Speedboats (2×15) vs six Barbarian Carriers (2×3), end of Round 1: **one dead Carrier per position**, with **two remaining bars 53% and 65%**. Physical bar-to-slot mapping and official Gameforge bar denominator/rounding are **unverified**. A second historic user-chat DEF14/Forge5 Barbarian fast-vs-player carrier case reported **0 total deaths, 65% and 70% bars**, but its original round number is not independently asserted.

The model-only single-round `simulate()` scenario injects fictional First-line fillers to let both sides engage, under an in-sample Experimental carrier selector. Its reported end-of-Round 1 Slot bars for the reverse case are **57% and 69%**. Both its **model shot allocation and model discarded-overkill** are not genuine original per-ship attack traces.

## Strict integer inversion, *conditioned* on survivor-only denominator

For `C = survivors × unit_HP`, displayed integer percentage `p` is compatible with wound HP `W` only if `p = R(100×(C−W)/C)`. The report inverts this with exact integer arithmetic for **floor**, **nearest-half-up** and **ceil** rounding, independently of a specific damage mechanism. For `C=2×2800=5600`, assuming `floor`:

| Original **unmapped** observed bar | Required survivor wound range | Current synthetic retained wounds | Extra wounds required | Model discarded overkill budget | Feasible recovered portion under this hypothesis |
| --- | ---: | ---: | ---: | ---: | ---: |
| 53% | 2,577–2,632 HP | 2,359 HP | 218–273 HP | 233 HP | 218–233 HP |
| 65% | 1,905–1,960 HP | 1,685 HP | 220–275 HP | 233 HP | 220–233 HP |

Recovering the **entire 233 model-discarded HP per Slot** conditionally yields survivor bars **53% and 65%**. This arithmetic coincidence is not evidence that Gameforge retains or reallocates overkill; it was already discussed as a mathematical counterfactual. This PR adds **a quantified feasible interval**, a checkable 233-HP budget bound from current **grouped engine events**, and comparisons under three competing display-rounding choices.

Under the *same survivor-only denominator and unchanged model damage*, floor admits one bar↔slot mapping for each of the two historical bar-bearing cases. Nearest-half-up and ceil admit none using **only recovered model-discarded overkill**. This statement is conditional: a different actual hit distribution, denominator, UI convention, or original fleet composition can produce other results. It does not establish official floor rounding, a unique true slot mapping or any correct official Focus/P/IR mechanism.

Cases without source bars remain marked `not_assessable_no_original_bars` (3 of 5); no artificial observations are introduced. Original DEF14 unknown round stays unknown. All five source cases were already researched **in sample**, with **zero independent held-out battles**.

## Reproduction and hard stops

```bash
python -m pytest -q tests/unit/test_p0_naval_hp_bar_inverse_bounds.py tests/unit/test_p0_naval_slot_hp_falsification.py
PYTHONPATH=. python tools/research/p0_naval_hp_bar_inverse_bounds.py \
  --output-json research-output/p0-naval-bar-inverse-bounds.json \
  --output-csv research-output/p0-naval-bar-inverse-bounds.csv
```

All source bar provenance, modeled shot groups/assumption IDs, lack of true Slot mapping, and synthetic discarded-overkill values remain separately marked in JSON. CSV includes case ID, rounding hypothesis and **provisional** mapping rather than hiding the ambiguity. Tests reject invalid rounded percentages, forged holdouts, missing/wrong addressed damage events, broken damage/overkill conservation and attempts to relabel unknown UI semantics as verified.

## Next real-world evidence gate

Collect a **new previously unseen Gameforge battle** with both complete fleets, upgrades, Forge state, round, carrier casualties by numbered physical slot, UI bar screenshots with matching Slot identities, and the game/UI version. To identify the actual denominator or rounding, capture at least one **same-slot** known HP state before and after combat, rather than inferring the rule from one in-sample matching pair. Until such evidence is available, do not port the hypothesized extra wound HP or bar convention into the production simulator.
