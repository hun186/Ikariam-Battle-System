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

### Whole-case adjacent **captured** timeline CSV (owner-merged PR #105)

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

### Read-only captured-pair input coverage ledger (owner-merged PR #106)

The case editor now provides an **in-browser collapsible read-only overview**
of each consecutive **captured-snapshot pair**, using the exact same
`compareCapturedRounds()` status codes that supply the two CSV exports.
`summarizeCapturedTimeline()` validates the case, sorts a copy of the
entered rounds chronologically and counts **only physical positions with
some manually entered fields** per pair:
`FIELDS_COMPARABLE`, `ONE_SIDED`, `INCOMPLETE`, `LABEL_CHANGED`,
`PHASE_MISMATCH`, `NO_ENTERED_VISIBLE_SLOTS`. Completely empty
pairs count as one explicit *missing-data alert*, not one observed slot.
The table also shows round-number gaps (not actual observed intervening
rounds), with a button to navigate directly to the selected target capture.

The counts are **NOT an evidence authenticity or model accuracy score**.
`ONE_SIDED` means an address was entered for only one snapshot, not
that the in-game tile was empty. User-typed matching unit/Wave labels
do not prove identity across screenshots. No HP, casualty, healing,
Reserve HP, production combat formula or original-screenshot authenticity
is derived. No `localStorage`, timestamp or v1 JSON state changes.
The panel cannot replace the original screenshots and explicit
case backup. Adversarial Node tests include unsorted R50/R80/R81/R82,
label and phase mismatch, partial draft, blank snapshots, and
invalid schema; true Chromium tests exercise R50→R80→R81→R82,
read-only table and click-to-round navigation. Hosted exact-HEAD
CI and formal Codex Review are mandatory for PR #106.

### Per-physical-slot transcription review checklist (owner-merged PR #107)

The captured-pair coverage table's new `待查欄位` control opens a purely
**read-only, ephemeral** checklist for one adjacent **captured** pair,
showing the exact side/line/physical position, both sets of existing typed
unit/Wave/count/visible-HP fields, the reason that the pair is not
numerically comparable, and a specific reminder to cross-check original
screenshots. The model's `inspectCapturedCoveragePair()` only permits
an existing chronologically adjacent source/target ID from the **same
validated case**. This prevents arbitrary, future, foreign or nonadjacent
pair IDs being treated as coverage-ledger review items.

Only existing `ONE_SIDED`, `INCOMPLETE`, `LABEL_CHANGED`,
`PHASE_MISMATCH`, or `NO_ENTERED_VISIBLE_SLOTS` codes are reported.
If both screenshots have no entered visible slots, one explicitly
location-less missing-data reminder appears. If every entered physical
position is comparable, the panel says there are no *typed-field*
restrictions **but does not claim authentic Gameforge evidence**.
All user-entered text is HTML escaped; clicking an inspection control
does not alter current round, timestamps, localStorage, JSON backup or
other recorded fields. Clicking a round-navigation control still
navigates normally and clears the ephemeral detail panel.

One-sided placement is not evidence of zero units or absent troops;
different Wave labels do not prove wave identity, and a gap between two
captured rounds cannot establish events inside the gap. Do not derive
casualty, damage, heal, Reserve HP or official Accuracy rules. The
checklist has no field to mark real screenshots independently verified.
Original screenshots remain external and Issue #73 still needs source
evidence before combat mechanics can be calibrated. Exact-HEAD Hosted
CI must cover Node adversarial pair-ID/mismatch/zero/non-mutation checks,
root/public parity, and real Chromium pair inspection and click behavior;
formal Codex Review required before owner-authorized merge.

### Read-only cross-round pending-field CSV handoff (owner-merged PR #108)

The captured-round coverage panel includes a **CSV export of the entire
case's *noncomparable* adjacent-captured-pair review queue**, suitable
for opening in Excel and giving a researcher a list of source screenshots
and visible fields to check. It uses the existing
`summarizeCapturedTimeline()` adjacency plus the exact
`inspectCapturedCoveragePair()` statuses, and a shared safe CSV serializer:
`ONE_SIDED`, `INCOMPLETE`, `LABEL_CHANGED`, `PHASE_MISMATCH` and
`NO_ENTERED_VISIBLE_SLOTS`. `FIELDS_COMPARABLE` rows are deliberately
absent; if the entire case has no typed-field review needs, export is
disabled/rejected **without claiming the original Gameforge screenshots
were authenticated**.

