# P0 Doctor / Tender exact-capacity healing boundary

Continues merged PRs #75 and #77; tracked by Issue #73. **Research only: no changes to production formulas and no new Gameforge observations.**

## Gap and method

Earlier actual simulator Round1-to-Round2 Doctor/Tender tests verify sufficient healing, surviving shooters, and guarded partial allocation. This addition **directly executes the real engine round-start pipeline**, using invented but internally consistent Wave/Slot state with a previous death in every combat wave, no reserve, and persistent wounds split across two distinct eligible combat classes. Independently inspect the Round2 snapshot HP, living count, healing/unknown events, assumption IDs, and source provenance. This catches a fake-success event with unchanged actual wounds, or any resurrected casualties.

Doctor scenario: Swordsman + Hoplite are eligible; a wounded machine Gyrocopter remains unhealed regardless of spare support capacity. Tender scenario: Ram Ship + Balloon Carrier are eligible. The seeded deaths and wounds are synthetic, never observed in an actual battle.

## Capacity threshold matrix

Both current support types derive 4000 HP per unit in the packaged v17 profile.

| Support units | Eligible wounds | Expected **current engine** outcome |
| ---: | ---: | --- |
| 1 | 0 | No healing required; no heal event |
| 1 | 3999 | Full survivor repair |
| 1 | 4000 | Full repair, exactly exhausted capacity |
| 1 | 4001 | Named unknown partial allocation; no hypothetical repair performed |
| 2 | 4001 | Full repair, 8000 capacity |

An insufficient-capacity simulation reporting no applied repair is **not proof that Gameforge heals none**. Its exact partial distribution and healing-vs-redistribution ordering are UNKNOWN. Neither low-HP targeting nor the carrier/ram damage concentration candidates change here.

## Reproduce and evidence

Run the research program with these arguments:

    PYTHONPATH=. python tools/research/p0_healing_capacity_boundary_audit.py --output-json research-output/p0_healing_capacity_boundary.json --output-csv research-output/p0_healing_capacity_boundary.csv

Run the targeted regressions:

    python -m pytest -q tests/unit/test_p0_healing_capacity_boundary_audit.py tests/unit/test_p0_land_doctor_multiround.py tests/unit/test_naval_tender_multiround_experimental.py

Outputs retain per-wave damage and death state *before and after* the real Round2 start, independent Round2 slots, all emitted support/redistribution events and the bounded experimental assumptions. Deliberately corrupted post-healing HP is rejected by a negative regression. The new Hosted workflow runs focused and full pytest suites, compileall and JSON/CSV artifact archiving.

## Scope not proven

This isolated Round2 boundary **does not shoot** in Round2; existing PR #75 and Navy multiround tests provide the synthetic actual-combat integration checks. No original, independent observed Gameforge casualties are created. Exact partial healing across waves, reserve refill order, Gameforge hit assignment/Accuracy and casualty-to-next-round effects remain open in Issue #73. Do not interpret full-clear capacity as verification of unobserved allocation, and do not merge without owner authorization.
