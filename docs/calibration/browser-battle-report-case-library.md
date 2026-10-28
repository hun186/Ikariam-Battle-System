# Browser battle-report case library — local-only initial implementation

Starting from owner-merged PR #97 `main` `15424a51775bb5a8d03067c8731dd3fab7e304e4`. Adds a dedicated web UI at `/battle-cases.html`, linked from the simulator header. The editor and reader render **the same actual battlefield metadata-derived slot geometry**, including sides, physical slot positions, Second/Third, Flank, Air and Reserve. Available Land and Naval geometries derive from `GET /api/simulate` (not an invented separate layout truth).

## User workflow

Create/choose/delete a case (up to 50 per browser), select battlefield, name and note; add/remove numbered captured rounds in arbitrary order (real round one not required); choose R-end or next prefire phase, enter source screenshot notes. Click any formation tile to edit unit, wave, visible count, visible slot HP %, observed round deaths; switch Read/Write modes without changing battlefield layout. Use the Reserve section to add/edit/delete a reserve wave and its declared HP source. Download case JSON and import it on another computer to preserve original captured transcriptions. The exported JSON uses compact serialization so even long round-by-round calculation notes do not inflate through pretty-print indentation. Import and export share a single **64 MiB UTF-8 byte** limit enforced by the same model; download is rejected with a visible message rather than producing a file that cannot be restored. The model also rejects oversized external files prior to JSON parsing. Cases exceeding the ceiling must be separated into smaller cases. A large multi-round, 100-Reserve-per-side, non-ASCII backup round-trip is covered by Node regression tests.

### Reserve HP evidence constraint

Game report screenshots DO NOT display Reserve HP. Each new Reserve row starts with `hp=100`, `source=assumed_full`; that is **NOT** an observed screenshot measurement. All default Reserve rows are tagged `預設 100%（未觀測）`. For the **earliest captured round in a case** (which may be R80 or another mid-battle round), check the explicit per-side `baseline_confirmed` only after the user has ensured those first-snapshot Reserve ships are full HP. Without the confirmation a case remains `REVIEW_REQUIRED` for reliable initial HP analysis. If a user has independently and precisely derived other Reserve HP, switch to `calculated` and enter the integer percent plus at least 20 characters describing concrete calculation evidence. This remains *external computation*, not Gameforge screenshot evidence and requires independent review. A 100% assumption may never be modified while keeping `source=assumed_full`.

Dynamic ordering: adding a newly earlier captured round re-evaluates the case's first-round confirmation gate. Formation slots are visually observed HP, unrelated to Reserve hidden HP. The validator bounds positive/negative and float/bool percentages, slot identities and per-case length; imported JSON must match v1 contract and battlefield metadata. Import creates a new case ID and does not silently overwrite existing data.

### Storage and integrity limitations

Browser `localStorage` only, not a server database, account sync or persistent Vercel state. Always export JSON before browser cleanup/device switch; keep original screenshots privately outside GitHub. No screenshot upload, original-image authentication, official damage/Accuracy/healing inference or production simulation data ingest. The research archive's local SHA-256 binder and stage-delta tools remain separately available; this UI does not falsely claim screenshots are authenticated by typing a source note. Future tasks: optional authenticated persistent storage and schema-mapped evidence export, after explicit scope review.

Static page is duplicated at root and `public/` to support ASGI local routes and Vercel static serving, matching simulator's existing root/public index parity. `/battle-cases.html` and `/battle-cases-model.js` have explicit rewrites before SPA catchall. Regression tests verify static parity, ASGI routes and Node JS model provenance rules/syntax (when Node available). Real-browser visual interaction not yet independently verified by hosted tests.

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
The successful Hosted workflow uploads synthetic desktop/mobile screenshots
for seven days. The workflow result must be checked before calling browser
acceptance passed. This does not verify official battle mechanics or game-source
authenticity.

For local execution install uvicorn and Python Playwright with Chromium,
start `uvicorn asgi:application --host 127.0.0.1 --port 8871`, then run
`python tools/report_case_browser_e2e.py --base-url http://127.0.0.1:8871`.