One row records the case identity and battlefield, earlier/target
**captured** round numbers, round-number gap, both transcription phases,
physical side/line/slot if entered (blank for wholly empty pairs), both
sets of *typed visible* unit/Wave/count/HP, status and original-source
cross-check reminder. Entered zero is preserved and missing values
remain empty. All rows are explicitly
`USER_TRANSCRIPTION_UNVERIFIED` and
`SOURCE_IMAGE_NOT_VERIFIED_NO_COMBAT_CAUSALITY`. The CSV does not
include original images, screenshots' authenticity, Reserve HP,
inferred death counts, actual combat damage, healing or Accuracy. No
skipped game rounds are filled. This is *not* a task-completion/verified
status tracker and must **not** replace JSON-v1 case backups or the
private original evidence files.

It reuses the UTF-8 BOM, escaping of quotes/control newlines, spreadsheet
formula-injection guard (including leading whitespace), sanitized
filename and 64 MiB export ceiling. The operation never updates the
case, timestamps, localStorage or the underlying battle simulator.
Regressions parse CSV using Python's csv.DictReader after Node export
with deliberately unsorted R50/R80/R81/R82/R90/R100, injection labels,
valid zero/blank, fully comparable refusal, invalid case and
empty capture pair.
Formal Codex review of the initial export found a P2 browser-freeze risk:
calling `inspectCapturedCoveragePair()` inside each export iteration
recomputed the entire timeline. The implementation now performs one
chronological adjacency summary, projects each corresponding pair's
`compareCapturedRounds()` rows through the same pure shared
`reviewItemsFromComparison()` helper as the browser inspector, and
never regenerates whole-case adjacency within the export loop. An added
100-round × 7 pending slots performance regression enforces the
bounded-time behavior on supported case sizes. Genuine Chromium must download only the
R81→R82 pending row in the synthetic browser case and verify its source
fields and unchanged localStorage. PR #108 requires exact-HEAD Hosted
CI and formal Codex Review; **never merge without owner permission**.

### Source-note-only captured-round manifest CSV (owner-merged PR #109)

The captured-round coverage panel offers a second **source handoff**
file: a single-row-per-captured-round CSV containing the **existing**
free-text `round.source` value (screenshot filename / game version /
transcription context where manually entered), together with
`case_id`, case name, battlefield, `capture_round`, the unique capture
ID, phase, and the existing `roundEntrySummary()` entered/pending
visible-slot counts and entry status. It is sorted by numeric capture
round regardless of original JSON array order. Users can join the
separate pending-slot CSV to this source-note index by
`case_id + capture_round` (the pending CSV has both earlier and target
round numbers). One captured round is enough to export.

`SOURCE_NOTE_TYPED_UNVERIFIED` means only that **some non-whitespace
source note was typed**; `SOURCE_NOTE_MISSING` means the note is blank
or whitespace-only, including when user-typed formation fields exist.
Both states always carry `USER_TRANSCRIPTION_UNVERIFIED`,
`ORIGINAL_IMAGE_NOT_INCLUDED`, `NOT_AUTHENTICATED`, and
`NOTE_TEXT_ONLY_NOT_PROOF_OF_SOURCE_OR_COMBAT_CAUSALITY`.
It never attaches, reads, checks the existence of, hashes, authenticates
or claims to corroborate screenshot PNGs or reports. It does NOT infer
combat results, Reserve HP, healing, or casualties. `round.source`
may contain a local path or private filename; users must check the CSV
before distributing it. Unlike the source-note text, actual image
evidence remains external.

CSV uses the existing shared UTF-8 BOM serialization, Unicode/text
formula-prefix guard, control newline/tab normalization, sanitized
filename and 64 MiB cap. It validates the v1 case; exporting never
modifies timestamps, localStorage, the JSON backup, case schema, or the
simulator. Node/Python CSV-parser regression covers out-of-order
R50/R80/R81/R82, empty vs whitespace notes, escaped formula strings,
typed zero, injected newline, invalid schema and the unchanged
JSON round trip; genuine Chromium validates R80 synthetic source note,
blank R82, explicit source-authentication disclaimers and unchanged
localStorage. Exact-HEAD Hosted CI and formal Codex Review are required
before owner-authorized merge.

### Joined pending-slot and source-note handoff CSV (Draft PR #110)

A third optional download makes the two previous exports actionable
without manually joining spreadsheets: it lists **only the same
pending/noncomparable physical-slot rows** as the existing review-queue
CSV, with BOTH the earlier and target capture's existing source note
text and source-note presence flags. It preserves case ID/name,
battlefield, earlier/target **captured** round numbers and round gap,
phases, physical address, manually typed visible unit/Wave/count/HP,
review reason and source-check instruction. Nonadjacent game rounds are
**not** imputed, and entered 0 remains distinct from missing null.
Entirely empty captured pairs stay one explicit location-less
`NO_ENTERED_VISIBLE_SLOTS` row. A case with only comparable typed rows
does not export a joined queue; it does **not** mean images are verified.

