# Browser battle-report case library — local-only initial implementation

Starting from owner-merged PR #97 `main` `15424a51775bb5a8d03067c8731dd3fab7e304e4`. Adds a dedicated web UI at `/battle-cases.html`, linked from the simulator header. The editor and reader render **the same actual battlefield metadata-derived slot geometry**, including sides, physical slot positions, Second/Third, Flank, Air and Reserve. Available Land and Naval geometries derive from `GET /api/simulate` (not an invented separate layout truth).

## User workflow

Create/choose/delete a case (up to 50 per browser), select battlefield, name and note; add/remove numbered captured rounds in arbitrary order (real round one not required); choose R-end or next prefire phase, enter source screenshot notes. Click any formation tile to edit unit, wave, visible count, visible slot HP %, observed round deaths; switch Read/Write modes without changing battlefield layout. Use the Reserve section to add/edit/delete a reserve wave and its declared HP source. Download case JSON and import it on another computer to preserve original captured transcriptions. The exported JSON uses compact serialization so even long round-by-round calculation notes do not inflate through pretty-print indentation. Import and export share a single **64 MiB UTF-8 byte** limit enforced by the same model; download is rejected with a visible message rather than producing a file that cannot be restored. The model also rejects oversized external files prior to JSON parsing. Cases exceeding the ceiling must be separated into smaller cases. A large multi-round, 100-Reserve-per-side, non-ASCII backup round-trip is covered by Node regression tests.

### Safe slot-label carry-forward for adjacent captured rounds (merged PR #100)

After adding a new captured round (such as R82), click **沿用前一截錄格位標籤**
to insert a *data-entry draft* from the closest earlier **captured** round (such
as R81, not necessarily the previous game turn). The source is determined by
chronological round number, never JSON array order. Only physical side/line/
slot position plus unit ID and Wave label are copied; blank source labels
are omitted. This does **not** establish that the same unit/Wave was actually
present in the new screenshot—these are prompts for manual verification.

The new draft's **counts, HP percentages and deaths are always null**;
Reserve entries, Reserve HP, source-note text, captured phase, first-baseline
confirmation and any evidence/measurement flags are never copied from the
prior screenshot. The target's existing source text and Reserve remain
unchanged. The operation refuses to overwrite *any* existing target formation
slot or to use an empty/invalid nearest earlier label set; it never silently
skips an empty nearest snapshot to reach an older one. Each source object
remains distinct so later editing cannot modify the original report.

The label-only template is **not a new Gameforge observation** or evidence
for Accuracy, healing, attack priority or reserve reconstruction. Existing
JSON v1 backup schema is unchanged. Synthetic Node model and genuine
Playwright/Chromium acceptance tests exercise sequential R80/R81/R82 and
out-of-order R50 transcription, repeat-apply rejection and complete backup
round-trip. PR #100 was owner-merged after exact-head Hosted CI and clean formal Codex Review.

### Read-only captured-round entry progress (PR #101 candidate)

Round tabs show a **derived progress hint** per captured R number. `EMPTY` means no entered formation fields; `DRAFT` includes only source notes, Reserve declarations or label-only slots; `PARTIAL` has both filled visible-unit/count/HP entries and still-incomplete occupied slots; `FIELDS_ENTERED` means all **entered** visible formation slots have a unit, count and HP. Numeric zero is a valid entered value. These labels say nothing about unentered physical positions, screenshot authenticity, completeness of the entire battle, or official mechanics.

The selected round additionally displays entered visible slots, pending slots and Reserve row count. **Reserve HP is never treated as visible**, and source notes / baseline confirmation do not promote a round to verified. The display is computed from existing v1 data without modifying storage or export format. Real Chromium acceptance covers R80 filled, R82 label-only draft, and out-of-order R50. This is research transcription assistance only.

### Read-only earlier captured-round field comparison (owner-merged PR #102/#103)

The editor's collapsible comparison defaults to the chronological **nearest earlier
captured** round, not JSON array order or necessarily an adjacent game round.
The new UI can select any earlier **captured** source round. Future, same-round
or non-existent identifiers are rejected by the model; case/target switching
resets the choice, while read/edit changes preserve it. The choice lives only
in browser UI memory and does not alter case JSON, timestamp or localStorage.
The displayed round-number gap is informational: skipped battle intervals
must NEVER be treated as sampled, continuous observations.
It renders only physical `side / line / pos` addresses with some manually
entered data. Differences appear only if both captured phases match, both
visible count and HP are filled, and both nonempty **unit and Wave labels**
match. Other rows report `ONE_SIDED`, `PHASE_MISMATCH`, `INCOMPLETE` or
`LABEL_CHANGED` with no numeric difference. Entered zero is distinct from
missing null. Omitted tiles must not be interpreted as empty battle positions.

