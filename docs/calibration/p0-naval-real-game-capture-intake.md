# P0 — Real naval R1-end / R2 pre-volley screenshot intake and safe hypothesis screening

**Issue #73.** Research-only complement to owner-merged [PR #86](https://github.com/hun186/Ikariam-Battle-System/pull/86), `main` SHA `1351cd748d5c80c6b6ef66f118b48423a1aadd76`.

## Problem this addresses

The existing Tender=1 study has 10 internal **synthetic** model cases and 12 active simulated Slot HP channels, but has **zero new Gameforge Tender R1/R2 battle observations and no independent holdouts**. Its capture priority output is a plan, not an observed battle. To collect new data without contaminating evidence, require explicit screenshot references, battle setup, timing, source classification and recorded visible R2 HP percentages before performing even an assumption-dependent model comparison.

**This tool does not view screenshots.** It validates **manually transcribed and explicitly unverified data**. A path/label typed as a source reference is not independently checked for existence, contents, hash or authenticity. No game mechanic, mapping, integer rounding, model-to-real equivalence or truly independent holdout can be established automatically.

## Reproducible operation

```bash
PYTHONPATH=. python tools/research/p0_gameforge_naval_capture_intake.py \
  --write-template my-real-battle-EMPTY.json
# Edit ONLY your copy with actual screenshots and their distinct references.
PYTHONPATH=. python tools/research/p0_gameforge_naval_capture_intake.py \
  --input my-real-battle-EDITED.json \
  --output-json my-real-battle-assessment.json
```

The template is **empty**, explicitly `record_kind=template_no_game_observation`, and contains no fabricated battle. Supply `record_kind=user_transcribed_unverified`, an evidence ID and three distinct evidence references for actual R1-end, R2 prefire and fleet setup. Each recorded R2-bar entry references the R2 screenshot. For this specific research comparison, also document supported naval battlefield ID, **one Tender**, Forge level, Workshop details and absence of reinforcements; affirm R2 picture is **pre-fire**. An explicit `model_fleet_equivalence=asserted_by_submitter_unverified` enables a purely **conditional** screen; it does **not** prove source equivalence or establish the Gameforge healing rule. Unknown setup or missing R1 context yields `NOT_COMPARABLE`, not a false negative.

### R2 HP capture shape

```json
{
  "unit_id": "ram_ship",
  "wave_id": "model-wave-id-hypothesis",
  "model_damage_position": null,
  "visible_percent": 70,
  "units_alive": null,
  "source_ref": "reference-of-R2-prefire-image"
}
```

This is an illustrative **schema example**, **not an observed 70% Gameforge bar**. Unknown model-to-real Wave IDs must not be silently guessed: in such cases the tool returns `NOT_COMPARABLE` until a mapping hypothesis is documented. Choose `mapping_mode=unmapped_per_wave` with `model_damage_position=null` to acknowledge unknown physical Slot addresses, or `assumed_model_slot_address` with a modeled position **only as an explicit, unverified hypothesis**. If only a subset of same-Wave bars is visible, unmapped comparison tests any subset of available model Slots, rather than incorrectly assuming the first numbered Slot. Recorded mapped Slot population, if supplied, must agree with model population before a what-if comparison is allowed. Actual game figures differing from the model should be flagged as **not comparable**, not fabricated away.

The output preserves user-transcription provenance, zero independently verified original Gameforge observations, zero independent holdouts and `official_game_mechanism_verified=false`. Valid captures yield `CONDITIONAL_SCREEN_ONLY`, listing model cases with matching visible percentages under a **single consistent global candidate rounding mode** versus incompatible cases *only if all modeling assumptions hold*. An impossible match across all ten models signals a model/scope mismatch, not official disproof of a Gameforge mechanic. Noncomparable captures emit structured error descriptions and exit 2. CLI refuses to accept arbitrary fields claiming `official_game_mechanism_verified`.

The historical user-reported **53% and 65% Carrier HP bars** refer to an unrelated in-sample battle and must **never** be imported as though they were a new Tender=1 R1/R2 observation.

## Remaining research gate

An observer must supply original files, validate event provenance and Wave/Slot mappings externally, and ideally obtain *held-out independently collected* repeated battle data. This tool does **not** derive true Gameforge per-ship damage, allocation or RR order, use screenshots as trustworthy data automatically, or modify the battle simulator. Keep Issue #73 OPEN. Draft PR requires exact-HEAD CI, formal clean Codex re-review and new explicit owner merge authorization.
