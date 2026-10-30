# Existing battle analysis → browser catalog, 2026-10-30

The authoritative historical research fixtures are unchanged in
`tests/fixtures/reverse_engineering`. `battle-cases-history.json` is a
**source-tagged, lower-trust projection** into existing browser report-case v1
records, NOT authenticated original Gameforge battle reports and NOT simulator
output. Main display starts with these 14 cases when browser storage is empty
and no first-import marker exists. The user may manually restore missing
historical cases, without changing local edits, by clicking
**載入之前 PR 的研究戰報**. The stable `research-...` IDs prevent duplicates.

## Imported sources (14 browser cases)

- One **same battle**: user Land Forge5 R1 and R80–R89, with explicit missing
  R2–R79 (no interpolation). R1 transcribes seven Axe positions and visible
  carabineer counts; R80–R89 transcribe owner-confirmed seven-slot casualty
  labels and only the survivor values individually present in source.
- A **different fight**: 400 Slinger/Attack24/Forge5 reinforcement in R77;
  records R76–R80 visible Barbarian first/second position transcriptions.
- Crispi R1 and Reikjavikas R1: source per-slot casualty counts, not guessed
  unit survivor HP/count.
- Three separate Barbarian Deckwrecker vs player Ram armor-grade fights:
  grade3/15 user-stated per-slot deaths and grade19 aggregate deaths/bars. Their source fixture does **not establish exact game-round timing**; the v1 schema requires one round, so its R1 tab is expressly documented as a catalog indexing placeholder rather than the actual observed R1. No Ram physical slots are populated, even for verbally reported per-slot losses, to avoid assigning them an invented Round1.
- Three separate player Fast Boat versus player Carrier R1 fights:
  aggregate Carrier deaths only.
- Four separate Barbarian/Player air-counterpart engagements:
  only source aggregate outcomes and unplaced HP bars.

Every case has an exact source fixture path, independent deterministic IDs and
round identifiers, `baseline_confirmed=false`, no Reserve HP, no fictitious
Wave identity. Individual deaths must not be invented from aggregate totals;
unknown positions are unentered, not zero. Original screenshots remain outside
the repository and source notes alone do not authenticate source origins.

## Lifecycle and limitations

The bundle lives under root and `public/` to support both ASGI local static
serving and Vercel static hosting. A first visit with empty browser data seeds
once; after the user deletes entries, the migration marker prevents silent
resurrection. Button re-import of missing IDs is explicit. A validated local
case with the same ID, even if edited, always wins. Entire bundle is
validated first; 50-case limit, case schema and battlefield metadata are
enforced before mutating storage. Failed quota writes do not swap the live
in-memory case array. No server-side user case database is introduced.

### Invalid saved-data protection (Codex P2 #4421688617)
Only a genuinely empty **original raw localStorage array** may cause automatic
historical seeding. If any raw record fails validation or exceeds the 50-entry
view limit, all storage writes are locked to preserve the recoverable original
bytes: no automatic seeding, manual restore, or editor save may overwrite them.
A browser notice instructs the user to back up and repair the source JSON.
An all-invalid raw array, a mixed valid/invalid array, manual import attempts
and reload byte-for-byte preservation are covered by real Chromium acceptance.

## Research case scope and anti-fabrication guard (PR #118 follow-up)

Legacy v1 JSON without case-level `research` remains valid, unchanged and
**unclassified**; it is never silently promoted to a complete report. New
browser-created cases default to partial observation. Optional `research`
consists of `kind` (`partial_observation`, `research_summary`, or user-claimed
`full_report`) plus six source-scoped fields (`objective`, `observed_scope`,
`known_conditions`, `hypothetical_inputs`, `unknown_fields`,
`confirmed_absences`), each bounded to 2000 characters. An empty field means
"not documented", not absence or authentication. All fields survive JSON
backup and import. Existing historical IDs continue to win against re-import,
so existing local edits remain untouched.

All 14 bundled research cases were given only existing fixture-grounded
annotations: 4 partial Land observations and 10 aggregate Naval summaries.
The Swordsman flank calibration fixtures (2026-06-25/2026-10-02) are **not
among these 14 imports**; the front-line 350 Hoplite scenario parameter in
the June source is a simulator hypothesis, not automatically an independently
verified original Gameforge front line. Only R76 Slinger-not-yet-deployed is
annotated in `confirmed_absences`, strictly for that unit and turn. No empty
tile is marked as an absent unit.

The pure `researchEvidenceGate` rejects automatic **global/whole-battle
calibration in every case**, including user-labeled `full_report`, because
neither self-reported completeness nor typed fields authenticate source images
or missing cross-line interactions. At most, typed partial observations may be
compared in a focused conditional research workflow; that does not assert
other lines are causally irrelevant. Summary-only records can support
descriptive totals only. There is NO currently wired simulator auto-calibration
from the browser case library, and this guard must be enforced by any future
consumer, not inferred from old `readiness` entry-progress messages.
