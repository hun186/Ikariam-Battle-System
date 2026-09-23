# Interface Contracts

## CONTRACT-001 `simulate`
Input: `profiles` (`mechanics`, `unit_stats`, `workshop`, `forge`, `support`), `policy`, `battlefield`, `max_rounds`, and each army’s `workshop.attack_level/armor_level`, `forge_level`, and `units[{unit_id,quantity,wave_id}]`. Integers reject booleans/strings; Workshop is any integer >=0; Forge is 0..5. Same `(unit_id,wave_id)` rows aggregate.

Output: profile IDs, policy, status/outcome, rounds/casualties, positioned initial/final state, events, structured assumptions and warnings. Strict unsupported behavior is `inconclusive` without fabricated casualties. Experimental assumptions have stable `EXP-*` IDs.

## CONTRACT-002 HTTP
`GET /api/simulate` returns authoritative UI metadata: profiles, profile verification metadata, units/domain/role/support flags, Forge levels and derived support capacity. `POST` projects CONTRACT-001; valid results 200, validation failures 400 `{error}`.

## CONTRACT-003 packaged data
Resources are loaded with `importlib.resources`; unit fields include per-field confidence/source/sources/cross-check status. Missing values remain null and cannot be simulated. Mechanics and numerical/rule profiles remain separate.

## CONTRACT-004 calibration fixture
Game version, scenario, round, and observed slot casualties/damage%/life% are parsed independently of winner expectations. Display percentage intervals preserve report-rounding ambiguity.
