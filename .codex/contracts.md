# Interface Contracts

`simulate` input contains profiles (`mechanics`, `unit_stats`, `workshop`, `forge`, `support`, `targeting`, `battle_end`), policy, `land-mini`, max rounds, and armies with side `forge_level` plus `units[{unit_id,quantity,wave_id,attack_upgrade,armor_upgrade}]`. Upgrades are non-negative integers; same unit on one side must use consistent upgrades. Strict unsupported behavior is inconclusive; experimental assumptions have stable, unique IDs and only report applied policies. Snapshots keep `total` and add `battle_sustaining_total`/`battle_sustaining_remaining`; termination is a separate event and never fabricates casualties.

`GET /api/simulate` returns profiles, verified-through metadata, supported/reserved battlefields, complete units with domain/role/support effect, Forge levels and support capacity. `POST` returns result or 400 validation error. Packaged data is the registry authority; UI has no duplicate list.
