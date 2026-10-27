# Naval R1-end versus R2-prefire: read-only delta ledger

Issue #73, research only. This utility performs simple arithmetic on
USER-TRANSCRIBED archive-v2 screenshot labels. It does NOT verify Gameforge
origin, image identity, timing, HP-rounding or official battle algorithms.

Run locally (keep private source JSON and images outside GitHub):

    PYTHONPATH=. python tools/research/p0_naval_stage_pair_deltas.py --input private-archive-v2.json --output-json private-stage-deltas.json

A valid nonempty PR #88 archive transcription is required. Comparison only
proceeds for distinct nonblank declared R1 and R2 source labels, a record
explicitly claiming R2-prefire timing, and explicit no reinforcements.
Rows must match ALL FOUR user-declared strings: side, unit_id, wave_label
and physical_slot_label.
If one phase and one side assign the **same physical slot label** to
different units or Waves, the tool cannot claim those overlapping rows are
separately identified physical groups. They appear under the report field
`ambiguous_physical_slot_labels`, and that side/slot is excluded from BOTH
phase comparisons. Other independently labeled slots may still yield
provisional numeric deltas, but the overall status stays PARTIAL.

A collision may reflect legitimate mixed ship/Wave occupancy in Gameforge,
not fraud or an impossible formation. The guard only prevents counting
ambiguous overlapping labels as distinct, independently comparable groups.
Different sides may use the same displayed slot label without a collision. Each row must contain the two integer observations
units_alive and visible_percent. Missing or mismatched rows are retained as
follow-up diagnostics; no wave/slot identity is guessed.

The result contains ONLY label strings, integer values, arithmetic differences
(R2 minus R1) and a user-JSON SHA-256, no original image bytes or original
record copy. Labels, hashes and "confirmed" values come from a submitter
and are NOT independently authenticated. Matching labels do not verify
physical ship continuity, even with declared zero reinforcements.

Statuses: UNVERIFIED_LABEL_MATCHED_STAGE_DELTAS means complete literal row
matching only; UNVERIFIED_PARTIAL_STAGE_COMPARISON identifies incomplete
or blocked comparisons; INVALID means the archive was invalid/blank,
writes diagnostics and exits 2. Partial reports exit 0.

Every report retains false flags for screenshot provenance, physical identity,
independently confirmed observations, independent holdouts, official healing/
damage mechanism and battle hypothesis comparison. A rendered HP percentage
increase with no ship-count change is NOT proof of Tender repair: aggregation,
rounding, reserve rebuild and heal/RR sequence remain unknown.

Only invented test records are included in CI. The workflow uploads its
existing EMPTY archive template, never user's records or screenshot bytes.
No battle engine production code or official-game formulas changed.
Issue #73 remains OPEN awaiting separately corroborated real game material.