`earlier_source_note_status` / `target_source_note_status` are
`SOURCE_NOTE_TYPED_UNVERIFIED` or `SOURCE_NOTE_MISSING`, computed
using the same `sourceNoteStatus()` as the original manifest.
Likewise, `earlier_source_note_text` / `target_source_note_text`
contain exact existing free text (after CSV control normalization),
not a hyperlink or verified upload. Each joined row additionally
carries `USER_TRANSCRIPTION_UNVERIFIED`,
`ORIGINAL_IMAGE_NOT_INCLUDED`, `NOT_AUTHENTICATED`, and
`NOTE_TEXT_ONLY_NOT_PROOF_OF_SOURCE_OR_COMBAT_CAUSALITY`.
Do not infer that a screenshot exists, has a matching file checksum,
was authenticated, or establishes a death/healing/targeting/Reserve HP
mechanic. Local screenshot filenames and paths may contain private
information and must be reviewed before sharing.

The older pending-review CSV format is unchanged for downstream
consumers; both exports share an internal single-pass
`capturedReviewQueueRows()` projection with one chronological coverage
summary and no `inspectCapturedCoveragePair()` call inside the loop
(the prior Codex P2 fix). Uses existing UTF-8 BOM, safe CSV escaping,
control normalization, formula-injection guard and 64 MiB size ceiling.
The new UI button is disabled when there are no pending typed-field
rows. Read-only operation leaves case JSON v1, timestamps,
localStorage and simulator untouched.

Node/Python CSV parser regression checks deliberately unsorted
R50/R80/R81/R82/R90/R100 captures, empty/missing/two-sided notes,
spreadsheet payloads, notes containing newline/tab, no-phantom
rounds, untouched original CSV, no source authentication claims and
unchanged JSON backup. The 100-round × 7-pending-slot performance
regression now covers the joined export too; the real Chromium
browser checks a single pending R81→R82 joined row, both source note
flags, absent original image and byte-identical localStorage. Exact-HEAD
Hosted CI and formal Codex Review required before explicit owner merge.

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

### Historical research case seed catalog (pending PR, 2026-10-30)
The browser can first-time seed up to 14 **historical research transcriptions**
from the existing repository's reverse-engineering fixtures via
`/battle-cases-history.json`. An explicit **載入之前 PR 的研究戰報** button
can restore missing catalog entries; stable `research-` IDs and a browser-local
migration marker make seeding idempotent and prevent deleted built-ins from
reappearing unexpectedly. Existing edited or imported cases are never
overwritten. No server database is created: users still own localStorage
data and JSON backups. The 50-case limit and v1 strict validation remain.

This includes the same owner Land R1/R80–89 battle (R2–79 explicitly missing),
a **different** 400-Slinger R76–80 battle, Crispi and Reikjavikas R1 source
casualties, and independently identified naval Ram, player speedboat/carrier
and barbarian/player air counterpart results. Source notes cite exact fixture
files; only observations attributable to a **physical slot** fill a tile.
Aggregate-only reports retain **no auto-assigned tile kills/HP**, while R1
source attrition with no observed survivor counts stores `count=null`.
A source image mentioned in a fixture is **not** a source image stored in
the GitHub repository; these cases do not authenticate Gameforge mechanics.

Validation must cover v1 schema/geometry, browser auto-seed and reload,
idempotent manual restore, preserving modified cases, empty-deleted history
marker, and ASGI/Vercel static parity.

## Explicit partial vs full source boundary

The full battlefield UI is a **template**; unentered positions are UNKNOWN
and must never be read as zero units. Case-level optional `research`
metadata distinguishes observation, control-condition, simulation hypothesis,
unknown information, and explicitly source-bounded absence. A statement like
"front line full" is a condition but does not prove exact original unit IDs,
numbers, HP, losses, waves or reserve size. Do not copy the 350-Hoplite
scenario from the flank Swordsman experiment into original source slots.
Self-selecting "complete battle" cannot authenticate missing combat evidence;
`researchEvidenceGate` always blocks whole-battle auto-calibration.

Legacy JSON case files lacking `research` remain valid and render unclassified.
New browser cases are partial by default. Case JSON export/import retains
metadata. Editing research notes changes local browser copies only.

## Focused side-and-lane study explorer — Draft follow-up after PR #118

The browser case library includes a **read-only** conditional partial-observation
explorer: select exactly one side and one runtime formation line, then display
**every physical slot from the canonical `GET /api/simulate` battlefield
geometry** for every independently captured round. Every slot's entered
unit/Wave/quantity/HP/death fields remain raw typed values. Missing fields are
`null` (shown as UNKNOWN, not 0); a slot with label-only input is marked a
non-numeric draft. Explicit typed zero deaths remain 0. No other line's units,
reserve or assumptions are silently imported.

