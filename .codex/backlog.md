# Backlog

## Accepted Items
| ID | Priority | Status | Item | Why deferred | Completion condition | Dependency |
| --- | --- | --- | --- | --- | --- | --- |
| BL-001 | High | Accepted | Force Solver / Minimum Winning Army | User explicitly excluded Function B from Phase A | Search evaluator repeatedly calls public simulator and returns a tested minimal/winning composition without duplicating combat rules | Calibrated Phase A oracle and declared search space |
| BL-002 | High | Accepted | Town-wall participation and garrison-limit battlefield escalation | Explicitly excluded from this focused correction; required for complete city battles | Evidence-backed wall deployment/target/damage rules and battlefield-size escalation tests | Phase A calibration and larger battlefield profiles |

| BL-003 | High | Accepted | Naval battlefield geometry/combat and shared naval report UI | Land mechanics were calibrated first; naval units exist numerically but battlefield execution remains reserved | Evidence-backed naval geometry and line/target/weapon rules execute through the same simulator/report framework | Phase A calibration |
| BL-004 | High | Accepted | Unit economy profile and General Score battle statistics | Current unit profile has combat numbers but no verified production-resource cost basis | Cost basis is sourced per player unit; General Score derives as resource total / 50; upgrades/Forge/buffs do not affect it; battle summary reports score lost/destroyed | Verified economy data |
| BL-005 | High | Accepted | Barbarian Village/Fleet profiles and generators | Barbarian counterparts have distinct stats/rules and village walls depend on scenario parameters | Separate barbarian land/naval unit profiles, zero resource/General Score basis, no upgrades/miracles/batches, and evidence-backed village/fleet generators | Barbarian evidence + wall model |