The calculated `countDelta` and `hpPointDelta` are **differences in
unverified typed inputs**, not observed kills, combat damage, healing, unit
identity, replenishment or official mechanics. Same Wave text does not prove
same real Wave across rounds. Reserve HP is never compared, case JSON v1 is
unchanged, and the operation cannot change stored data or engine results.
Missing original screenshots prevent empirical calibration of Issue #73.
PR #102 passed exact-source Hosted CI and clean formal Codex Review before owner Merge. PR #103 passed exact-source Hosted CI (14/14) and clean Codex Review before owner-authorized Squash Merge into `main` (`611765320122b50073d1ef2b88375505d9d81818`).

### Derived typed comparison CSV export (owner-merged PR #104)

The browser may download **only the currently selected earlier/target captured
pair** as a UTF-8-with-BOM CSV for spreadsheet analysis. It uses the **same
`compareCapturedRounds()` result** as the visible table. Each physical
side/line/position with any entered data becomes one row. Explicit
`comparison_status` can be `FIELDS_COMPARABLE`, `ONE_SIDED`,
`INCOMPLETE`, `LABEL_CHANGED` or `PHASE_MISMATCH`. Numeric
`typed_count_delta` and `typed_hp_percentage_point_delta` are
**empty for all non-comparable rows**, not zero. Entered numeric 0 is distinct
from an empty/missing field. Every row is marked
`USER_TRANSCRIPTION_UNVERIFIED` and
`TYPED_FIELDS_ONLY_NOT_COMBAT_CAUSALITY`, and includes case ID/name,
battlefield, captured round numbers, gap and phase, physical position, plus
typed visible unit/Wave/count/HP fields. The gap is **not** a continuous
battle observation. There are NO Reserve fields, original screenshot
content, official Gameforge source claims, inferred kills, heal amounts,
combat mechanics or provenance authentication.

Untrusted CSV strings are quoted/double-quote-escaped, control newlines
and tabs are normalized, and strings beginning with spreadsheet-formula
prefixes (=, +, -, @), including after leading whitespace, are prefixed
with an apostrophe. Actual finite integer numeric cells (including
negative deltas) remain numeric. Filenames sanitize imported case IDs.
CSV export is disabled with no prior round or no entered visible slots;
it does not mutate the case, timestamps, localStorage or JSON-v1 schema.
**CSV is a derived analysis view, NOT a replaceable JSON backup or
independently corroborated game evidence.** User must keep the existing
case JSON backup and original screenshot sources separately.

PR #104 passed exact HEAD GitHub Actions 14/14 and clean formal Codex Review before owner-authorized Squash Merge into main `96de242b77806eda8ebe6be927f1d29fb954a9ba` (2026-10-29 17:33 Taiwan).

### Whole-case adjacent **captured** timeline CSV (Draft PR #105)

One additional case-level button exports all chronologically adjacent **captured
snapshots** (not every true in-game round) into one Excel-compatible CSV.
For a case containing R50, R80, R81, R82, rows are emitted exclusively
from pairs R50→R80, R80→R81 and R81→R82, in numeric order even if stored
JSON round array is out of order. Each pair uses **the same**
`compareCapturedRounds()` and shared `comparisonCsvRows()` and CSV
formula-escaping helpers as the single selected-pair export.

Every row explicitly includes `earlier_round`, `target_round`, gap,
phases, physical side/line/position, typed values, comparison status,
`USER_TRANSCRIPTION_UNVERIFIED` and
`TYPED_FIELDS_ONLY_NOT_COMBAT_CAUSALITY`.
If both captured snapshots have no entered visible slots, a single
`NO_ENTERED_VISIBLE_SLOTS` record is retained for that pair with blank
numeric fields, **not skipped or portrayed as actual zero casualties**.
A missing physical position in one capture is `ONE_SIDED`, not zero
population. Unobserved intervening rounds are **never** interpolated.
Draft/phase/label mismatches maintain blank numeric deltas. Reserve HP,
original game screenshots, official mechanics, source authentication and
causal casualty/healing calculations are out of scope.

