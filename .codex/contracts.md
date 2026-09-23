# Interface Contracts

## CONTRACT-001 `ikariam_battle.simulate`
- Status: Draft Phase A; authority: `models.py`, `engine.py`, tests.
- Input: `Scenario` or mapping with `ruleset`, `policy`, `battlefield`, `max_rounds`, optional `effects`, and `attacker/defender.units[]` containing `unit_id`, `quantity`, `attack_upgrade`, `defense_upgrade`, optional `wave_id`.
- Output: ruleset/policy, status/outcome (including `inconclusive`), rounds completed, casualties, initial/final state, round snapshots, events, assumptions, warnings.
- Validation failures raise `ScenarioError`/`ValueError`. Same input and data version is deterministic.

## CONTRACT-002 `POST /api/simulate`
- JSON projection of CONTRACT-001. Success 200; invalid payload 400 `{error}`. `GET` returns usage and supported units. `/api/simulate` is retained for ASGI/Vercel.
- New optional fields may be additive; breaking schema changes require an explicit version/migration.

## CONTRACT-003 unit registry
- `data/units/<ruleset>.json`; stable id, display name, battlefield class, attack/armor/HP, slot capacity, ammunition, target priority, properties, upgrade semantics, provenance, ruleset version.
- Missing unit ids are rejected, never guessed.
