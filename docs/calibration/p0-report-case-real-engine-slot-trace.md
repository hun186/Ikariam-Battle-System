# P0 — Real engine execution → captured physical slots (research)

**Issue #73; research-only.** This bridge runs the real
`ikariam_battle.simulate()` on an explicit scenario. It does NOT
reconstruct or authenticate a historical Gameforge battle. The user
is responsible for scenario input, screenshot origin and any asserted
mapping. This is distinct from PR #115's user-entered predictions.

## Local production-engine trace

From the repository root (Python 3.11+):

    python -m tools.research.p0_report_case_real_engine_trace \
      --scenario explicit-scenario.json \
      --output-json NEW-real-engine-trace.json

The output contains SHA-256 of exact scenario bytes, engine source
`ikariam_battle/engine.py` bytes, serialized actual engine result bytes,
real policy/status/rounds completed, actual assumptions and unsupported
mechanic events, plus original model snapshots' `side`, `engine_round`,
`line`, `physical_position`, `damage_position`, `unit_id`, `wave_id`,
`slot_id`, `units`, `casualties`, `damage`, and engine
`hit_points_percent`. No fabricated predictions; the tool really calls
the current production engine, but the scenario is still hypothetical
unless independently corroborated.

Engine round 0 represents an initial model state, NOT end of game round
0. Engine round N is normally a completed round-end snapshot, but
an unsupported-mechanic boundary may stop mid-round. Do not infer an
unexecuted game action from such a truncated trace.

The engine's `hit_points_percent` is an internal aggregate metric.
There is **no authenticated equivalence** to the game UI HP bar
denominator, rounding or semantics.

## Optional exact, explicitly user-asserted slot binding

Only with a private browser-case v1 JSON, original local PNG/JPEG
evidence root, filled prior screenshot manifest and valid PR #114
manual-review worksheet:

    python -m tools.research.p0_report_case_real_engine_trace \
      --scenario explicit-scenario.json \
      --case private-case.json \
      --manifest private-image-manifest.json \
      --evidence-root private-images \
      --review-worksheet private-review.json \
      --slot-map private-exact-slot-map.json \
      --output-json NEW-bound-engine-trace.json

A slot map must use exactly these top-level fields and explicitly
tie an original case to the scenario and a canonical review row:

    {
      "schema": "p0_real_engine_slot_map_v1",
      "case_id": "exact-private-case-id",
      "case_sha256": "sha256-of-exact-original-case-bytes",
      "scenario_sha256": "sha256-of-exact-scenario-bytes",
      "bindings": [{
        "review_item_index": 0,
        "target_capture_id": "exact-captured-target-id",
        "engine_round": 2,
        "side": "attacker",
        "line": "first",
        "physical_position": 1,
        "engine_wave_id": "actual-wave-id-from-prior-engine-trace"
      }]
    }

This is illustrative data, NOT a Gameforge observation. The validator
checks exact scenario/case SHA-256, battlefield, target capture ID,
exact numeric round (never invent a round offset), side/line/physical
position and engine wave ID, and prevents duplicate review rows and
forged extra fields. It rehashes the **current** local image bytes and
rechecks the prior reviewer worksheet; changed originals invalidate
the old review.

Each binding reports whether a real model slot actually exists and
its quantity/model HP context. Numeric differences stay **null** by
design: even a matching model slot or reviewer-reported 'readable'
photo does NOT independently verify real-game slot identity, unit
continuity, starting state or UI HP-bar equivalence. Statuses remain
`NOT_ASSESSABLE_*`. A missing engine slot remains unassessable.
Source provenance, independent observations, holdouts and model
calibration stay false/zero. This is an exploratory alignment record,
not a published empirical model accuracy metric.

## Safeguards

The CLI never uploads originals or includes screenshot bytes, private
free-text source notes or absolute evidence paths in the output.
It refuses to overwrite case backups, images, manifests or prior
reports. Real engine execution is distinguishable from manually
submitted candidate predictions and cannot be spoofed by providing
edited output as input. All regression test data are deliberately
synthetic, using minimal fake image headers, with the real simulator
invoked in tests.

No damage, target, HP, healing or Reserve algorithm is modified.
Issue #73 stays OPEN pending authenticated original game evidence and
independent held-out observations.