At least two captured rounds and a valid v1 case are required. The entire
CSV is constrained to 64 MiB, UTF-8 BOM, control-character normalization
and formula-prefix escaping; source selection in the single-pair UI does
not modify the independent full-timeline chronology. This is a read-only
derived report; users must preserve the original JSON case backup and
source screenshots. No localStorage write or case schema change.
Node/Python adversarial CSV decoding, empty-pair, out-of-order and
import/export invariance, plus real Chromium full-timeline download
are acceptance tests for PR #105. Neither test fixtures nor synthetic
screenshots count as new Gameforge observation for Issue #73.

### Reserve HP evidence constraint

Game report screenshots DO NOT display Reserve HP. Each new Reserve row starts with `hp=100`, `source=assumed_full`; that is **NOT** an observed screenshot measurement. All default Reserve rows are tagged `預設 100%（未觀測）`. For the **earliest captured round in a case** (which may be R80 or another mid-battle round), check the explicit per-side `baseline_confirmed` only after the user has ensured those first-snapshot Reserve ships are full HP. Without the confirmation a case remains `REVIEW_REQUIRED` for reliable initial HP analysis. If a user has independently and precisely derived other Reserve HP, switch to `calculated` and enter the integer percent plus at least 20 characters describing concrete calculation evidence. This remains *external computation*, not Gameforge screenshot evidence and requires independent review. A 100% assumption may never be modified while keeping `source=assumed_full`.

Dynamic ordering: adding a newly earlier captured round re-evaluates the case's first-round confirmation gate. Formation slots are visually observed HP, unrelated to Reserve hidden HP. The validator bounds positive/negative and float/bool percentages, slot identities and per-case length; imported JSON must match v1 contract and battlefield metadata. Import creates a new case ID and does not silently overwrite existing data.

### Storage and integrity limitations

Browser `localStorage` only, not a server database, account sync or persistent Vercel state. Always export JSON before browser cleanup/device switch; keep original screenshots privately outside GitHub. No screenshot upload, original-image authentication, official damage/Accuracy/healing inference or production simulation data ingest. The research archive's local SHA-256 binder and stage-delta tools remain separately available; this UI does not falsely claim screenshots are authenticated by typing a source note. Future tasks: optional authenticated persistent storage and schema-mapped evidence export, after explicit scope review.

Static page is duplicated at root and `public/` to support ASGI local routes and Vercel static serving, matching simulator's existing root/public index parity. `/battle-cases.html` and `/battle-cases-model.js` have explicit rewrites before SPA catchall. Regression tests verify static parity, ASGI routes and Node JS model provenance rules/syntax (when Node available). PR #99's real Chromium interaction and browser backup tests passed on the merged source; the label-draft extension passed exact-source CI and formal review before PR #100 merged.

### Real Chromium browser interaction acceptance

The static HTML and Node fake-DOM tests are not equivalent to a true browser.
The dedicated GitHub Actions workflow `.github/workflows/battle-report-browser-e2e.yml`
starts the repository's local ASGI app, installs Chromium and executes
`tools/report_case_browser_e2e.py` using Python Playwright and a fresh browser
profile. It uses entirely **synthetic case data**; no user's original Gameforge
screenshots or real personal identifiers are uploaded.

The browser flows cover R80 as the first captured report (after deleting
the initial empty R1), physical geometry slot indices, visible HP and deaths,
the explicit hidden-Reserve 100% assumption and user confirmation, read-only
versus editor rendering, R81 and an earlier R50 baseline, downloading a JSON
backup and uploading those exact bytes, deleting the original case and
verifying localStorage after reload, plus mobile viewport screenshots.
After reload the test re-exports the imported case and compares the entire
parsed JSON against the original download, allowing differences **only**
for the import-generated case ID, name and timestamps. This comparison
covers all captured rounds, source notes, physical slots, units/counts,
casualties, HP, Reserve origins and confirmation flags—not just the
visible R80 HP. Browser CI must pass on the exact revised source HEAD
before declaring this acceptance correction verified.
The successful Hosted workflow uploads synthetic desktop/mobile screenshots
for seven days. The workflow result must be checked before calling browser
acceptance passed. This does not verify official battle mechanics or game-source
authenticity.

For local execution install uvicorn and Python Playwright with Chromium,
start `uvicorn asgi:application --host 127.0.0.1 --port 8871`, then run
`python tools/report_case_browser_e2e.py --base-url http://127.0.0.1:8871`.
