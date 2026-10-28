# Prospective Tender priority: is Balloon Carrier healed after other ships?

**Issue #73, research only. New owner-provided qualitative hypothesis on 2026-10-27, not original screenshot evidence.** The user observed that with Tender capacity insufficient, carriers may appear to change HP gradually over successive rounds, and speculated that carriers are late in the Tender's healing priority. This observation does **not** independently confirm actual target order or even whether HP-bar motion was caused by insufficient healing versus incoming damage, Reserve replacement, or display rounding.

Existing PR #84/85 synthetic Tender probes compare ram priority, steam ram priority and proportional partial allocation, but their synthetic patient rows are not a controlled carrier-versus-other-wounded-ship observation. This new tool compares independent **hypothetical** carrier-priority classes, without pretending to run Gameforge:

- `noncarrier_before_carrier`: proportionally allocate finite healing across all eligible noncarriers first; carriers receive only leftover capacity.
- `proportional_all`: allocate across all eligible wounded waves by wound volume.
- `carrier_before_noncarrier`: deliberately opposed hypothetical priority as a negative control.

Each within-group allocation uses deterministic largest remainder for integer HP and conserves the configured finite healing capacity. It does not modify the simulator's existing `UNKNOWN-TENDER-HEALING-ALLOCATION` guard. Inputs have `record_kind=hypothetical_wound_input_not_game_observation` and must be manually supplied; all GitHub fixtures are invented.

Invented local-only example — these numbers are **not** official ship HP, per-Tender HP or measured game data:

```json
{
  "schema": "p0_naval_carrier_late_tender_priority_v1",
  "record_kind": "hypothetical_wound_input_not_game_observation",
  "carrier_unit_ids": ["balloon_carrier"],
  "healing_capacity_hp_levels": [0, 40, 80, 100, 140, 160],
  "wounded_waves": [
    {"unit_id": "ram_ship", "wave_label": "W1", "eligible_for_tender": true, "wounds_hp": 80},
    {"unit_id": "balloon_carrier", "wave_label": "W1", "eligible_for_tender": true, "wounds_hp": 60}
  ]
}
```

Run: `PYTHONPATH=. python tools/research/p0_naval_carrier_late_tender_priority.py --input private-hypothesis.json --output-json private-priority-comparison.json`.

At invented capacity 40, the late-carrier hypothesis predicts 0 HP assigned to the carrier, whereas proportional and carrier-first allocate some carrier healing. When capacity exceeds total other-ship wounds (80), the carrier-last candidate starts assigning carrier healing; at or above 140, all candidates converge. This is a *discriminating-capture threshold*, not a claim about official Tender repair numbers or battle physics.

## Actual Gameforge evidence needed

Capture R1-end and R2-prefire (prior to R2 attack) **for every visible damaged ship group**, with carrier and noncarrier groups simultaneously wounded. Keep battles' attacker/defender composition, Forge, Workshop, reinforcement timing, same Wave/slot labels, losses and visible unit counts documented. Repeat across under-capacity and sufficient-capacity Tender quantities while recording exact observed bars, Reserve transitions, each wave's wounds and support vessel count. Screenshots should show stage timing clearly, not just post-attack rounds. PR #95-96 local byte-gating plus conditional integer HP intervals can help screen captures without authenticating them independently.

If noncarriers consistently approach full HP while carriers receive little/no measured prefire HP restoration, across controlled capacity thresholds, that would favor (but not prove) carrier-late priority. If all types gain proportionally it favors proportional healing. If a carrier appears to lose HP between phases, separate fresh enemy damage, wave replacement and UI bar semantics before drawing any allocation conclusion.

**Never report owner conjecture, model outputs, or self-entered wave HP as authenticated Gameforge evidence.** No production damage formula, Tenders' official allocation order or Heal/RR chronology is changed by this research-only comparison.