# P0 naval: survivor HP residual falsification (historical samples)

Continuing merged PR #76, tracked by Issue #73. **Research only**: this changes no combat formula, policy or Gameforge rule claim.

## Source scope

The existing naval air-counterparts fixture has four user-chat observations and one **separately sourced** DEF3 no-Forge observation. All **five were already researched** in this repository and are therefore classified as previously analyzed/in-sample; there are **zero independent holdouts**. The user confirmed 30 speedboats, six carrier targets and two 15-vs-3 positions for the additional DEF3 observation, but its slot deaths and exact opposing fleets remain unavailable. The original unit-equivalence mapping remains provisional.

This tool runs the real simulator under its existing Experimental rules, in a controlled single-round fight with **fictional First-line fillers** to enable naval attack phases. It exports original totals and any reported slot losses / HP bars separately from model target-slot deaths, surviving HP, engine damage events, model assumptions and full round-one event trace. Where target-slot ammo is not exposed by the control snapshot it is **unknown**, never invented.

## Reproducible commands

~~~bash
PYTHONPATH=. python tools/research/p0_naval_slot_hp_falsification.py \
  --output-json research-output/p0_naval_slot_hp_falsification.json \
  --output-csv research-output/p0_naval_slot_hp_falsification.csv
python -m pytest -q tests/unit/test_p0_naval_slot_hp_falsification.py
~~~

## Key falsification target: reverse ATT14 / Forge5

User chat reported player 30 Paddle Speedboats vs six Barbarian Carriers at Round 1: **one carrier death in each of two positions**, with **53% and 65%** remaining bars. The current controlled engine predicts **one death per position** but **57% and 69%** under its modeled survivor HP denominator, an unmapped sorted-pair **+4 / +4 percentage-point** gap.

The previous mathematical hypothetical which retains damage after a destroyed carrier can reproduce **53% / 65%**, but is **not a verified official damage-overflow mechanic and is not the engine's output**. Do not modify combat overkill to match just this in-sample case.

The original battle screenshots are not attached; displayed bar-to-physical-slot mapping and the true UI HP calculation are unconfirmed. The report compares sorted pairs merely as a diagnostic, **not proof of a specific game slot's HP parity**. DEF14/Forge5 reported bars 65%/70% are similarly conditional. The other historical cases may match casualty aggregates under controlled assumptions without independently validating allocation mechanics.

## Gates and next work

The comparison rejects historical cases that claim independent/holdout status, invalid observations, malformed model slot coverage, or missing model damage events. Unknown original rounds remain unknown, and never inherit the simulator's round number. Hosted workflow runs focused tests, full pytest and reproducible JSON/CSV artifact upload.

The next true falsifier must be a **new, previously unmodeled real battle**, collected with original complete fleet formation, Workshop/Forge, round number, numbered physical-slot casualties, surviving HP bars (and UI denominator/rounding if verified), and any subsequent round. Record original provenance *before* fitting. Assess multiple candidates on the same independent data; keep Doctor/Tender partial allocation and overkill semantics explicitly unknown.
