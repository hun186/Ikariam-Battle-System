# Mechanics evidence register (`paper-2020`)

The repository PDF, *Ikariam battle system* (61 pages), is empirical/a-posteriori research—not an official or complete specification. Page numbers below are PDF pages. `DOCUMENTED` means explicit in the paper, not Gameforge-confirmed or current.

## Confidence

- **DOCUMENTED** — clear formula or repeatable worked observation in the paper.
- **EMPIRICAL** — reports support it, but it is not established generally.
- **HYPOTHESIS** — proposed explanation with competing possibilities.
- **UNKNOWN** — explicitly open/very open, or insufficient for an a-priori algorithm.

## Rule register

| Rule ID | Description | PDF section/page | Confidence | Implemented? | Regression test? | Unresolved assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| FORM-STD-001 | First/second order `[6,4,2,1,3,5,7]`; third `[5,3,1,2,4]`; flanks `[6,4,2;1,3,5]`; balloons `[1,2]`; anti-balloon `[2,1]`. | §1.2 p.3; §2.2 pp.8–9 | DOCUMENTED | Yes | Yes | Further battlefield sizes are not encoded. |
| FORM-NONSTD-001 | Non-standard renumbering occurs and is inferred a posteriori. | §2.3 pp.10–11 | UNKNOWN | No; strict stops | Yes | No a-priori selector. |
| AM-ROW-001 | A firing line is an `n × m` attacking matrix, one firing unit per populated cell. | §2.1 pp.4–6 | DOCUMENTED | Yes | Yes | Mixed-unit rows are open (p.60). |
| AM-MOD-002 | Row `i` targets damage-position `i mod q`; zero means `q`. | §2.1 pp.5–6 | DOCUMENTED | Yes | Yes | Retargeting after destruction is open. |
| AM-VECTOR-003 | Matrix rows sum to a target-hit vector in standard-renumbering order. | §2.4 pp.11–12 | DOCUMENTED | Yes, sparse trace | Yes, steam-ram/catapult examples | Column permutation only has the paper’s stated scope. |
| DEPLOY-001 | Slots fill in standard order; capacity and reserve are distinct. | §2.2 p.9; §4.3 pp.19–20 | DOCUMENTED | Yes | Yes | Multiple unit types sharing a line are unresolved. |
| DMG-INT-001 | `d=(A+u)-(a+v)`; level-5 attacker ×1.2; level-5 defender +2 armor. | §3.1 pp.15–16 | DOCUMENTED | Yes | Yes | Other Hephaistos levels unsupported. |
| DMG-ROUND-002 | “Appropriate approximation” varies (13.6→14; 15.6→15). | §3.1 p.16 | UNKNOWN | Explicit policies; experimental uses floor | Yes | No general selector. |
| RR-001 | Between rounds, same-wave `ds=D/N*s`; waves remain separate. | §4.3–4.3.1 pp.18–20 | DOCUMENTED | Yes | Yes | General fractional allocation unknown. |
| RR-INT-002 | Sub-unit integer damage follows standard order until represented. | §4.3.1 p.20 | EMPIRICAL | Deterministic remainder policy | Yes | General upper/lower rounding unknown. |
| SR-001 | Damage can redistribute within each target slot after one line, before the next. | §4.4–4.5 pp.21–25 | EMPIRICAL | Phase/event reserved; not applied | Strict boundary | Paper shows cases where SR does not occur. |
| IR-001 | Damage can redistribute after each shot; rocket/steam-ram example uses 439. | §4.6 p.25 | EMPIRICAL | No | Strict boundary | Trigger/rounding not generalized. |
| KILL-TYPES-001 | 1-, D-, P-, I-, IR/PIR-, M-kill are a-posteriori categories. | §5 pp.26–27 | EMPIRICAL | Experimental I-kill event only | Yes | Author conventions, not official mechanics. |
| KILL-SELECT-002 | Kill type cannot be predicted generally. | §5.2 onward, pp.29–46 | UNKNOWN | Strict returns `inconclusive` | Yes | Core blocker to exact simulation. |
| CHRONOLOGY-001 | Demonstrated order includes third→SR→second→SR→first. | §4.5 p.24 | EMPIRICAL | Not generalized | Documentation only | SR is conditional; full chronology unknown. |
| TARGET-PRIORITY-001 | Rocket derivation uses priority order; third line does not fire at second. | §2.5 pp.12–15; §20 p.60 | EMPIRICAL | Minimal compatible-line data | Matrix tests | Complete priorities/transfers unknown. |
| WAVES-001 | RR is isolated by arrival wave even when displayed reserve aggregates it. | §4.3 pp.19–20 | DOCUMENTED | `wave_id`, per-wave state | Engine tests | Multiple-wave deployment needs more evidence. |
| HEAL-001 | Tender cures 200 life/round; doctors cannot handle steam giants. | §4.3 p.19; §20 p.60 | EMPIRICAL | No | No | Doctor amount/selection/chronology incomplete. |
| DURATION-001 | Damage intervals compound in long battles. | §17 pp.56–59 | UNKNOWN | No | Strict boundary | Paper says data/analysis are insufficient. |
| ACCURACY-001 | Accuracy may affect IR, D-kill columns, or Am formation. | §18 p.60 | HYPOTHESIS | No | Strict boundary | Counterexamples exist; effect unknown. |
| RETARGET-SLOT-001 | Redistribution after a target slot is destroyed. | §13, §19 pp.47,60 | UNKNOWN | No | Strict boundary | No reliable algorithm. |
| RETARGET-LINE-002 | Transfer after a target line is destroyed. | §13, §19 pp.47,60 | UNKNOWN | No | Strict boundary | No reliable algorithm. |

## Phase A implemented scope

The engine implements deterministic deployment, capacity/reserve/wave state, standard Am targeting, decomposed integer damage, persistent slot damage, RR, and machine-readable events. Strict mode stops before casualty calculation because `KILL-SELECT-002` affects every supported matchup, returning deployment plus an `unsupported_mechanic` event.

The versioned unit subset is sulphur carabineer, hoplite, swordsman, barbarian knifeman, rocket ship, and steam ram. Values are tied to PDF examples and are **not 2026/current game data**.

### Explicit experimental policy

`EXP-I-KILL-001` pools each slot’s damage, floor-rounds per-hit damage, kills `total // hit_points`, and preserves the remainder. Every such response lists the assumption. This exercises the complete engine/API/UI; it does not claim Ikariam chose I-kill.

## Review coverage

Text was extracted from all 61 pages for navigation. Figures accompanying Am/deployment (pp.4–15), RR (pp.18–21), SR (pp.22–25), IR (p.25), kill examples (p.26 onward), very-open problems (pp.47–59), and the open-question summary (p.60) were reviewed. Tests encode stated formulas/vectors rather than image pixels.
