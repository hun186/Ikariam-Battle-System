# P0 — What naval HP-bar screenshots could distinguish the current hypotheses?

**Issue #73 · research-only · prospective measurement planning.**

Starts at verified owner-merged [PR #85](https://github.com/hun186/Ikariam-Battle-System/pull/85) on Hosted `main` `0b2cc3ac81ebf5bdbcfb4507603f1027b5e46b42`. This study consumes that PR's **one actual synthetic no-partial model + nine mathematical counterfactual prefire HP projections**. **No new Gameforge battles, fresh screenshots, independent holdouts or official UI percentage calculation have been obtained.** No production simulator rule is modified.

## Why PR #85 model agreement was not yet sufficient

Several alternative healing-timing and recipient-location policies can yield identical displayed rounded HP percentages. In the player's interface, the R2 HP bars may be whole percentages rather than the simulator's internal two-decimal numbers; `floor`, `nearest_half_up` and `ceil` are **competing assumptions**, NOT verified Gameforge formats. Furthermore physical model damage position is not proven to map to a numbered real battlefield Slot: if two HP bars belong to the same unit Wave but the original screenshot has no Slot mapping, swapping their locations may be invisible.

A model is not uniquely identified just because its unrounded internal HP differs. This analysis calculates **pairwise separability** across the ten named **synthetic** cases, under:
1. Three alternative *fixed known* whole-percentage rounding rules.
2. One `unknown_same_rounding_mode_across_visible_slots` setting: both models can predict one vector under **any single globally consistent** rounding interpretation. A pair is robustly distinguishable only if the sets of allowed visible-bar vectors do **not** overlap.
3. Separately, **unmapped physical Slot ownership** (per-Wave multisets of bar percentages), compared with a hypothetical accurately numbered Slot map.

**An identical result, or overlap under allowed rounding/mapping, remains ambiguous — never infer a verified official Gameforge mechanic.** Reserve wound HP is used internally to verify source conservation but is **not proposed as screenshot-visible data**, because whether this HP can be inspected in the game UI is unverified.

## Operational prospective evidence output

The JSON outputs individual source-tagged case × live-combat-Slot integer percent predictions for each rounding rule, with model Wave ID, position, population and hypothetical HP denominator. For each rounding uncertainty scenario it reports:

- Pairwise hypothesis comparisons distinguishable from **all hypothetically mapped visible Slot bars**, versus those distinguishable from an **unmapped unordered multiset per Wave**.
- Explicit hypothesis pairs that remain ambiguous even if **all visible Slots are recorded**.
- A deterministic **greedy**, not globally optimal, recommended **capture order** of Slot identifiers, with marginal and cumulative distinguishable pair counts. It does not claim a minimum number of screenshots, nor can it know the true in-game Slot mapping.
- CSV with ordered candidate visible Slots, marginal/newly distinguished pairs, provenance and unverified UI flags. The order may differ by assumed rounding and cannot be applied as a confirmed game screenshot coordinate.

Real follow-up should seek one **new, independent** battle with R1-end and R2 prefire screenshot, Slot numbering and HP bars, unit alive counts, support vessel count, full setup/upgrades/Forge, reserve counts if visible, and any reinforcement events. If the UI percentage denominator or its rounding is still unknown, retain multiple plausible interpretations rather than force one. Existing player-reported **53% / 65% Carrier bars** are **a different unmapped in-sample fight** and MUST NOT be matched to these Tender synthetic projections.

## Reproduce and strict review gate

```bash
python -m pytest -q tests/unit/test_p0_naval_hp_bar_capture_discrimination.py
PYTHONPATH=. python tools/research/p0_naval_hp_bar_capture_discrimination.py \
  --output-json research-output/p0-naval-hp-capture-plan.json \
  --output-csv research-output/p0-naval-hp-capture-plan.csv
```

Hosted checks must pass on the **exact PR HEAD**; do formal Codex Review and resolve findings; retain a Draft PR and never Merge without explicit owner authorization. Keep Issue #73 OPEN. No evidence here identifies Gameforge healing allocation, chronology, individual casualty focus or official display semantics.
