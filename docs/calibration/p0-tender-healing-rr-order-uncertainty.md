# P0 — Tender healing versus RR order and localization (conditional model comparison)

**Issue #73, research-only.** Continuation of owner-merged [PR #84](https://github.com/hun186/Ikariam-Battle-System/pull/84) at Hosted `main` `812827f8135127d39216ba9f01e3a0def2d3b2ef`. Original Gameforge Tender allocation and Healing-versus-RR chronological order are **UNKNOWN**. Existing experimental `reserve_redistribution()` is a provisional simulator rule, NOT a confirmed official algorithm.

## Source and distinction between evidence types

Read the same **invented Naval fleet** R1/R2 internal simulator witness used by PR #83 and PR #84: one Tender under-capacity at nominal **4000 HP**. Source contains actual *simulated* R1 surviving per-Wave injuries, Round2 pre-volley physical Slot/Reserve quantities and HP, a named under-capacity `UNKNOWN-TENDER-HEALING-ALLOCATION` event, and synthetic R2 firing. There are **no new genuine Gameforge screenshots, battle observations or independent holdouts**. The source simulator **applied zero partial healing as an explicit Experimental fallback**, not evidence that the game would do so.

PR #84 produced conditional **Wave-level full-4000-HP allocation policies**: Ram Ship first, Steam Ram first, and proportional largest remainder. This PR holds each of those `3` Wave grants fixed and compares a second dimension: where hypothetical healing is applied relative to model RR. A fourth, zero-partial reference exactly reconstructs actual simulated Round2 prefire HP.

| Per-Wave policy | Per-Wave repair HP | Hypothetical order/location rule |
| --- | --- | --- |
| Original model fallback | 0 HP | Actual simulated prefire result; no alternate combat |
| Ram Ship first; Steam Ram first; proportional | 4000 HP total | (A) Wave wounds healed **before** provisional RR |
| Same three policies | 4000 HP total | (B) Provisional RR **first**, then heal earliest/central damage-position Slot before Reserve |
| Same three policies | 4000 HP total | (C) Provisional RR **first**, then heal Reserve before Slot |

Thus **1 baseline + 9 conditional alternatives**, each reporting per-Slot and Reserve persistent wounds/HP percentages, surviving populations and conservation proofs. Existing `reserve_redistribution` provides the same integer rounding primitive for all alternatives. None runs the actual R2 combat with healed combatants; this is a static **Round2 prefire HP projection**, not a verified Gameforge battle outcome.

### Fundamental identification limitation

The alternatives change **both timing and recipient localization**. A difference between (A) and (B)/(C) proves only that those invented composite transformations can yield different **mathematical** HP outcomes. It cannot establish that real Gameforge heals before or after RR, or targets Slots rather than individual ships. A matching HP bar alone may not distinguish any of these possibilities. Future real observations must specify numbered physical Slot, individual survivor HP if obtainable, all original fleets/reinforcements/upgrades, support count, Forge, R1 end and R2 start.

### Fail-closed validation

- Preserve exact source Wave IDs, R1/R2 casualty permanence, Slot addresses and Round2 frozen deployed/reserve populations.
- The **zero-heal** independent RR replay must equal the existing simulator's actual Slot and Reserve wounds **individually**.
- At every candidate: per-Wave wounds after = before − hypothetical heal; per-Slot + Reserve wounds = after; assigned healing equals hypothetical Wave grant; no ineligible/injured HP underflow or population resurrection.
- Negative mutations: duplicate physical Slot, corrupted original R2 prefire wound, fake ineligible heal, invalid or excessive capacity, duplicate exported projection IDs.
- Explicit provenance and `game_mechanic_verified=false`; no executable production healing, damage, accuracy, RR or targeting formula modified.

Reproduce:

```bash
python -m pytest -q tests/unit/test_p0_tender_healing_rr_order_uncertainty.py
PYTHONPATH=. python tools/research/p0_tender_healing_rr_order_uncertainty.py \
  --output-json research-output/p0-tender-rr-order-hp.json \
  --output-csv research-output/p0-tender-rr-order-hp.csv
```

Merging requires **exact-HEAD Hosted CI** and fresh formal `@codex review` with actionable P1/P2 resolved and **explicit owner Merge authorization**. Issue #73 remains OPEN for actual partial Doctor/Tender allocation/chronology, naval concentration and overkill, low-HP Land kills, and previously reported 53%/65% naval HP bar discrepancy.
