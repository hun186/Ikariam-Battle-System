# P0 — Round2 same-Wave Reserve refill, healing and RR continuity

## Verified baseline and scope

Starts from owner-authorized merged PR #78 and main `3d3cfbc8d513efe4e4cd65059a304ebb8439451f`. PR #78 audited the Doctor/Tender 4000-HP capacity threshold without Reserve. This follow-up tests actual **Round2 existing-engine preparation**, with a damaged Reserve and one partially empty slot, under the same-Wave refill path.

**All states are SYNTHETIC and seeded, not Gameforge battles or independent holdouts.** The real `_prepare_round_start` pipeline is executed but no actual attacks are simulated in this audit. No production mechanics changed.

## Controlled conservation witnesses

| Witness | Land Hoplite | Naval Ram Ship |
| --- | ---: | ---: |
| Original / living / previously dead | 121 / 120 / 1 | 25 / 24 / 1 |
| Two deployed slots before Round2 | 30 + 10 (cap 30 each) | 6 + 2 (cap 6 each) |
| Reserve before | 80 | 16 |
| Round2 after same-wave refill | 30 + 30, Reserve 60 | 6 + 6, Reserve 12 |
| Wounds before | Slot1 600 + Slot2 200 + Reserve remaining | Same |

Both resulting slots each hold precisely one-fourth of the same Wave's living population. Without support, the existing provisional RR hypothesis therefore assigns 5000 surviving wounds as 1250 / 1250 / 2500 (slots/Reserve), and 5001 wounds as 1250 / 1250 / 2501. These are **simulator predictions, not observed HP bars**.

Per-domain cases: no support + 5000; one supporter + 5000; one supporter + 5001; two supporters + 5000; one supporter + 4000. Insufficient 4000-HP support **does not mean the real game repairs none**: current Experimental must identify unknown partial allocation and refrain from inventing a Gameforge answer. Two supporters fully clear 5000 injury; one supporter fully clears exactly 4000.

The audit compares real mutated Wave/Slot damage and alive counts with independent expected numeric HP shares, checks public snapshots, healing/RR event totals and assumption IDs, and injects two negative mutations (fake Reserve wound, fake Reserve resurrection) that must be detected even when events were unchanged. Every case preserves one historical death and provenance. Separate prior multi-round simulate() tests remain responsible for active Round2 shots.

## Run and evidence

    PYTHONPATH=. python tools/research/p0_reserve_rr_healing_continuity.py --output-json research-output/p0-reserve-rr-continuity.json --output-csv research-output/p0-reserve-rr-continuity.csv

    python -m pytest -q tests/unit/test_p0_reserve_rr_healing_continuity.py tests/unit/test_p0_healing_capacity_boundary_audit.py

Hosted Actions run the focused and full regression suites, compileall and upload a versioned structured JSON/CSV evidence artifact.

## Remaining Issue #73 unknowns

No observed individual-shot hit trace, no independent per-slot Gameforge HP holdout, no verified partial Doctor/Tender allocation or healing-vs-RR ordering, no new cross-wave reinforcement/fallback or ammo model, and no solution yet for observed naval 53%/65% vs controlled 57%/69% survivor bars. Keep Strict UNKNOWN. Do not merge without explicit owner instruction.
