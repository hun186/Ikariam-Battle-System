# Multi-round actual engine versus typed partial captures

Research only, Issue #73 remains OPEN. This read-only local CLI extends the prior single-capture actual engine diagnostic from PR #121. It executes the actual production simulator separately for each selected source capture and revalidates all existing screenshot-byte, manual reviewer worksheet and explicitly user-asserted physical-slot/Wave mappings. No historical Gameforge scenario reconstruction or combat mechanic is proven.

## Requirements and example

Supply the same six local inputs as the focused actual-engine diagnostic: scenario, canonical partial-observation browser case, image manifest, local image directory, completed review worksheet and exact user-asserted source-to-engine Wave/slot map. Select between 2 and 10 distinct captured case IDs in increasing numeric round order. Each selected capture must have source phase round_end, nonempty partial research objective and scope, and at least one typed numeric observation for the chosen side and line. ID means rounds[].id in the case JSON, not numeric battle round.

~~~bash
python -m tools.research.p0_report_case_multi_round_engine_diagnostic \
  --scenario explicit-scenario.json \
  --case private-case.json \
  --manifest private-image-manifest.json \
  --evidence-root private-images \
  --review-worksheet private-filled-review.json \
  --slot-map private-exact-slot-map.json \
  --capture-id captured-r80-id \
  --capture-id captured-r81-id \
  --capture-id captured-r82-id \
  --side attacker \
  --line flank \
  --output-json NEW-multi-round-diagnostic.json
~~~

All filenames and IDs above are placeholders, not authenticated observations. The current actual production engine is executed once PER selected capture through the unchanged strict source-gated PR #121 adapter. This intentionally favors auditable fail-closed behavior over speed for a bounded 2-10 round research task. All model, scenario, case, review and engine digests must agree across outputs; mismatches reject.

## Meaning of each pair

Output schema: p0_multi_round_actual_engine_capture_diagnostic_v1. It retains the individual focused round reports plus adjacent selected-capture pairs. A source-capture numeric round gap greater than one yields NOT_ASSESSABLE_MISSING_INTERVENING_CAPTURE_ROUNDS and null changes: no interpolation. A physical position typed only in one of the two captures yields NOT_ASSESSABLE_TYPED_POSITION_MISSING_IN_ONE_CAPTURE rather than a fictitious zero.

A numeric count change is only descriptive and requires BOTH per-capture upstream eligibility statuses ENGINE_MINUS_USER_TYPED_COUNT_UNVERIFIED, matching original physical position, nonblank identical typed unit and Wave labels and identical manually asserted engine unit/Wave identities. The reported fields typed_count_change, engine_count_change and engine_minus_typed_change are simple differences. They never establish why units changed: casualty, damage, reinforcement, wave swap, Reserve, healing and accuracy mechanisms are all unverified. A zero difference is not proof of a correct model. Equal Wave labels themselves do not independently prove continuity.

Gameforge UI HP bar semantics do not equal verified engine internal HP semantics. No HP numerical comparison, inferred game mechanic or global fit score is reported. No absent round or physical slot is invented; null stays unknown and explicitly transcribed zero remains a zero. Original images, local paths and source notes are excluded. Source authenticity, independent holdouts and calibration flags stay false/zero. JSON output is bounded 64 MiB and created exclusively; it refuses overwrite of any existing evidence or prior report.

Verification: pytest -q tests/unit/test_p0_report_case_real_engine_trace.py and hosted full Python CI. Test screenshots and private capture fixtures are synthetic only.
