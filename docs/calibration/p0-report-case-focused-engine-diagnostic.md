# Focused actual-engine vs typed battle capture — research only

**Issue #73 remains OPEN.** This local, read-only CLI really executes ikariam_battle.simulate() using the researcher's explicit scenario, then reuses the existing PR #116 fresh local-image-byte, human worksheet and exact manually asserted slot/Wave mapping gates. It produces a focused comparison of **one captured round_end, one side and one line**, not a Gameforge battle replay or mechanic validation.

Unlike PR #120's browser candidate editor, these numbers come from a reproducible current production engine execution. That does NOT verify that the input scenario corresponds to the historic battle, that the screenshots are genuine, that a Wave mapping reflects actual game identity, or that any combat rule is proven.

## Source prerequisites

Use the existing private browser case v1 JSON, local screenshot files, image manifest, completed manual-review worksheet and explicit exact engine slot map:

- [Source image binding](p0-report-case-local-image-binding.md)
- [Manual review](p0-report-case-manual-visual-review.md)
- [Actual production engine trace and exact slot-map format](p0-report-case-real-engine-slot-trace.md)
- [Engine mapping preparation without automatic bindings](p0-report-case-engine-slot-map-preparation.md)

The case must have research.kind=partial_observation and nonempty objective/observed_scope. Its chosen captured-round ID (the literal JSON rounds[].id, not the game round number) must be a round_end snapshot. A canonical side and line must have at least one manually typed numeric observation (including explicit zero).

## Run locally from repository root

~~~bash
python -m tools.research.p0_report_case_focused_engine_diagnostic \
  --scenario explicit-scenario.json \
  --case private-case.json \
  --manifest private-image-manifest.json \
  --evidence-root private-images \
  --review-worksheet private-filled-review.json \
  --slot-map private-exact-slot-map.json \
  --capture-id "exact-id-from-rounds-json" \
  --side attacker \
  --line flank \
  --output-json NEW-focused-engine-diagnostic.json
~~~

The filenames above are placeholders for the actual local files. Strict comparison requires exact scenario/case SHA-256, matching actual effective geometry, exact source capture/engine round and manually asserted physical slot+Wave identity. No offset, replayed missing round, missing Gameforge Wave or absent slot is silently invented.

Output schema: p0_focused_actual_engine_capture_diagnostic_v1. A new file is written exclusively; existing evidence and reports cannot be overwritten. Output includes source/engine/review hashes, executed engine assumptions, selected source round/side/line, and only originally entered physical positions. For each originally typed slot it preserves count/HP/deaths with null distinct from zero and carries an explicitly user-asserted Wave binding (if one exists). When there is no binding, the status is NOT_ASSESSABLE_NO_EXPLICIT_REVIEW_SLOT_BINDING and no numeric engine comparison is performed. Other NOT_ASSESSABLE reasons are passed through from the prior strict alignment, which freshly rechecks the original local image bytes and reviewer worksheet. Numeric count difference appears only under ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED.

Engine internal hit_points_percent is context only. Gameforge screenshot HP semantics are NOT established equivalent and engine-minus-game-HP is always null; typed deaths are not inferred as engine casualty equivalence. No model accuracy ranking, inferred unknown positions, whole-battle fitting, independent holdouts, source authentication, or combat-mechanic verification follows even where the count delta happens to be zero. Results omit screenshot bytes, source notes and local image paths. Browser storage, capture JSON and combat code are untouched.

Run pytest -q tests/unit/test_p0_report_case_real_engine_trace.py and Hosted CI. All automated image and capture fixtures are deliberately synthetic, not real Gameforge evidence.
