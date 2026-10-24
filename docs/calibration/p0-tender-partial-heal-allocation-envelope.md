# P0 — Tender under-capacity HP allocation envelope before Round 2

**Issue #73 · Research-only, no production formula changed.**

This study continues owner-authorized merged [PR #83](https://github.com/hun186/Ikariam-Battle-System/pull/83), Hosted `main` `0d399bb53a28378ffd09add16884611a721a1411`. That PR showed that **one Tender** cannot clear all surviving naval wounds from a specific *synthetic* Round 1 battle, even though **one Doctor** suffices for the unrelated synthetic Land case. The simulator correctly emits `UNKNOWN-TENDER-HEALING-ALLOCATION` and uses named Experimental `EXP-TENDER-HEAL-NONE-001` to **apply no invented partial healing**. That fallback is not evidence that Gameforge heals zero.

## What this adds

Use only the live `p0_live_insufficient_support_round2.live_case("naval_tender", 1)` witness. Preserve source classification: all armies invented, authentic internal `simulate()` R1/R2 events for the existing no-partial-applied model, **zero observed Gameforge battles or independent held-out validations**. Read Round1-end actual surviving Wave wounds and Round2 *pre-volley* deployed Slot/Reserve counts, checking identity, eligibility, casualties, the original partial-heal UNKNOWN event and source HP conservation independently.

Produce four explicitly different **mathematical** cases:

| Hypothesis | Hypothetical allocated 4000 HP budget | Round2 actual combat executed under it? |
| --- | --- | --- |
| Current Experimental no-partial-applied fallback | 0 | **Yes** for actual prior PR #83 witness; this PR only replays observed model R2 prefire |
| Prioritize Ram Ship surviving wounds | Up to 4000 first; remaining for other eligible Wave(s) | **No** |
| Prioritize Steam Ram surviving wounds | Up to 4000 first; remaining for other eligible Wave(s) | **No** |
| Proportional allocation by Wave injuries, integer largest remainder | Exactly 4000, proportional among eligible wounded Waves | **No** |

For hypothetical cases, keep the *real modeled Round2 deployed unit populations unchanged* and re-apply the package's existing provisional `reserve_redistribution` integer rounding rule to each wave's remaining wounds. The output yields per-Slot / Reserve projected HP under that **specific bounded mathematical assumption**. It is **not** a second combat simulation, a candidate official healing rule or validated true heal-before-RR chronology. The Gameforge game could allocate by **individual injured ship**, not Wave; the deployed makeup, applied capacity and order may differ.

To prevent baseline drift, the zero-heal variant must **reproduce the real synthetic Round2 prefire Slot/Reserve damage exactly**, not just agree in total. Each alternative is explicitly bounded by 4000 model HP, eligibility, Wave injury and positive remaining HP; no prior casualties may revive. Negative mutation tests reject a corrupted public Round2 snapshot, fake eligibility/official assumption, duplicate Wave identity and out-of-bound capacity. JSON and CSV retain original source provenance, hypothesis ID, per-Wave repair/remaining damage, assigned per-Slot HP and reserve HP, plus flags indicating zero actual Gameforge observations.

## Use and further falsification

```bash
python -m pytest -q tests/unit/test_p0_tender_partial_heal_allocation_envelope.py tests/unit/test_p0_live_insufficient_support_round2.py
PYTHONPATH=. python tools/research/p0_tender_partial_heal_allocation_envelope.py \
  --output-json research-output/p0-tender-partial-healing-envelope.json \
  --output-csv research-output/p0-tender-partial-healing-envelope.csv
```

To identify the genuine official mechanism, require a **new independent actual battle** with identical fleets, one Tender, exact Round1 individual/Slot survivor HP, original Round2 prefire HP bars and deaths (ideally each numbered Slot), and all relevant upgrades, Forge state, any reinforcements. The game does not expose per-projectile shot trajectories through these historical reports; do not mislabel simulator grouped damage events as official traces.

Keep Issue #73 OPEN. Formal exact-HEAD Hosted CI, Codex Review and explicit owner Merge authorization are required before integrating this research; continue maintaining `.codex/memory.md` and documented remaining UNKNOWN boundaries.
