# P0 — Prepare physical-slot candidates without auto-mapping

**Issue #73; depends on owner-merged PR #116. Research only.** The standalone
`p0_report_case_engine_slot_map_draft.py` runs the *actual* current production
simulator, revalidates the exact local case, fresh private screenshot file byte
hashes and previous human-reported review worksheet, and lists only the engine
slots sharing the same numeric game-round claim and typed physical address.

```bash
python -m tools.research.p0_report_case_engine_slot_map_draft \
  --scenario explicit-scenario.json \
  --case private-case.json \
  --manifest private-image-manifest.json \
  --evidence-root private-images \
  --review-worksheet private-review.json \
  --output-json NEW-slot-map-preparation.json
```

The result is **not** the `p0_real_engine_slot_map_v1` object accepted by
PR #116; it has no `bindings`, chooses no `engine_wave_id`, and reports
`automatic_slot_bindings_created=0`. Candidates may have different Wave IDs,
units, or phases; their presence at one physical position **never** establishes
that the historical Gameforge Wave or battle scenario matches. A researcher
must independently inspect and assert an exact Wave/round/slot relationship,
then manually construct the existing strict slot map. The PR #116 downstream
validator still enforces every authenticity and comparability gate.

Missing Gameforge rounds, capture phase mismatch, unreadable review, absent
engine addresses, incomplete engine rounds, and unsupported rules are
explicitly marked as unsuitable for direct alignment. If the actual engine
uses a settlement/garrison-driven **effective** battlefield different from the
case, the tool fails closed even if the requested battlefield looks equal.

The new output records only source-byte SHA-256 and candidate engine metadata;
it never exports image contents, local paths or private source notes, and it
refuses to overwrite an existing report. All original-image authentication,
independent holdout, and mechanic-validation flags remain false or zero.

Verification: `pytest -q tests/unit/test_p0_report_case_engine_slot_map_draft.py`
followed by the repository's Hosted CI; synthetic fixtures exercise the real
engine, but **none** is an observed Gameforge battle. No production formula,
case JSON format, browser storage or original screenshot is changed.