This explorer is gated by validated case schema, `partial_observation` kind,
declared research objective + observed scope, and at least one numeric typed
field **on that exact selected side and line**. Legacy unclassified,
`research_summary`, user-declared `full_report`, geometry-less lines and
side/line with label-only input remain blocked. Neither the explorer nor
export grants `globalCalibrationAllowed`. Existing browsing, export/import,
research notes and localStorage remain unchanged.

Each capture shows its actual round number and phase, source text and a
**sum of entered per-slot deaths** with `enteredDeathPositions / physicalSlots`
coverage; an entirely missing death column yields a null CSV sum, not a
fabricated 0. This is not the *total battle casualties* or necessarily a
complete line death count. No missing game rounds are interpolated. There
is no cross-round wave identification, replenishment/depletion arithmetic,
cross-line causal inference, inferred damage/hits or engine calibration.
`exportFocusedLaneCsv` is CSV injection-escaped, byte-bounded and marks
source evidence `USER_TRANSCRIPTION_UNVERIFIED` and `NOT_AUTHENTICATED`.
The 2026-06-25 flank Swordsman study is an instructive separate fixture,
not newly imported as an authenticated full report.

Regression coverage: Node model tests for two-round gaps, null-vs-zero,
label-only and wrong-line guards, legacy/summary/full rejection, geometry
boundary, formula-escaped CSV and no JSON mutations; real Chromium tests
for selectable focus lane, unknown slots, CSV download and non-mutating
wrong-side browse.

## Scoped browser comparison: candidate prediction vs user-typed capture

After the owner-merged focused-lane explorer (#119), a follow-up adds a
**session-only candidate comparison worksheet**. It is an ergonomic browser
front-end for a narrow *user-entered* candidate; it does NOT replace the
independently image-byte-gated PR #115 candidate diagnostic or the PR #117
actual simulator slot-mapping preparatory tool. Neither the browser worksheet
nor a copied label is evidence that a current engine run produced the numbers.

1. Open a **partial observation** case, select the actual side/line and
   captured target round, and click *建立目前截錄回合的空白候選範本*.
2. The worksheet contains exact case ID, case \`updated\` revision, battlefield,
   captured round ID/number/phase, side, line, and the **entire canonical
   physical-position list**. Only user-typed unit/Wave labels are copied;
   predicted \`count\`, \`hp\`, \`deaths\` are ALL \`null\`. Set a nonempty
   \`candidate_label\`, an explicit \`assumptions\` description and only those
   predicted numbers that are genuinely available from an outside research
   hypothesis.
3. Paste the JSON into the editor and click Compare. UI and bounded,
   read-only CSV export show prediction-minus-user-typed numeric deltas **per
   field only when both exist on that exact physical address** and known
   unit/Wave labels do not conflict. Null means missing, not zero; 0 is a
   real explicitly entered value. If labels conflict, numeric differences
   are withheld. If Wave or unit identity is not known, the numeric difference
   is described as physical-position-only, NOT a common underlying wave.
4. No score, ranking, model fitting or mechanism validation follows. The
   candidate source class is always
   \`USER_ENTERED_MODEL_CANDIDATE_NOT_ENGINE_ATTESTED\`. The browser never
   calls POST /api/simulate, never authenticates source screenshots or an
   alleged engine revision, never updates localStorage with candidate text,
   and never changes combat formulas.

**Schema:** \`ikariam-focused-model-candidate-v1\` is a separate standalone
worksheet JSON, not a modification to report case storage schema v1. It
requires exact field sets: \`schema\`, \`source_class\`, \`case_id\`,
\`case_updated\`, \`battlefield\`, \`round_id\`, \`round_number\`, \`phase\`,
\`side\`, \`line\`, \`candidate_label\`, \`assumptions\`, \`predictions\`.
Each predictions entry is exactly
\`{pos,unit,wave,count,hp,deaths}\`; one entry per canonical physical position
in strict order, all null numeric defaults. Candidate JSON is bounded
to 128 KiB UTF-8; names/labels to 120 characters and assumptions to
2000 characters. Whole-case, wrong-side, wrong-line, wrong-phase,
round-number, wrong-geometry, changed-case-revision, forged source class,
duplicate/extra/missing physical positions and invalid numbers all fail
closed. All CSV text is spreadsheet-formula escaped. The candidate editor
and result are cleared when selected case, revision, round, side or line
changes. Saved original report case JSON remains unchanged.

For authoritative source/engine comparison, still use the existing local
screenshot-bound CLI pipeline and independently verified physical-slot
bindings. The browser is for **descriptive hypothesis triage only**; a
small numerical difference is not empirical proof of an algorithm.
