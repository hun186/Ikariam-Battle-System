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
