# Land Barbarian battle — verified rounds 80–89, source casualty / reserve / displayed HP inverse research

> **Research-only, source-grounded, not a Gameforge combat-rule specification.** Created 2026-10-14 for [Issue #71](https://github.com/hun186/Ikariam-Battle-System/issues/71). Keep independent of NAVAL Draft PR #69 and its Accuracy/overkill calibration. Do not merge or change the production battle engine without explicit authorization.

## 2026-10-15 CROSS-WEAPON ACCURACY / FRESH-HIT CONCENTRATION / R77 18-TICKET HYPOTHESIS

Owner requested a stricter falsification test of the earlier **R77 Knife +6×3 =18 extra full-shot equivalents** matching the partially filled Axe physical2 hypothetical **≥18 unconsumed/readdressable tickets**, comparing **20% Slinger accuracy** against **70% Sulphur Carabineer accuracy**, **fresh HP1120 Axe hit-to-kill six vs two**. This is **two DISTINCT owner battles**, Slinger ATT24 Forge5 R77–R80 vs Gun ATT11 Forge5 R1–R89, not direct experimental replication.

### Source stats, candidate Accuracy selection, and why occupancy alone is insufficient

| Source primary weapon / target | Accuracy (packaged) | Forge5 full damage | Target HP | Fresh hits-to-kill |
|---|---:|---:|---:|---:|
| Sulphur Carabineer Attack11 → Axe | **70** | **710** | 1,120 | **2** |
| Sulphur Carabineer Attack11 → Knife | 70 | 730 | 360 | 1 |
| Slinger Attack24 → Axe | **20** | **187** | 1,120 | **6** |
| Slinger Attack24 → Knife | 20 | 207 | 360 | 2 |

These are project packaged weapon Accuracy and owner-confirmed Forge levels, **not proof of actual Gameforge accuracy algorithm**. Project experimental `ikariam_battle/accuracy.py` (`EXP-ACCURACY-CONCENTRATION-001`) chooses another healthy target until the most-injured surviving individual's remaining HP% `<=accuracy`, then focuses. A healthy Axe after one 710 gun hit has **36.6% HP remaining**, already below70: 14 direct hits into a fresh pool can pair and kill **7 Axe**. A healthy Axe after 187 Slinger hit has **83.3%** and needs **five** hits into the *same* Axe before remaining HP `<=20%` (sixth kills). Knife after one207 Slinger hit has **42.5%** left (>20), so one hit alone does not switch the experimental focus rule. The project is **explicitly experimental and current game's code is unverified**. The 2020 AT Barbarossa/Xanto paper §18 says the author's earlier Accuracy hypotheses had counterexamples and offered several competing conjectures (IR trigger, number of D-kills, AM grouping): https://www.scribd.com/document/638484147/ikariam . Older Gameforge help describes Accuracy in terms of hit **concentration**, not a proven Bernoulli miss probability; independent GitHub forum 2024 speculation about random hits is not an actual algorithm specification.

**Executable individual-selection falsifier:** Fresh 21 Axe with14 actual gun hits and experimental Accuracy70 ⇒ **seven killed**. Fresh 50 Knife with49 actual Slinger hits at Acc20 ⇒ **zero gun kills**; even 55 full hits into 50 Knife ⇒ **only five gun kills** before hypothetical wall, far short of owner's **19 deaths**. Fresh 19 Axe with49 Slinger hits under this selection ⇒ **zero gun kills** before walls, whereas owner sees two Axe deaths. Thus the simplistic experimental "keep spreading until HP% below Accuracy" model **CANNOT reproduce R77**, even if Knife receive six extra tickets. It must not be installed as official Gameforge targeting solely because it explains musket 14→7.

### Joint R77 full seven-slot inverse accounting, NOT just 18-shot numeric matching

All following lower bounds require owner-EXPECTED but UNVERIFIED **ALL full HP before R77**, **floor(mean surviving HP%)** UI assumption, Forge5 primary damage187 Axe /207 Knife, at most seven **one-shot-kills** from walls, max **350 FULL primary source tickets** (7 deployed Slinger groups×50) with unknown ammo. **Shots** are gun-like full damaging primary tickets; actual AM addresses don't guarantee they fired. Source screenshot fronts: `Knife31(-19)/56, Axe17(-2)/81, Axe49(-1)/81, Axe49(-1)/81, Axe50(-0)/83, Knife31(-19)/56, Knife31(-19)/56`.

| Physical Slot | Source AM | Minimum loss of total original HP (dead + survivor injuries) | Minimum full gun tickets IF each death-eligible slot gets ONE ideal FULL-HP wall kill, no overkill waste | Minimum full gun tickets if fresh-health individual D-kill and excess 2-hit/6-hit overkill is LOST |
|---|---:|---:|---:|---:|
| 1 Knife | 49 | 11,639 | **55** | **60** |
| 2 Axe (starts19) | 49 | 5,668 | **25** | **25** |
| 3 Axe | 49 | 10,999 | **53** | **53** |
| 4 Axe (center) | 56 | 10,999 | **53** | **53** |
| 5 Axe (no deaths) | 49 | 8,961 | **48** | **48** |
| 6 Knife | 49 | 11,639 | **55** | **60** |
| 7 Knife | 49 | 11,639 | **55** | **60** |
| **Seven-Slot Total** | **350** | **71,544** | **344** | **359** |

The HP-only minima allow FULL injury pooling/reuse with **ZERO overkill loss**, do NOT independently reproduce death counts or near-uniform individual wounds. Illustrative integer HP-only `350-ticket` assignment physical L→R **[55,27,54,56,48,55,55]** (vs AM **[49,49,49,56,49,49,49]**) has delta **[+6,−22,+5,0,−1,+6,+6]** and can fit each **HP-loss interval** if each death-eligible cell receives one wall one-kill of some HP amount up to a full victim. This witness does **NOT** construct 19 Knife casualties and all seven HP bars via any actual Kill Type. In particular **the 18 Knife extra shots are NOT a complete or unique redirect pattern**: another Axe cell physical3 also needs >=4 tickets above baseline even with a full wall one-kill, so the shortage can't be attributed solely to an 18-to-three-Knife transfer without addressing other slots.

For strict **individually focused D-kill**, every **full Knife kill from two207 hits wastes `414−360=54` HP**; every full Axe kill from six187 hits wastes `1122−1120=2` HP. If a Knife cell has19 observed deaths and 1 wall kill, then 18 gun killed Knife create **at least `18×54=972` lost overkill**. Need `ceil((11639−360+972)/207)=60` full hits per Knife cell; not55. Across seven slots, best case with one ideal wall 1-kill in each nonzero-death cell => **359** full gun hits, above max350. Furthermore, permitting **ANY distribution** of up to seven ideal full-HP wall one-kills over ALL targets (even unrealistic physically), an exhaustive **bounded wall allocation** integer search still requires **at least353 full primary hits**. This is a rigorous conditional refutation of **"reroute tickets alone + fresh individual D-kill with discarded overkill + 350 primary hits + seven walls"**. The game can still work under weaker assumptions: pre-R77 old HP state, alternate weapon/ammo, different bar semantics, wound transfer/overkill recovery (P/IR), extra sources, or different wall behavior.

The new case even pushes AGAINST simple **fully pooled damage converted directly into deaths by `floor(total_damage/HP)`**: a Knife Slot receiving55×207=11,385 full damage would trivially allow **31 Knife HP360** to be consumed, whereas **only19 deaths total** are observed; some damage must be retained as survivor wounds (or be lost by overkill), not every pooled HP unit converted to death. Thus the competing models are **not** just D vs one naive full-slot HP floor-kill. Kill count and surviving HP must be fitted *together*.

### The small target counts do NOT prove "no more targets to receive shots"

At R77 Axe physical2 **19 full Axe** would collectively require **19×6=114** perfectly focused187-damage primary hits to kill all, far above default **49** AM addresses. In the earlier musket fight R84 center Axe start21 and14 nominal gun addresses would need **21×2=42** complete gun attacks to kill all, also >14. Neither potential redirect is forced by literal empty-target exhaustion. The candidate trigger must be a different rule (source-row grouping, Accuracy/focus, effective target-capacity metric, slot HP threshold, AM model limitation, SR/IR/RR, etc). The previous numerical18 =6×3 is an intriguing but **non-identifying coincidence** without additional controlled screenshots.

**Critical follow-up experiments:**
1. Slinger Axe cell **19 vs 25 vs 50** full HP, fixed source 7×50 and Forge5, record same-round all seven Slot casualty and BAR values. Changes in **AM addresses** versus **individual hit distribution** should be differentiated.
2. Fix one Axe cell at19 and vary source primary weapon Acc20 vs Acc70 *without changing effective per-hit damage* if controllable (otherwise cannot attribute differences uniquely to Accuracy because weapons differ in damage/hits-to-kill).
3. Vary slinger ATT level around24 while preserving Forge5/formation size; hits-to-kill Axe may cross a threshold only when `ceil(1120/damage)` changes.
4. Capture source ammunition and R76 pre-hit bar to validate **350 effective primary shots and initial full HP**, without which the numerical counterexamples remain conditional.
5. Never hardcode an inferred 18-hit diversion nor apply an unverified Kill Type to production engine.

Executable read-only model `tools/research/land_cross_weapon_accuracy_am_reallocation_probe.py`, tests `tests/unit/test_land_cross_weapon_accuracy_am_reallocation_probe.py`. Source fixture values are unchanged; the exact Gameforge Accuracy, D/I/P/IR selector and redirected target groups remain UNKNOWN.

## NEW SEPARATE 400-SLINGER CASE — R77–R80: COUNT CONSERVATION, INJURY POOLS, FRONT→REAR COLLAPSE (2026-10-15)

**This is ANOTHER battle**, not the full-Axe R1→R89 Forge5 musketeer battle above. Four owner-supplied screenshots (20261014-170017, -170407, -170814, -170830.png) of a **400-Slinger attack-workshop Lv24** player army: 7 second-line slots×50=350 in battle, reserve50, 7 defensive wall sections. Owner says Barbarian Axe+Knifeman targets before R77 attack *should have been* 100% HP (**hypothesis, not verified exact pre-round HP**). **Owner explicitly confirmed THIS Slinger battle also had active Forge Lv5** (2026-10-15 follow-up), independently of the other Carabineer fight. Exact primary ammunition status and deployment time (late reinforcement vs long battle) unknown. Screenshot source is in conversation, not hosted GitHub. Provenance fixture `tests/fixtures/reverse_engineering/land_barbarian_slinger400_rounds77_80_20261015.json`.

| Observed round | Barbarian frontline physical L→R survivors (-this round deaths) | Owner-confirmed surviving front HP% | Frontline deaths |
|---|---|---|---:|
| R77 | Knife31(-19); Axe17(-2),49(-1),49(-1),50(-0); Knife31(-19),31(-19) | 56,81,81,81,83,56,56 | **61** |
| R78 | Knife0(-50); Axe11(-4),48(-2),47(-3),48(-2); Knife0(-50),0(-12) | 0,63,62,57,62,0,0 | **123** |
| R79 | Axe0(-4),39(-11),36(-14),39(-11) [four Axe positions] | 0,29,29,29 | **40** |
| R80 | Axe0(-50),0(-50),0(-14) [three positions] | 0,0,0 | **114** |

R80 Barbarian SECOND line, Axe Thrower `HP320/armor0`: four slots **44(-6)** and final one **12(-5)**, HP% owner-given **[65,61,61,65,61]** (29 dead, **188** survivors). R79 screenshot prior rear line 50×4+17 = **217**, visually full green bars; exact pre-R80 HP100% not numerically owner-confirmed.

### Exact count conservation: the strongest unconditional signal

- R77 frontline Knife 31×3 =93 alive, with **19 Knife in reserve**. R78 Knife deaths 50+50+12=**112 = 93+19**. All Knifemen disappear; per-cell prior positions cannot be matched one-for-one across slot refill and compaction.
- R77 Axe frontline survivors **17+49+49+50=165**. R78 Axe survivors **11+48+47+48=154**, precisely 11 fewer than R78 observed Axe deaths **4+2+3+2=11**.
- R79 Axe deaths **4+11+14+11=40**, so R78 154→**114**. R79 visible final **39+36+39=114**.
- R80 Axe deaths **50+50+14=114**: ALL remaining Axe die that round. These three physical slots show **refilled/compacted counts**, not individual continuity with prior positions 39/36/39.
- R79 Axe Thrower second-line **217**, R80 29 killed and **188** survivors. Exactly same wave count, while their HP bars fall to65/61/61/65/61.

### Current project source damage/AM controls, not verified Gameforge attacks

For **Slinger primary weapon base60, attack Workshop Lv24 => bonus24×5=120, before Forge180**, official community-packaged Axe HP1120/armor20, Knife HP360/armor0, AxeThrower HP320/armor0:

| Player Forge in this battle | Axe per full primary hit | Knife and Thrower per hit | Fresh Axe full hits to kill |
|---|---:|---:|---:|
| OFF Forge0 counterfactual | **160** | **180** | **7** |
| **ON Lv5, OWNER-CONFIRMED actual profile** | **187** | **207** | **6** |

Every source primary Slinger has **5 ammunition** and Accuracy20 (packaged stats). These FOUR screenshots do NOT independently prove the 350 deployed slingers each fired successfully or still had ammo at R77. No free assumption that Accuracy20 is random independent 20% hit success. `_shot_rows([50]*7)` current-project source AM for seven occupied physical enemy front slots produces **[49,49,49,56,49,49,49]** addresses (50 source rows modulo 7 target slots; the center physical4 receives an extra full source row of 7 shots); after collapse to four Axe slots (physical2–5) it produces **[84,91,91,84]** in physical order; at three Axe slots (physical3–5) **[119,119,112]**. These are model *addresses*, not confirmed original actual gun shot logs and do not by themselves predict casualties or source phase switch.

**Independent partial R77 clue, IF the target before R77 truly had zero wounds and no other HP transfer:** The physical5 Axe group starts50, ends **50(-0) at83% HP**. The current AM gives this physical5 slot **49** source addresses. Forty-nine complete hypothetical Forge5 slinger primary hits at187 give **9163 wounds**, `floor(100×(1−9163/(50×1120)))=83%` exactly. Forge0 would display86% under the same model, but is now a counterfactual only. Other R77 slots do NOT all fit independent groups of 49 or 56 hits, consistent with AM addressing/spill, old injuries, wall kills or unverified UI semantics. Owner has now **explicitly confirmed Forge5**; shot accuracy, target redirect and remaining ammunition are still unknown.

### 2026-10-15 user correction: R80 First→Second target transfer is ALREADY IN GAME HELP

**Owner correctly challenged an earlier false UNKNOWN.** The game's Art of Warfare in-game Help gives the **long-range/Second** source target formation priorities **First → Flank → Second**; when a higher-ranked formation is eliminated, later individual eligible attacks pick the next existing legal target line. The project ALREADY persists this as `ikariam_battle/data/rules/legacy-community-land-targeting.json`, both `priorities.second=["first","flank","second"]` and `metadata.target_transfer_contract.status="KNOWN_AT_FORMATION_CLASS_LEVEL"`: `"Later individual shots select the next listed formation after a higher-priority formation is eliminated."` The engine's `_resolve_volleys` explicitly examines target-class priorities while firing each shot and falls back after a class runs out of living targets, preserving a frozen within-class slot address book. An August 2026 Gameforge community guide also describes this ordering, and public Gameforge battleground Help sets the firing order; see https://forum.ikariam.gameforge.com/forum/thread/117436-guia-campo-de-batalha-e-suas-prioridades-2/ and https://gameforge.com/en-GB/games/ikariam-battlefield.html.

**For Slinger R80**, once the remaining **114 First-line Axes** are killed and **no Flank is present**, any **later effective Second-line Slinger shots** are expected by the KNOWN game target-priority rule to attack the enemy **Second-line Axe Throwers**. **The existence and direction of the formation-level fallthrough is NOT an unresolved new Gameforge damage mechanism**, and no speculative cross-line damage spill rule is required merely to reach Second-line enemies. The owner's displayed 29 rear Axe Thrower deaths and HP61–65% follow an established *legal target choice*.

**Actual unresolved research questions:** how many of the max350 potentially firing Slingers retain loaded primary ammunition; where in the firing/row sequence First became empty; exact original First vs later Second shot count; within-target-class Attack Matrix addresses, hit Accuracy, D/I/P/IR allocation, overkill and prior wounds; whether our hypothetical shot split **199 into First ×187 +151 into Second ×207** is real. That 199+151 is ONLY an aggregate HP-budget witness which assumes zero wall contribution and full damage, NOT a recovered Gameforge sequence. If the real front falls earlier/later or walls kill some Axes, a different split can fit. **Distinguish known formation-class fallthrough from unknown quantitative within-class damage redistribution.**

### Strong new R77 geometry clue: 49 vs 56 source shot rows can explain TWO neighboring HP bars

The current project row-major AM for seven 50-unit Slinger source slots has **50 rows × 7 shots**, cyclically assigned by damage priority. There are 7 full cycles of 7 target addresses plus 1 extra source row: six physical target cells receive **49**, central physical4 receives **56**. This is not an arbitrary per-cell average50.

Under the USER-SUGGESTED (unverified) full-HP start R77 and OWNER-CONFIRMED active Forge5 (187 per primary hit against Axe HP1120), test two R77 Axe cells without tuning ANY attacks:

- **Physical5** screenshot: **50(-0), 83%**. It receives 49 AM addresses ⇒ `49×187=9,163` wound points; if these spread among its fifty Axe survivors and no one is killed by the wall here, `floor(100×(1−9163/(50×1120)))=83%` EXACT.
- **Physical4, central** screenshot **49(-1), 81%**. This is the extra 56-address target ⇒ `56×187=10,472` wound points. Suppose gun wounds distribute near-uniformly over initial50 surviving during slinger phase; wall fires last and direct-kills one Axe carrying `floor(10472/50)=209` prior gun wounds (no wall ATK added), leaving49 at `10,472−209=10,263` wounds; `floor(100×(1−10263/(49×1120)))=81%` EXACT.

The Forge0 comparison is counterfactual only; owner-confirmed Forge5 allows the 49/56-shot source budget to fit both 83% and81% under the stated injury-distribution hypothesis. But the other physical slots in R77 are NOT yet reproduced with this simple model: e.g. Axe physical3 with49 addresses and one wall kill would show roughly83%, whereas owner reports81%; the 3 outer Knife slots with31(-19)/56% also need a different allocation and/or prior wounds. This supports studying AM attack reallocation or RR/SR/IR / Accuracy when a partially filled Axe slot physical2 has only19 units at start, not proof of a specific switch. Wall must NOT be assumed to one-shot the physical5 Axe cell in R77 because screenshot shows **zero** losses there.

### Owner-confirmed Forge5 exposes a possible R77 AM reroute constraint

The user explicitly confirmed Forge Lv5 was ACTIVE in this **400 Slinger / Workshop attack Lv24** battle; primary nominal hits therefore deal **187 against Axe HP1120/armor20, 207 against Knifeman HP360 and Axe Thrower HP320/armor0**. Forge0 is a *counterfactual control* only.

**Three identical Knife edge cells at R77:** each `31(-19), 56%` Knifemen started with50 units. If ALL were full HP360 at round start (the owner's expectation, NOT logged) and the display floors total living HP%, then `31×360×56..57%` means a surviving-HP interval **6,250–6,361**; HP removed from50 healthy Knives is **11,639–11,750** EACH. Standard seven-target AM source addresses **49** full Forge5 hits per knife cell, each207 → `49×207=10,143` HP, plus the **maximum** one full Knife HP360 from an assumed wall kill totals **10,503**, SHORT of the observed lower bound by **1,136**. To satisfy it using full slinger shot equivalents and **at most one full wall one-kill**, need at least `ceil((11639−360)/207)=55` damaging shots per Knife cell, **6 beyond its original49 AM addresses**. All three Knife cells have identical observed counts and bars, giving an aggregate potential deficit of **18 effective full-shot equivalents**.

**Part-filled Axe slot physical2 as possible source (NOT a verified redirect):** R77 Axe `17(-2),81%` means only19 Axes at start. Under the same fresh-HP + floor-bar assumptions, living HP after R77 **15,423–15,612**, vs starting `19×1120=21,280`; round HP loss **5,668–5,857**. Yet baseline AM assigns **49 Forge5 Axe hits ×187 =9,163 HP**. If no damage were discarded/overkilled/invalid and wall adds only nonnegative HP removal, at most `floor(5857/187)=31` complete shots could be consumed locally, so **at least18** of49 default shot-equivalents would need to go elsewhere. The number 18 matching 3×6 Knife deficits is suggestive evidence to TEST a shared AM source-row/slot-level spill mechanism, analogous to the earlier center Axe→outer Knife hypothesis. **It is NOT established that exactly18 attacks actually shifted**: source ammo, wasted damage, Accuracy, wall targets, previous injuries and target eligibility may break any of these assumptions. Other Axe cells in R77 still require explanation.

### Four-round reverse bounds if displayed percent = floor(mean living HP)

Define `p=floor(100×actual_remaining_HP/(n×unit_HP))`. Then for each slot `ceil(n×unit_HP×p/100) ≤ actual_remaining_HP ≤ ceil(n×unit_HP×(p+1)/100)−1`. Summing surviving Axe slots:
- End R78 154 living Axes: aggregate HP **104,431–106,151**.
- End R79 114 living Axes: aggregate HP **37,029–38,301**.
- Therefore net effective Axe HP removed R78→R79 is **66,130–69,122** if the snapshots represent comparable same-wave HP totals and no hidden HP influx/loss source. This includes DEAD Axes and further injured survivors; it is NOT only `40×1120`, nor a proof of a particular Kill Type.
- If exactly350 effective full Slinger primary shots all address the Axe first line R79, Forge0 max `350×160=56,000`. EVEN giving seven wall sections a generous upper bound `7×1120=7,840` one-full-health-Axe kills, total max **63,840**, **below the minimum 66,130**. Thus the **strict conjunction of Forge0 / primary shots / max7 one-Axe wall kills / zero other sources / no earlier HP-state bookkeeping / floor-average bars is falsified**. Forge5 is now CONFIRMED; Forge0 represents a rejected actual-case setting and remains only a historical counterfactual; remaining unknowns are source hit success, wall selection, HP-bar semantics, ammo and redistribution.
- **Confirmed actual Forge5** full primary Axe hit187 gives `350×187=65,450`; at least **680 additional HP disappearance** required from wall or another source at R79's minimum. Even a single effective independent wall one-hit-kill could make a budget feasible, subject to timing and actual victim HP.

**R80 first-line collapse and damaged rear line:** If the R79 second-line 217 Axe Throwers were genuinely 100% at end R79 (only visually inferred), initial total rear HP is `217×320=69,440`. End R80 188 survivors with shown bars65/61/61/65/61 imply end combined HP **37,825–38,422**, or **31,018–31,615 HP removed** from rear in R80. Add vanishing front Axe HP37,029–38,301 ⇒ **at least 68,047 HP** disappears across two enemy classes within R80; upper interval is69,916. This is not automatically all Slinger damage: walls may contribute direct kills, RR and attack order are unresolved.

**Owner-confirmed Forge5** primary nominal damage `187` Axe/`207` Thrower needs *at least* `ceil(37029/187)=199` attacks to finish frontline and `ceil(31018/207)=150` to account for rear loss, total **349** full damaging Slinger-primary attacks **IF walls contribute ZERO and rear starts full**; of the max350 model addresses, this is mathematically *barely feasible* only at the low ends of the allowed HP intervals, and depends on the **already-known Help Second-line target-priority fallthrough First→Flank→Second**, not an unknown *permission* to reach the rear. Exactly when the front disappears and how many shots remain still require reconstruction. Forge0 similarly requires `ceil(37029/160)=232` + `ceil(31018/180)=173` = **405** full hits, exceeding 350 WITHOUT an external wall source; Forge5 is established, but does not prove actual ammo, source order or target transfer.

**Stronger integer R80 feasibility witness (NOT Gameforge source-shot history):** There is even one completely integral Forge5 configuration within both screenshot HP intervals with **zero assumed wall contribution**: `199` full Slinger shots at187 into front Axe consume `199×187=37,213` HP (inside R79 front range37,029–38,301), then `151` shots at207 into rear Axe Throwers remove `151×207=31,257` HP, leaving `69,440−31,257=38,183` aggregate rear HP (inside displayed rear interval37,825–38,422). Thus `199+151=350` fills the **entire** 7×50 source-fire budget and reproduces the aggregate HP limits using the **known** priority-based First→Second fallthrough (if no Flank) and IF all 350 shots successfully apply full damage. The shot split is a purely mathematical allocation, not an observed trace. This is **only an HP-budget existence proof**, not an observed Gameforge wall phase, slotwise damage allocation, per-hit ammo log, casualty distribution or even proof that all350 shots landed. It cannot establish how many actual wall 1-kills contributed. A real sequential D-kill might waste some damage, requiring additional paths or wall contribution. Most importantly, **target selection of later shots into Second is already established by Help**; what remains unresolved is **whether 151 tickets actually reach Second**, and how its slot-level hits/wounds were calculated.

**What this tells us about our prior musketeer hypothesis:** This provides a valuable DIFFERENT-weapon test of (i) persistent aggregate Slot injuries across rounds, (ii) target-slot shrinkage/refill vs individual soldier identity, and (iii) damage or targeting reaching a new line as earlier line dies. But **7/14 odd-even shot count** is not a universal condition: Slinger starts at 49 addresses for six target slots, 56 for physical central4 (50 source rows cycling 7 targets); with owner-confirmed Forge5 an Axe takes6 full fresh primary hits (Forge0 needs7 only in the historical counterfactual). Their ratios, ammo, source phases and targets are different. R79→80 backline target selection follows the **known formation-level First→(Flank)→Second priority** once First dies; the amount and resulting wounds still do NOT establish a particular slot-level P/I/D/IR mechanism. Future tests must derive one general allocator without hardcoding each screenshot.

Research-only code/fixtures: `tools/research/land_slinger400_rounds77_80_probe.py`, `tests/unit/test_land_slinger400_rounds77_80_probe.py`, `tests/fixtures/reverse_engineering/land_barbarian_slinger400_rounds77_80_20261015.json`. Forge active Lv5 is now owner-confirmed. Outstanding follow-up: were the Slingers freshly deployed around R77 or did they enter earlier and possibly exhaust their 5 primary ammunition? No production combat engine code changes without independent source confirmation.


## CRITICAL OWNER PROVENANCE CORRECTION — R1 and R80–R89 are ONE CONTINUOUS BATTLE (2026-10-15)

**The owner explicitly confirmed that the screenshot showing the very FIRST round (R1, all seven Axe frontline slots each starting at50) and the screenshots R80–R89 belong to THE SAME BATTLE.** All previous wording saying "different battle", "independent battle", or "R1 is not R80–89" was factually wrong and superseded. These are **two NONCONTIGUOUS observational windows of one continuous battle**, not two separate fights. Canonical fixtures are kept in two files for analytical convenience only, and now share exact `battle_identity.battle_id` **`land-barbarian-same-owner-battle-r1-r89-20261014`** with explicit owner-verification provenance. Their raw round vectors remain unchanged.

**Implication for R81–R83 central Axe 99% HP:** Carry-over/redistribution from prior attacks within **the SAME battle** is a natural possibility, not a new unexplained contemporary source that needs a new Kill Type. R1 side slots already ended 98% and99% injured under the current floor-average candidate; R1 **middle five slots ended100%**, so we cannot assert those precise side wounds moved intact to center over eighty rounds. Unobserved **R2–R79** (and R80's observed 99% Axe bar, 45 Axe survivors, four deaths) could independently create, transfer, discard or rebuild injuries, with survivor identity changes, replenishment and RR/SR/IR effects. `D-kill 14→7` for R81–R83 is compatible with surviving previously-wounded Axes showing99% even if gun hits during those rounds are focused onto victims who die without newly wounding survivors. However the actual wound history of central individuals is **NOT reconstructed or observed**, and the HP99% display aggregation/round snapshot semantics remain research hypotheses.

**Research change:** Stop treating late HP99 as independent evidence for an alternative R81–83 instant Kill Type. Instead, treat earliest and latest views as a **single longitudinal state transition with missing intermediate steps**. Keep possible Stage A re-addressing and Stage B gun-damage accounting as separate hypotheses, while never inventing R2–R79 events, reserves or per-individual HP states. Read source window `R1` and `R80..89` within the same fixture `battle_id`, not as independent replication of the model. The exact matching R1 vs R84–87 models therefore represent two time windows **from ONE battle**, which is less independent statistical evidence than two separate fights. Do not change combat engine or merge draft PR without authorization.


## OWNER TWO-PART CORRECTION — MORTAR→GUN→WALL AND INDEPENDENT TARGET REROUTE / KILL ACCOUNTING (2026-10-14)

### Part 1. SAME battle's first-round FULL-Axe snapshot: WALL LAST, it DOES consume previous gun wounds on the killed Axe

Owner explicitly gives the proposed **phase order: mortar first, then muskets, then wall**. The older joint model's phrase "same 490 surviving wounds on both edges after the wall" is **incorrect as stated**: **490 is the gun-phase residual BEFORE the wall attacks**. Mortars direct 1-kill five fresh Axes in physical1, zero in physical7, so they cannot consume wounds from a gun phase that has not yet run. Gun group7 into each edge at confirmed Forge5 yields `7×710=4970=4×1120+490`, retaining 490 wounds across **41 left / 46 right** survivors AFTER guns. If a near-uniform integer per-Axe redistribution occurs before wall (UNVERIFIED), a wall one-shot direct-killing a left Axe removes `floor(490/41)=11` OLD gun wounds; on right removes `floor(490/46)=10`. Then:

| Phase/item | Left physical1 | Right physical7 |
|---|---:|---:|
| start Axe | 50 | 50 |
| mortar effective one-shot casualties (HYPOTHESIS) | 5 | 0 |
| guns: 7 complete hits, pooled kills | 4 | 4 |
| gun-phase living Axe before wall | **41** | **46** |
| gun-phase total residual wounds BEFORE wall | 490 | 490 |
| wall final 1-kill removes OLD gun wounds (near-equal share) | **11** | **10** |
| end survivors | **40** | **45** |
| end living wound totals AFTER wall | **479** | **480** |
| display if floor-survivor-mean HP (UNVERIFIED) | **98%** | **99%** |

Compute `floor(100×(1−479/(40×1120)))=98%`, `floor(100×(1−480/(45×1120)))=99%`. If the wall instead kills a near-equal-share victim carrying **one extra** wound, end totals478/479 would still show98/99. This is consistent with all source data while respecting the owner's firing order. Do **not** confuse removing a wall victim's prior ~11/10 injuries with adding the wall's huge raw damage to guns; wall damage is discarded after a one-shot kill. The earlier zero-adjustment model happened to predict the same displayed bars because percentages are coarse, but its post-wall damage **state** was wrong. Whether the real engine near-equalizes individual wounds and which target wall picks remain UNKNOWN.

### Part 2. Original R81–R87 mixed Knife / Axe battle: split AM reroute from post-reroute gun damage mode

The owner identifies two SEPARATE candidate mechanisms rather than a single "below25→non-D kill" switch:

**Stage A, conditional Attack Matrix target change.** In original R81–R83, physical center4 Axe receives 14 modeled musket AM **addresses**; leftmost Knife receives7. Before R84 the center Axe count drops from29 at start R83 to21 at start R84, so some unknown trigger might route ONE seven-shot source group from physical center4 to physical left1. Post-route candidate address vector becomes **[14,14,14,7,14,14,7]** instead of the baseline **[7,14,14,14,14,14,7]**. If those extra seven delivered complete Forge5 hits to Knife HP360, that is exactly seven additional one-shot Knife gun deaths (and one wall direct Knife kill still hypothetical), accounting for leftmost increase8→15. A population threshold **25** is illustrative only: with a predicate `before_center_population < threshold`, **every integer threshold22–29** would cause the SAME transition between start R83=29 and start R84=21. Therefore current observations CANNOT identify25, nor even establish that occupancy drives rerouting. Ammo, target priority, AM spill and source grouping all unverified.

**Stage B, gun damage accounting AFTER stage A.** Under Forge5, HP1120, Axe armor20, complete gun damage710, healthy Axe takes TWO full hits. At14 center addresses, attacks may pair `14/2=7` fresh Axe kills (D-concentration, 300 overkill discarded per two shots). At seven actual full center hits, this division is INCOMPLETE (`7%2=1`). The SAME battle's R1 all-Axe screenshot ALREADY exhibits clean14-address inner cells and gun aggregate-remainder-consistent7-address edge cells, even though all enemy cells initially have50 units. Thus **partial hit groups** may be enough to alter observed kill/wound results without requiring a separate low-population Kill Type trigger. If using the currently proposed retained Slot wound-pool candidate after stage A, gun center damage `7×710=4970` plus previous living aggregate wounds `W`, so `gun_kills=floor((W+4970)/1120)`, with `rem=(W+4970)%1120`; divide rem near-equally among post-gun surviving Axes and finally one wall 1-kills a wounded Axe, removing that individual's injury from the living pool. Earlier R83 end21 Axe/99% hypothetical `W=25` predicts R84–R87 gun kills **4,4,5,4**, walls1 each; center end count **16,11,5,0** and bars **97,92,96,0**. This is a math witness, NOT verified Gameforge attack chronology/selector.

With illustrative threshold25 and separately the parity/complete-pair group-accounting candidate, an independent research probe `tools/research/land_two_stage_attack_hypothesis_probe.py` compares all original R81–R87 seven-slot death vectors and the already tested R84–R87 aggregate HP witnesses, without changing the engine. It intentionally **does NOT** reconstruct early R81–R83 99% center HP bars: D-kill from concentrated full hits could coexist with PREEXISTING survivor wounds from R80, but actual individual state/history is unknown.

**Falsification priority:** Seek a controlled battle with exactly7 or14 center gun attacks, *same* Axe HP, Forge/Workshop, and varied Axe occupancy, with fixed mortar+wall source accounting. If odd/even address count alone predicts pooled-vs-D residuals at both high and low occupancy, Stage B need not be directly controlled by population. Vary occupancy while leaving group lengths unchanged to isolate Stage A trigger. Neither stage is proven, and matching two battles still allows competing damage allocators (P/IR/RR, attack overflow, ammo/Accuracy). No production combat code change / NAVAL change / merge authorized.

## OWNER CORRECTION — MORTAR AM FIRST SIX + WALL + GUN EXPLAINS R1 SEVEN SLOT HP (2026-10-14)

**Read this before the older R1 analytical section immediately below. Both R1 and R80–R89 are SAME battle (missing R2–R79).** Owner pointed out the 5×6 mortar groups already on screenshot: the current project AM `_shot_rows([6]*5)` places **five attacks into each of first six physical Axe slots**, NONE into rightmost7: mortar-address histogram `[5,5,5,5,5,5,0]`. This follows source six attack rows each of five; land-max physical L→R priority labels `[6,4,2,1,3,5,7]`, so priorities1–6 correspond to ALL physical slots1–6. If EVERY mortar attack directly one-shot-kills one Axe and all seven corresponding wall sections each kill one, subtract mortar+wall deaths from the observed `[10,13,13,13,13,13,5]`: the required **gun death vector** is exactly **[4,7,7,7,7,7,4]**; current-project 7×12 musket AM addresses are `[7,14,14,14,14,14,7]`.

This permits a complete conditional seven-slot model:
- Five middle slots: 14 complete Forge5 gun hits into fresh HP1120 Axe, each gun hit710, **paired individual D-kill** = seven gun Axe deaths; 2×710−1120=300 overkill per Axe is lost, thus **zero surviving gun wounds**. Add mortar5 + wall1 => 13 killed each, **37 survivors at100% HP**.
- Left edge: seven full gun hits give `7×710=4970=4×1120+490`; assume a **pooled gun damage with retained remainder** kill allocation, gun4 deaths and 490 aggregate survivor wound HP. Add mortar5 + wall1 => **10 killed /40 remain**, `floor(100×(1−490/(40×1120)))=98%`.
- Right edge: same gun4 deaths and **same 490 wounds**, mortar0 + wall1 => **5 killed /45 remain**, `floor(100×(1−490/(45×1120)))=99%`.

**Thus source ALL seven death counts [10,13,13,13,13,13,5], survivors [40,37,37,37,37,37,45] and HP bars [98,100,100,100,100,100,99] are simultaneously reproduced with one consistent conditional model.** The older statement "middle 13 still lacks 5 casualties" was a **gun+wall-only control omission of the mortar source**, NOT an unexplained casualty once mortar is included. **No distinct left/right gun mechanics are required**, since the identical 490 wounds across **different survivor populations** naturally yield 98 vs99%.

**Do NOT overclaim recovered Gameforge behavior:** Mortar primary packaged damage 5400 is high enough for a full Axe, but Accuracy is 10 and all 30 real hits + same-target AM, walls seven effective facing targets, source chronology/HP wound preservation, gun D-vs-pooled switch and floor-bar aggregation are *candidate premises*, not battle shot logs. Old 2020 community paper I-kill example requiring exact divisibility does NOT apply directly to `4970/1120`; label edge behavior "pooled remainder" only. Read-only `tools/research/land_round1_mortar_wall_gun_decomposition_probe.py`, tests, new fixture provenance preserve this hypothesis. No production changes or merge authorized.

## SAME-BATTLE EARLY SOURCE — FULL AXE FIRST ROUND: EDGE 7 / MIDDLE 14 ADDRESSES, KILLS NOT JUST GUNFIRE (2026-10-14)

Owner supplied **the VERY FIRST round of this SAME battle (also observed at R80–R89)** screenshot in the ChatGPT conversation (`image(20261014-151332).png`; the original image is **not committed to Hosted GitHub**), with same owner-confirmed PLAYER Forge Lv5 and Sulphur Carabineer Workshop Attack11. Barbarian first-line all seven physical positions appear to contain **Barbarian Axe Swingers** and start with **50 each** (source screen remaining + this-round kills). Transcribed L→R end states **[40(-10),37(-13),37(-13),37(-13),37(-13),37(-13),45(-5)]**, total **80 Axe deaths**, with owner-given displayed surviving HP **[98,100,100,100,100,100,99] %**. Research fixture: `tests/fixtures/reverse_engineering/land_barbarian_round1_full_axes_20261014.json`; model registry maps Axe HP1120 armor20 (internal numeric Gameforge IDs unverified). This R1 screenshot is **FROM THE SAME continuous battle as R80–R89**. Keep a separate observation fixture but link both by battle_id; the real rounds R2–R79 are not supplied and must not be reconstructed from guesses.

**Important multi-source visual confound:** Defender (player) screenshot also displays walls [1]×7, guns [12]×7, artillery [6]×5 and additional flank/side [15]×2; attacker also has ranged [50]×7 and five destroyed siege groups [0(-6)]×5. These counts are screenshot transcriptions, NOT individual attack ledgers. Especially the five center positions' 13 Axe deaths cannot be asserted to be **solely** from direct musket D-kill on the basis of their 100% survivor bars.

**Existing current-project AM under full 84 gun source scenario:** physical target addresses are `[7,14,14,14,14,14,7]`. Current packaged confirmed Forge5, Attack11 yields **710 FULL GUN DAMAGE** against Axe HP1120, so a FRESH Axe requires **two full hits**. Under the EXTRA UNVERIFIED control of *exactly one effective independent wall 1-kill facing EACH Axe slot*:

| Actual L→R | Leftmost1 | Middle2–6 (each) | Rightmost7 |
|---|---:|---:|---:|
| AM **addresses** if all 84 guns fire | 7 | 14 | 7 |
| observed Axe deaths | **10** | **13** | **5** |
| observed survivors HP% | **98** | **100** | **99** |
| Pairwise gun D-kill deaths `floor(shots/2)` + one wall kill | **4** | **8** | **4** |
| Observed minus that D+wall control | **+6** | **+5 each** | **+1** |
| Lossless pooled gun slot `floor(shots×710/1120)` + one wall kill | **5** | **9** | **5** |
| Observed minus that pool+wall control | **+5** | **+4 each** | **0** |

**Critical quantitative rejection:** `14×710=9,940`; 14 perfect complete hits can D-kill only **seven** fresh HP1120 Axes (paired), plus wall one = **eight** (not 13). A lossless numerical HP-pool would get **eight** gun deaths plus wall one = **nine** (not 13), and leave **980 residual damage** BEFORE any wall victim wound is removed; its survivor HP is near 98%, inconsistent with shown 100% under simple floor-bar controls. To reach middle **13** clean full-health survivor outcomes, we must FIRST identify additional attack-source casualties/damage, different true damage stats, wall attack counts/allocation or a nontrivial kill mechanism. The 100% bars alone DO NOT prove pure musket D-kill.

**Independent edge clue:** At the **RIGHTMOST** end, just **seven** full Forge5 Axe gun hits =`7×710=4970 = 4×1120 +490`. Hypothetically one direct wall kill facing the same slot yields **5 dead, 45 living** and near-equal survivor-wound distribution preserves about `490−floor(490/46)=480` wound points; conditional `floor(100×(45×1120−480)/(45×1120))=99%`, an EXACT match to **five deaths / 99%**. This is NOT proof of actual seven successful shots, wall targeting, mode or floor-average bar. With just the SAME seven+wall model leftmost would also get **5 dead / 99%**, but ACTUAL leftmost is **10 dead /98%**, so extra source/targeting/damage is essential.

**Better Kill Type discriminator:** All seven enemy Axe positions start at **50 each**, so edges exhibiting residual HP are NOT dependent on dropping below ~25 or losing target slots. Instead the AM address **count per targeted Slot** is 14 for middle (even, divisible by fresh hits-to-kill `ceil(1120/710)=2`) versus 7 for edges (odd, not divisible by2). An unpaired 710-shot can damage surviving Axes even with no formal Kill Type branch change. But 2020 Barbarossa/Xanto §5.1 strikingly uses exactly **[7,14,14,14,14,14,7]**, calls 14 attacks/2-hit target a **D-kill** case and seven a DIFFERENT **I-kill** example. That historical I-kill depends on perfect divisibility of old `7×32 / 56=4`; today's `7×710 /1120=4.4375` is **NOT divisible**, so **do not label today's edge I-kill as proven**. Paper: https://www.scribd.com/document/638484147/ikariam (2020 pre-v13 and author cautions; no verified Gameforge source code). Candidate selection features to test: `shots % shots_to_kill_full`, source attack group length, wound carryover, P/IR/overkill and other combat lines; not merely size of Axe population.

**Executable discriminant:** `tools/research/land_round1_full_axes_probe.py`, plus `tests/unit/test_land_round1_full_axes_probe.py` explicitly guards confirmed images/HP and refuses to claim 13 middle deaths from 14-musket + one-wall D-kill. New independent evidence must constrain *all* attacking sources, wall targeting and shot chronology before interpreting the 5 central clean columns as D-kill. Source screenshot remains ChatGPT-only. No production engine changes or merge authorized.

## RESEARCH BREAKTHROUGH CANDIDATE — ONE INTEGER WOUND-POOL RULE FITS R84–R87 (2026-10-14)

The owner proposed a **mode-dependent** explanation: at R81–R83, the current baseline AM gives **14 addressed muskets to central Axe** and individually paired D-kill would cause **seven Axe gun deaths** + one independent wall 1-kill, matching eight observed; after central Axe population falls, an unknown mechanism may move one **seven-shot AM source row** to the leftmost Knifeman, whose one-hit HP360 makes exactly **seven additional Knife kills**, while the remaining **seven** Forge5 gun shots deliver `7×710=4970` damage to the central Axe slot and use some NON-D-kill pooled / indirect / redistributed outcome. **AM baseline 14 remains true in the current program.** The rerouting, phase switch, 7 effective hits and mode selector are all hypotheses, NOT confirmed Gameforge logs. The owner noticed the change occurs after center unit count falls from 29 (round83 start) to 21 (round84 start): a threshold **between 21 and29**, potentially half a 50-capacity slot at25, is a falsifiable suggestion, NOT verified.

**New simpler proposed kill rule** does NOT divide 4970 by a floating-point "average injured Axe HP" and round 4.56 to4 while rounding4.78 to5. Let `H=1120` be **full Axe HP**, `D=4970` proposed effective gun damage to center, and `W` **aggregate prior wounds retained among live Axes in that Slot**. After the proposed seven gun hits, take:

```
gun_kills = floor((W + D) / H)
gun_residual_wounds = W + D - gun_kills * H
alive_after_guns = alive_before_guns - gun_kills
wall_deaths = 1                                      # INDEPENDENT HYPOTHESIS
wall_victim_old_wounds = floor(gun_residual_wounds / alive_after_guns)
alive_end = alive_after_guns - wall_deaths
W_end = gun_residual_wounds - wall_victim_old_wounds # if alive_end >0; else 0
display_bar = floor(100*(alive_end*H - W_end) / (alive_end*H))
```

The wall is **one 1-kill after the gun phase** in this proposed chronology; its large **ATK never enters** the gun pool. Prior to wall attack, gun residual wounds are **near-uniformly redistributed across surviving Axes** with integers; one of the least-injured units (the integer floor share) is struck by wall, which subtracts that unit's **preexisting** wound from the survivors' total. This chronological order, integer per-unit distribution, wall targeting and the UI's floor-mean display are **unverified**; 2020 Barbarossa/Xanto §4.1–4.6 motivate redistributed damage in general but do NOT certify this exact step order. Source paper https://www.scribd.com/document/638484147/ikariam , officially posted (with pre-v13 caveat) at https://forum.ikariam.gameforge.com/forum/thread/43268-ikariam-battle-system/.

### Exact four-round integer witness (no per-round death threshold adjustment)

Assume end R83 center **21 Axe /99%** actually has `W83=25` aggregate injuries; `100×(21×1120−25)/(21×1120)≈99.894%`, shown as 99% IF game floors rather than rounds nearest. Then apply exactly the SAME math for all rounds:

| Round | Old live wounds `W` | `W+4970` gun pool | `floor(pool/1120)` gun kills | Gun residual | Axe alive after gun | Wall 1-kill removes wound | End Axe count | End live wounds | Floor-mean HP bar | User screenshot |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| R84 | 25 | 4995 | **4** | 515 | 17 | floor(515/17)=**30** | **16** | **485** | **97%** | 16 /97%, 5 Axe deaths |
| R85 | 485 | 5455 | **4** | 975 | 12 | floor(975/12)=**81** | **11** | **894** | **92%** | 11 /92%, 5 Axe deaths |
| R86 | 894 | 5864 | **5** | 264 | 6 | floor(264/6)=**44** | **5** | **220** | **96%** | 5 /96%, 6 Axe deaths |
| R87 | 220 | 5190 | **4** | 710 | 1 | floor(710/1)=**710** | **0** | **0** | **0%** | 0 /0%, 5 Axe deaths |

This simultaneously reproduces the **gun kills 4,4,5,4** plus **one wall casualty each**, exact surviving counts **16,11,5,0**, and reported bars **97,92,96,0** with 100% integer calculations; no selective round86 rounding, no healing, and no prior arbitrary per-round wall-victim wounds 70/150. Under the proposed wall-after-gun near-equal wound redistribution, `wall_wound_loss` emerges deterministically as **30,81,44,710**.

**Sensitivity rather than one fine-tuned input:** End R83 live 21 Axe and displayed 99% conditionally allows total integer wounds `1..235`. Exhaustively enumerating every such starting integer wound gives **29 separate complete R84–R87 matches**, exactly `W83=1..29`. The 25-point example is not unique; for >29 the modeled bar/kill sequence deviates. This is a credible **mathematical candidate**, not independent proof of actual game selector, per-shot histories or UI floor. No candidate real damage-wave state has been observed.

**Important falsifiers/remaining unknowns:**
- **Why only seven full effective center gun hits?** Baseline current-project AM **addresses 14** at all seven occupied slots. In this candidate, one 7-shot group reroutes to leftmost **or** another gun-effectiveness/AM/source adjustment causes only seven full hits into Axe. It does NOT derive rerouting from the damage pool. The leftmost Knife seven extra deaths fit seven redirected full Forge5 hits numerically but are **not** explained mechanistically.
- **Why change from D-kill to pool after R83?** A slot-occupancy threshold at about half a 50-unit first-line slot, HP/ATT changes, target priority, allocation phases and accuracy are separate hypotheses. The source state crosses 29 (startR83) →21 (startR84), but one battle does not identify a switch.
- **Wall chronology:** game may resolve walls before guns, or distribute wounds across same-wave reserve differently; near-equal integers are the chosen **candidate**, not proven PDF IR/SR/RR behavior.
- **Ammunition/full-hit count:** 84 unchanged primary gunshots across nine rounds was not proven due packaged primary ammo3, possible source replacement / other weapons.
- **Overkill/last Axe:** at R87 all Axes die, 710 not-yet-consumed wound points are removed with last hypothetical wall victim. Whether Gameforge discards or transfers this residual damage, possibly to other slots, is unknown.
- **Other examples are essential**: test separately on other Axe populations, different Workshop/Forge/Accuracy and comparable battle logs; do NOT put this into production engine merely because it exactly matches four consecutive rounds.

**Executable / persistent:** `tools/research/land_round84_87_integer_slot_pool_probe.py` and `tests/unit/test_land_round84_87_integer_slot_pool_probe.py`, independent of existing `land_round85_86_wall_isolated_killtype_probe.py` which only demonstrated a hand-picked *seven-hit* one-round witness. This is the **multi-round strongest candidate**, but still research-only with explicit unknown source rerouting, wall scheduling and redistribution semantics.

## CORRECTION — CENTRAL AM BASELINE IS **14** ADDRESSES, NOT SEVEN (owner correction, 2026-10-14)

**Important correction to our previous R85→R86 numerical witness:** The real **current-project AM model** for **seven source groups of 12 muskets**, all **seven** physical first-line Barbarian slots occupied, assigns L→R attack **addresses** `[7,14,14,14,14,14,7]`. The **central physical4 Axe Swinger receives FOURTEEN model addresses**, because damage priority1 gets two source rows of seven. This is established by the repository's `_shot_rows([12]*7)` / `land-max` geometry, **NOT a verified screenshot-by-screenshot successful Gameforge hit ledger**. Never label 7 as the default center AM.

The later **7-center-address** configuration `[14,14,14,7,14,14,7]` is an **additional, not-yet-verified hypothesis** that one 7-attack source row gets diverted from the central Axe slot to the physically leftmost Knifeman at R84–87. It numerically lines up with leftmost knife deaths going 8→15 and central axe deaths falling, **but it may not be the mechanism**. Other alternatives include 14 addresses with only part delivering full damage, ammo/shot gating, altered individual focus, slot aggregate/overflow or independent source-target assignment. Attack-address count ≠ complete gun hits ≠ gun casualties.

The previously showcased `900 - 70 + 7×710 - 5×1120 = 200` is only a **conditional seven-full-effective-hit / one-central-wall-kill / lossless pooled-Slot existence witness**. It is **NOT** a calculation based directly on the unchanged AM. Recompute from the 14-center-address baseline BEFORE assuming any diversion. If **all fourteen** addresses instead cause full 710 damage into exactly that same hypothetical conserved central pool, with unchanged R85 900 old wounds and wall victim removing70 old wounds, `830+14×710=10770`: the pooled candidate predicts `floor(10770/1120)=9` **gun deaths**, plus **one** independent wall death = **10 deaths**, **1 remaining Axe carrying690 damage and a 38% bar**. This contradicts observed **6 deaths, 5 alive, 96%**, and rules out **only** the conjunction of fourteen fully effective exclusive attacks with lossless pooling and the selected wall/prior-wound parameters. It **DOES NOT** disprove the existing AM 14-address pattern or provide evidence of real seven-address diversion.

The corrected executable `tools/research/land_round85_86_wall_isolated_killtype_probe.py` and tests independently pin **14 unchanged AM addresses**, **7 diverted addresses as hypothetical**, and both slot-pool outcomes. The actual target selection, full-hit count, wall targeting, Academy/Forge/Workshop damage sequence, and P/I/D/IR allocator remain open. Wall is kept as independent one-hit-one-kill control and NEVER contributes its raw ATK to the gun pool.

## NEW LAND RESEARCH CONTROL — wall 1-kills (one-shot) separate from gun Kill Type (owner 2026-10-14)

**Why this is a research priority:** The owner clarified that high-level city walls should be modeled initially as **one effective wall hit causing exactly one whole Barbarian death**. In the paper §5 this is strictly **One-Shot-kill (1-kill)**; **D-kill** means attackers sequentially concentrate on an enemy until it dies. The owner's shorthand wall D-kill thus means direct one-to-one wall deaths, not the paper's multi-hit D-kill category. Under this control, do NOT add the wall's raw large ATK to the musket damage pool or infer its overkill contributes to surviving Axe wounds. **However, how many effective wall attacks target each physical slot per round is unconfirmed.** For center R86, the commonly used `one wall kill` is a case assumption, not part of the screenshot's shot log. Keep both `wall_kill_count_by_slot` and `gun_damage_or_hits_by_slot` separate, then test wall allocations 0/1/2/3. The owner explicitly prioritizes identifying the gun attack result, not refitting Reserve.

**Kill Type selection hypothesis:** Paper §5 calls D-kill, I-kill, P-kill and IR-kill *post-hoc descriptions*, **NOT recovered Gameforge code branches**. Test whether selection correlates with (a) effective per-shot damage after Workshop/Forge/armor, (b) target HP, (c) `ceil(HP/damage)` full-health hit-to-kill threshold, (d) attack-group or AM row size, divisibility and remainder `group_damage % target_HP`, (e) concentration versus wasted overkill, (f) Accuracy, (g) target Slot occupancy and source firing order, and (h) carry-over wounds and ammo. Accuracy itself remains UNKNOWN: **do not implement independent Bernoulli misses** or pretend it is a proven selector. AT Barbarossa's **2025-04-12** Gameforge thread #260 directly describes a pre-update integer-division I-kill case disappearing after changing unit damage/HP with upgrades (https://forum.ikariam.gameforge.com/forum/thread/107659-infinite-horizons-2/?pageNo=13). This validates studying parameter-dependent *outcomes*, not assuming a specific internal `if` decision tree. Old 2020 paper §5.1 I-kill example requires exact integral division; **an arbitrary carry-over slot pool with a remainder must NOT be labeled verified I-kill**.

**Direct precedent in paper §7 for the owner's isolation method:** AT Barbarossa's concrete carabineer-versus-hoplite example FIRST attributes one kill to each opposite-facing wall segment and subtracts wall and third-line casualties before analyzing how many kills the carabineers caused. This is exactly the research decomposition proposed here, but it is a 2020 pre-v13 historical scenario, not proof of one opposing wall hit per active physical slot today.

**New documented cross-slot clue:** 2020 community paper §13, *Am theory lacks*, explicitly warns that damage addressed to a small or weak Slot can **exceed that Slot's total life and apparently damage other Slots**; incomplete Slot / nonstandard renumbering are confounds, and the precise algorithm is called an open problem. This supports **studying** attack spill to the physical leftmost Knifeman, but §4 RR is inter-round same-wave redistribution and SR/IR are largely within targeted Slot; they alone do not prove immediate cross-class cross-slot spill or leftmost priority. See https://www.scribd.com/document/638484147/ikariam . Both paper and forum are player-led reverse-engineering, not official executable Gameforge rules.

### R85→R86 independent damage control: seven hypothetical center full gun hits (Forge5)

- User observed end R85 **11 Axe at 92%**, then end R86 **5 Axe at 96%**, round R86 **6 Axe deaths**. Source profile HP**1120**, actual player Forge5 ATT11 gun attack**710** vs Axe. **Conditional** display convention `floor(100×surviving HP / max survivor HP)` produces R85 aggregate living wounds **863–985** and R86 **169–224**. Identical individual survivor identity across the snapshots, no reserve/wave input/HP inflow, chronology, and the bar convention remain unconfirmed.
- First isolate hypothetical **one wall one-shot 1-kill** in central Axe Slot, contributing **one casualty** but **zero wall numeric damage** to the gun pool. Five Axe deaths remain attributed to the guns under this case. Under *individual-only exclusive full-hit D-kill*, seven gun hits to kill five Axes require **at least three** previously one-hit-ready Axe victims (`2×5−7=3`), each with previous wound **≥410**, aggregate **≥1230**. Even redistributing all pre-existing injuries **WITHIN** the same center 11 Axes cannot generate 1230 from a 92% bar at max 985. Thus the restrictive model is **conditionally incompatible** without wound inflow, different bar semantics/timing, extra gun shots, more wall kills, other sources or a distinct damage allocator. The previous no-healing 92→96 witness in the HP probe **did not verify** enough combat attacks to kill those six.
- **Exactly reproducible alternative, NOT an official mechanism:** Let end-R85 11 living Axes carry **900 total preexisting wounds** (within 863–985). The hypothetical wall directly kills one Axe that happened to carry **70 old wounds**, so it removes **one casualty + that 70 old-wound amount** but its actual overkill damage is discarded and NEVER added to guns. Ten Axes now retain **830 pooled old wounds**. Seven hypothetical full Forge5 gun hits contribute `7×710=4970` fresh damage; hypothetical perfectly conserved slot-level damage pool totals **5800**. Five gun kills consume `5×1120=5600`, leaving **200** aggregate wounds over **five** surviving Axes: `floor(100×(5600−200)/5600)=96%`. All observed center deaths/survivors/bar are matched, with **no healing**, **no cross-slot effects** and **no need to instantiate individual gun victim trajectories**. But the `70` wound allocation to the wall victim and aggregate conservation/overkill are merely constructed existence witnesses.
- Under that SAME hypothetical starting pool and seven full shots, Forge0/1/2/3 yield **4 gun Axe kills**, while Forge4/5 yield **5**; five kills become possible at **682 effective damage per shot** in this constructed setting. The actual Forge5 leads to 200 residual wounds and 96%; Forge4 would produce a different bar. This directly illustrates the user's *conditional* idea that changing Workshop/Forge damage can cross casualty/HP regime boundaries, with absolutely no proof that the game dispatches on that mathematical threshold.

**Executable research-only falsifier:** `tools/research/land_round85_86_wall_isolated_killtype_probe.py` with `tests/unit/test_land_round85_86_wall_isolated_killtype_probe.py`. The probe computes conditional 0–3 wall-kill cases, the individual D-kill prewound lower bounds, a separate wall-one-kill + aggregate-gun-damage witness and counterfactual Forge sensitivity. It does **NOT** claim to explain the additional **seven leftmost Knife deaths** at R84–87, nor to validate source ammo, wall aim, RR/SR/IR, or Accuracy. No production engine changes allowed without independent evidence.

## 2026-10-14 owner's critical corrections — must be applied BEFORE using earlier numerical inferences

1. **Owner-confirmed actual player Forge = level 5.** The owner first confirmed that the player had Forge ACTIVE and then explicitly confirmed **level 5** for this very R80–89 battle. Using current packaged `v14-hephaistos`, workshop attack11 gives pre-Forge `580+11×5=635`; effective attack `635×1.15=730.25`, floor after armor yields **730 vs Knifeman (armor0)** and **710 vs Axe Swinger (armor20)**. Forge0 comparisons (635/615 and ≥505 prior wound) are **historical COUNTERFACTUAL CONTROLS**, not real-battle values. Under a full 710-point hit against fresh Axe HP1120, the conditional one-hit-ready prior injury threshold is **410**, not 505.

2. **A seven-shot AM address deviation is NOT equivalent to seven exclusive full-hit attacks on the physical leftmost knife slot.** The owner explicitly highlighted the **distributed damage mechanism described in the repository Battle System PDF**, under which a firing event may participate in spread damage across multiple target slots. Recheck the authoritative PDF `ikariam battle system.pdf` or `ikariam-battle-system.pdf`, versions and applicable Land rules; distinguish (a) an AM source firing address, (b) effective attack amount, (c) allocation to one/many target slots or units, (d) accumulated target HP damage, (e) casualties, and (f) the final game HP-bar aggregation. Even if seven more knife losses are accounted for by a full AM row *numerically*, that is NOT proof that its entire damage was diverted to a single leftmost cell.

3. **Conditional Axe prewound inference, not a Gameforge observation.** At confirmed Forge5, if exactly seven **exclusive complete** gun hits go to central Axes and a separately hypothetical wall kills one Axe, then R84/85/87 four gun-killed Axes with seven shots require at least one prior wound ≥410; R86 five gun-killed Axes require at least three prior wounds ≥410 (≥1230 aggregate). These bounds additionally assume individual focus pairing, no additional shot sources/redistribution and unchanged relevant HP state. They are NOT independently observed, and cannot be generalized to actual combat without proving this attack allocator.

4. **Use center Axe survivor count AND owner-supplied HP bar jointly for new inverse bounds:** central survivor sequence R80–87 `45,37,29,21,16,11,5,0`; per-round central deaths `4,8,8,8,5,5,6,5`; displayed bar `99,99,99,99,97,92,96,0%`. The **92→96% rise while 11→5 survivors remain** can be compatible with survivors-only averaging and selective death of the most injured; do not call it healing. For each candidate PDF-compatible damage allocation, update actual per-individual/slot damage states, apply Forge inputs and explicit UI rounding/denominator variants, then compare the entire round-to-round sequence. Since game individual-hit histories are invisible, use feasible hidden-state enumeration/bounds rather than pretending original per-shot logs are available.

5. **Separate confirmed evidence from convenient fits:** user-confirmed R80–89 casualties, player R80 84+19, **player Forge level 5**, one effective high-level-wall hit lethal, and displayed HP bars are evidence; 84 valid gunshots every round, seven wall strikes, one-facing-each-wall allocation, seven exclusive center hits, previous individual wounds and floor-mean UI bars remain **HYPOTHESES**. If attack effects permit other sources/multi-kills, `84+7=91` is not a universal cap. No production formula change.

6. **Codex follow-up:** Prior P2 identity provenance/pairwise Axe concentration/HP continuity were addressed in code. The next exact-head Codex review (`b8ce21e`) identified three remaining P2 in **historical narrative**, not yet cleared: wording falsely implied owner never confirmed Forge was active; §6A/6B omitted that 14 Axe shots require 7 **paired individual** hits; and §6B omitted **same survivor population and no intervening RR/SR/IR/rebuild/healing/HP transition** for the previous-bar contradiction. All three narrative premises are corrected in this update alongside owner-confirmed Forge5. Fresh exact-head review required.

### PDF source check, Forge sensitivity and Codex P2 controls — 2026-10-14

**Source qualification (important):** Both repository PDFs are listed as 38,277,072 bytes, but binary equality and exact revision have not been verified. The GitHub connector cannot return their 38 MB binary in this environment. The accessible text transcription of AT Barbarossa and Xanto, *Ikariam Battle System*, dated 16 July 2020 (sections 2, 3, 4 and 5), was cross-checked. That document is a **player-led reverse-engineering investigation**, not Gameforge's published executable code or an official complete specification. Its Gameforge forum post explicitly warns the data were pre-game-version-13 and that many numeric values changed. See https://www.scribd.com/document/638484147/ikariam and https://forum.ikariam.gameforge.com/forum/thread/43268-ikariam-battle-system/. Direct page-image/binary verification of the exact repository PDFs remains outstanding.

**What its actual redistribution taxonomy supports:**

- **Attacking Matrix:** hypothetical source firing addresses/rows, not a guaranteed mapping to individual deaths; physical order must be distinguished from damage-priority renumbering.
- **RR (Reserve Redistribution, §4.3):** between rounds; same-unit, same-wave survivor damage may redistribute across reserve and deployed slots. Proposed slot allocation is `slot_damage = total_wave_survivor_damage × slot_population / same_wave_survivors`, subject to unknown integer assignment. This is the strongest PDF reason not to assume persistent individual HP wounds from one screenshot to the next.
- **SR (Slot Redistribution, §4.5):** within the already targeted slot after one firing line and before the next. Not universally active.
- **IR (Immediate Redistribution, §4.6):** within an addressed target slot between individual shots, again subject to examples and unverified universal triggers.
- **One shot splitting immediate damage across distinct target slots is NOT proven by the cited PDF sections.** It may be investigated as a separate candidate, but neither the owner observation nor the text is direct confirmation of this implementation.

**P2-A:** fixture now distinguishes owner-confirmed Knifeman/Axe Swinger labels from packaged registry model IDs and unknown internal Gameforge IDs/per-hit traces.

**P2-B:** Under the **now confirmed Forge5** profile, fourteen full Axe hits each at 710 cause **zero Axe deaths** if delivered to fourteen distinct fresh HP1120 individuals; they can cause **seven** deaths only if paired onto seven individual fresh axes (or another compatible prior-wound allocation). Addresses do NOT enforce that focus. Forge0 comparison remains 615, not real.

**P2-C:** The HP clash field is a **counterfactual** gate requiring (i) exact 7 exclusive Forge5 hits plus stipulated wall addresses, (ii) identical survivor identities with unchanged wounds across both snapshots, (iii) no RR/SR/IR, recruitment, healing, replacement or intervening HP transfer, and (iv) matching screenshot boundary and actual floor-average HP display. None of those premises is verified by real-game per-hit logs; `incompatible_IF_bar_floors_average_of_survivor_HP` stays false.

**Forge:** Owner confirmed the actual **level = 5**, not merely active. The probe now consumes `player_forge.level=5` from the fixture for its actual-game **weapon damage input** (730 knife, 710 Axe, `1120−710=410`) and retains `weapon_profiles(0)` solely as a marked Forge0 counterfactual. The **actual target/accuracy/hit allocation** is not confirmed by knowing the damage profile.

**Joint HP constraints (additional read-only executable probe):** Under the explicit *candidate* floor-of-average-survivor-HP convention and Axe HP1120, R85 11 survivors/92% constrain remaining aggregate wounds to **863–985 integer HP**; R86 5 survivors/96% constrain them to **169–224 HP**. A witness has R85 total wounds 900 spread as five ×40 and six later-dying soldiers bearing 116/116/117/117/117/117 damage. If only the more injured six subsequently die, the five survivors still carry 200 wounds and display 96% **without healing**. This proves *HP-bar feasibility*, not that any assumed seven gun hits, wall phase or actual battle events can kill those six; per-hit damage budget is an independent required constraint. See `tools/research/land_round80_89_hp_state_probe.py` and matching tests.

**R88/R89:** 91 deaths with six/four occupied physical target slots remain strong observed constraints. `84 gun + 7 effective walls = 91` is conditional on the sources, all shots and at-most-one-kill premises; it is not a universal upper bound if multi-kill or another source is permitted. The posthoc wall fallback is not a proven algorithm.

**Next AI: Start here, then inspect source fixture, PDF, `tools/research/land_round80_89_am_focus_probe.py`, `tools/research/land_round80_89_two_class_am_probe.py`, wall source experiments and their tests. Hosted main authoritative; work in land Draft PR #72, keep naval PR #69 untouched, never merge without explicit owner command.**

---

## Crucial owner's wall-fire correction — separate seven walls from 84 musketeer shots (2026-10-14)

**Owner confirmed:** The defending city wall is at a high level, and **one effective wall attack can kill one attacking Barbarian**. Therefore earlier comparisons that directly equated user-reported Barbarian deaths to **only** the 84 modeled firearm attack addresses were incomplete. In this source sample, seven defending wall sections are visibly present from **R81 through R89** (their `1(-0)` unit symbols indicate walls surviving, not their number of firing shots). The user **did not explicitly confirm** that every wall section actually fired once every round, or the wall phase, target-priority distribution and any misses. Preserve **known one-shot lethality** separate from **hypothetical 7 wall hits/round**.

To test a concrete two-source conditional **maximum** model, assume 84 musket attempts and all seven wall sections each fire once and score **one kill** in the walled rounds, giving a maximum budget of **91 kills/round**, not 84.

| Round | Owner-verified observed Barbarian main deaths | Hypothetical successful wall kills | Remaining deaths attributable to muskets *if wall hypothesis true* | Difference vs 84 modeled musket attacks |
|---:|---:|---:|---:|---:|
| 80 | 19 | **not applicable** (different open-field situation) | **not independently separable** | — |
| 81 | 84 | 7 | **77** | −7 |
| 82 | 84 | 7 | **77** | −7 |
| 83 | 84 | 7 | **77** | −7 |
| 84 | 88 | 7 | **81** | −3 |
| 85 | 88 | 7 | **81** | −3 |
| 86 | 89 | 7 | **82** | −2 |
| 87 | 88 | 7 | **81** | −3 |
| **88** | **91** | **7** | **84** | **0** |
| **89** | **91** | **7** | **84** | **0** |

The sign of the last column is the **modeled number of gun attacks minus hypothetical gun kills**, NOT directly observed misses, individual shot logs, target immunity or official Accuracy. `91 = 84 + 7` is an extremely useful joint-source *conditional* equality at R88–89, not proof exactly seven walls fired.

### Per-position conditional decomposition, Round81–83

For **seven occupied target cells**, try an illustrative wall assumption of **one kill on each target cell**:

| Physical target position L→R | 1 | 2 | 3 | **4 (distinct axe)** | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Modeled musketeer AM attack addresses | 7 | 14 | 14 | **14** | 14 | 14 | 7 |
| **Hypothetical** wall successful kills (NOT observed addresses) | 1 | 1 | 1 | **1** | 1 | 1 | 1 |
| Owner-confirmed actual unit casualties R81–83 | **8** | **15** | **15** | **8** | **15** | **15** | **8** |
| Implied musketeer kills, conditional on walls | 7 | 14 | 14 | **7** | 14 | 14 | 7 |
| Implied gun kills − modeled AM addresses | 0 | 0 | 0 | **−7** | 0 | 0 | 0 |

This is an **exact arithmetic fit** with all six non-center cells; the center's seven non-kill gun addresses may represent surplus/nonlethal damage, overkill, other targeting, or incorrect assumptions. Central HP displayed 99% does not identify where seven actual musket bullets landed. The wall section target mapping `one each` is **not independently observed**.

### Wall-target-distribution-INDEPENDENT lower bound (stronger than illustrative one-per-slot)

The above `one wall kill in each position` decomposition is only a convenient accounting scenario. We can also derive a **rigorous conditional impossibility** without assuming **where** the seven wall attacks land.

For physical position `i`, define its *shortfall relative to the FIXED proposed 84 musket AM addresses* as `s_i = max(0, observed_deaths_i - modeled_gun_addresses_i)`. If each gun attack can kill **at most one** and is held to its modeled position, the sum of all positive shortfalls must be covered by wall kills or other attacks:

| Round(s) | Observed source deaths | Positive deficits vs fixed musket AM, L→R, before adding walls | Required additional one-kill events | Hypothetical wall kill budget | Still unexplained with ANY wall positioning |
|---|---:|---|---:|---:|---:|
| 81–83 | 84 | `1,1,1,0,1,1,1` | **6** | ≤7 | **0 minimum** |
| **84–85, 87** | **88** | `8,1,1,0,1,1,1` | **13** | ≤7 | **≥6** |
| **86** | **89** | `8,1,1,0,1,1,1` | **13** | ≤7 | **≥6** |
| 88 | 91 | `2,1,1,1,1,1` | **7** | ≤7 | **0 minimum** |
| 89 | 91 | `4,1,1,1` | **7** | ≤7 | **0 minimum** |

For R84–87, the leftmost **15 deaths** alone exceed its proposed **seven musket address opportunities + all seven hypothetical wall hits = 14**, hence even giving all wall attacks to that one target still leaves at least one unexplained death. Across ALL cells the stricter lower bound is **13 − 7 = 6**. The conclusion is not “six gun hits definitely changed position”; alternatives include extra source waves, more than one lethal target per modeled shot, omitted fire phases or an incorrect 84-address assumption. But **the combined restrictive model (fixed 84 gun AM, ≤7 one-kill wall attacks, one gun hit kills at most one)** is falsified for R84–87 under the owner's visual death data. This is independent of any particular proposed wall target-priority distribution.

At R88 and R89 the positive shortfalls add to exactly seven, so **IF** the muskets have exactly 84 addresses each causing one kill and walls have exactly seven kills, the wall slot distribution would have to be `2,1,1,1,1,1` and `4,1,1,1` respectively; this is an **inverse requirement conditional on that highly restrictive model**, not an official wall attack priority.

### R84–87 and after reserve/axe depletion

With the **same hypothetical one-wall-kill-per-cell** distribution:
- R84,85,87: after subtracting wall, required gun kills `14,14,14,4,14,14,7` vs modeled physical AM `7,14,14,14,14,14,7` → residual **+7,0,0,−10,0,0,0**. The first slot needs **SEVEN MORE lethal hits than its nominal AM addresses**. A fixed unchanged 84-attack AM with *every wall exactly once per corresponding enemy position* cannot explain this; some source readdressing, wall priorities, more gun attacks, or wrong hit-to-kill assumption must change.
- R86: gun kills after wall `14,14,14,5,14,14,7` versus fixed AM → residual **+7,0,0,−9,0,0,0**.
- **R88**, six occupied targets: existing main AM under 84 shots predicts **14 addresses each**. Actual `16,15,15,15,15,15`; one hypothetical wall distribution `2,1,1,1,1,1` (one per occupied plus extra to leftmost) makes implied guns exactly `14,14,14,14,14,14`.
- **R89**, four occupied targets: existing main AM predicts **21 addresses each**. Actual `25,22,22,22`; another hypothetical wall distribution `4,1,1,1` gives `21,21,21,21` gun kills.

These R88–89 wall allocations are **post-hoc algebraic examples**. They are NOT a verified wall priority rule; they put all excess wall attacks into the leftmost occupied position specifically because that matches current outcomes. A competing model that gives each of the seven wall sections **one source-row attack** through the existing **Land AM row-major physical damage-priority** instead has `_shot_rows([1]*7) == [1,1,1,1,1,1,1]`; it hypothetically places **ALL SEVEN wall hits on physical center position 4** both at R88 (`0,0,0,7,0,0`) and R89 (occupied physical 2–5: `0,0,7,0`), unlike the post-hoc leftmost-extra split. This produces residual gun-kill patterns **R88 `+2,+1,+1,−6,+1,+1`** and **R89 `+4,+1,−6,+1`** against musket AM. This is an important discrete row-major source behavior, but **does not establish that official Gameforge walls use this algorithm**, or that seven wall sections really fire one successful attack each. The difference makes wall targeting a **testable separate algorithm**, not something to conflate with musketeer Accuracy.

**Independent unresolved engine boundary:** Current experimental town-wall logic includes damage *to* walls and breach/refill priority; its **offensive wall Accuracy/shot targeting is not calibrated**. Therefore no production engine code has been changed to add wall kills based on these pictures. Keep the wall's *lethal effectiveness* as a direct user observation, the number of actual wall attacks and addresses as unknown, and the numerical 7-shot control as a candidate requiring further evidence.

**Reproducible source-separated experiment:** `tools/research/land_round80_89_wall_source_probe.py` reads fixture `wall_attack_followup`, runs actual current `land-max` AM address calculations and produces alternate wall-targeting decompositions. `tests/unit/test_land_round80_89_wall_source_probe.py` protects the 81–89 death budget, center residual, and differing 7/6/4 active target positions. Neither produces fake game individual-shot telemetry.

## Current research priority correction — ATTACK FOCUS, not refill rediscovery

**Owner correction 2026-10-14:** Reserve/round-start replenishment, source-unit replacement and front-line slot refilling are ALREADY known and represented in the existing combat simulator. The axe/ordinary reserve accounting below is **only evidence provenance / controlled input verification**; do not spend the next research stage "discovering" that depleted reserves cannot replace casualties. The substantive new question is **target address / attack concentration / additional attack sources / casualty versus hit-budget conservation as active target cells shrink**.

The current production Land `engine._shot_rows([12]*7)` and target address selection `addressed[(row_number-1) % len(addressed)]`, paired with current `land-max` **first** physical order `[6,4,2,1,3,5,7]`, permits a **CONDITIONAL baseline** if all seven shown player musketeer second-line groups (12 units per source cell) successfully fire one time in the same phase and each target front cell is addressable. This is an AM-address histogram, NOT a casualty predictor. Those assumptions about complete source fleet, ammo eligibility and unit shots have NOT been verified from the ten images.

| Game round | Actual occupied Barbarian front cells, physical L→R | Current AM addressed hypothetical shots (84 total) | User-verified Barbarian **deaths** | Residual deaths MINUS model addressed shots (**not extra hits**) |
| --- | --- | --- | --- | --- |
| 81–83 | 1–7 | **7,14,14,14,14,14,7** | **8,15,15,8,15,15,8** | **+1,+1,+1,−6,+1,+1,+1** (net0) |
| 84–85, 87 | 1–7 | **7,14,14,14,14,14,7** | **15,15,15,5,15,15,8** | **+8,+1,+1,−9,+1,+1,+1** (net+4) |
| 86 | 1–7 | **7,14,14,14,14,14,7** | **15,15,15,6,15,15,8** | **+8,+1,+1,−8,+1,+1,+1** (net+5) |
| 88 | 1–6 | **14,14,14,14,14,14** | **16,15,15,15,15,15** | **+2,+1,+1,+1,+1,+1** (net+7) |
| 89 | 2–5 | **21,21,21,21** | **25,22,22,22** | **+4,+1,+1,+1** (net+7) |

**Three sharp focus/attack constraints:**

1. **R81–83 same pattern 3 times:** deviation from current Land AM (if 84 fully eligible shots and 1-shot/kill) is **−6 deaths at central physically distinct unit and +1 at EVERY other six cells**. This exact residual zero structure needs explaining by target-dependent HP/damage/targeting or other attack effects, not a generic Reserve note.
2. **R88–89 retain 91 reported casualties despite 6→4 target cells:** the current row-address system changes from **14 shots per occupied cell to 21 shots per occupied cell**. The owner separately confirmed each effective *high-level wall attack* kills one Barbarian, and seven living wall sections are visible; **if each fires a successful attack**, the 7 wall + 84 musket budget matches 91 deaths exactly. The *real wall shot count and target distribution* remain unknown, and the conditional leftmost-extra `2,1,1,1,1,1` / `4,1,1,1` wall scenarios are only examples; full rationale above.
3. **Under a restricted model where ONLY these 84 hypothetical musketeer shots occur and EVERY shot kills at most one unit, R84–89's 88/89/91 casualties are impossible**. At least one restriction is wrong (e.g., extra attacking source / additional fires / multi-unit damage accounting / incorrect source-frame or turn interpretation). A casualty minus shot count is NOT an actual attack trace and cannot identify the culprit without other observations.

**Focused implementation:** `tools/research/land_round80_89_am_focus_probe.py` derives physical-slot AM address histograms from actual `land-max` data and `_shot_rows` and compares them with the owner-confirmed round-end deaths, without claiming shots==kills. `tests/unit/test_land_round80_89_am_focus_probe.py` protects physical 7/6/4-slot cases, R81–83 exact residual and R88/R89 fixed +7. **Next experiments should compare different target address selectors, multi-attacker phase eligibility and Gameforge-visible casualties/HP; no more refill rule discovery.**

## 0. Quick start for the next AI agent

1. Inspect Hosted GitHub **main**, this research branch `research/land-barbarian-rounds80-89-observations`, issue #71, Draft PR if opened, last exact-head CI, last exact-head Codex Review and unresolved threads; never assume a historical review approves current head.
2. Read the **user-verified** machine-readable fixture `tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json` and the corresponding static regression `tests/unit/test_land_barbarian_rounds80_89_research.py`.
3. Distinguish **(i)** owner-confirmed casualty labels and provided slot HP %, **(ii)** other screenshot-transcribed reserve/remaining unit counts, **(iii)** cross-round conservation calculations, **(iv)** *hypotheses* of engine mechanics. Screenshots were attached in the originating ChatGPT conversation (ten PNG images), not committed to this repository; if raw pixels are required for new automated processing, request source image access. The long-lived numeric fixture is independently useful without them.
4. Examine current Land engine's `attacking_matrix` addressing, first/second/third firing order, target eligibility `ATK>DEF`, Forge and Workshop, ammunition/reload and existing `same-wave` / `cross-wave` refill rules. Do not import NAVAL Accuracy assumptions as Land facts.
5. A useful first goal is to explain front-line **loss patterns with reinforcement capacity constrained**. Follow with models predicting newly measured adjacent-round totals/slot distribution, without requiring game-hidden per-individual shot logs. Keep a research-only experimental probe; don't hard-code round numbers or verified casualties as combat outputs.

## 1. Actual visual evidence and explicit confirmations

This is one lengthy Barbarian Village attacking/defending battle. User's **player musketeers Workshop Attack Lv11 / Defense Lv3**. The ten screenshots span rounds **80,81,82,83,84,85,86,87,88,89** in ascending order. The user explicitly confirmed:

- `35 (-15)` means **35 remaining displayed and 15 lost IN THAT ROUND**, not total losses across all previous rounds.
- Earlier assistant transcription of **all Barbarian seven-cell front-line deaths for rounds80–89** was correct.
- The player at round80 had **84 main-line + 19 siege-unit deaths** (the seven `0(-12)` cells and the siege `0(-6)×3`, `0(-1)`).
- Supplied front-line seven-cell *displayed surviving-health bar percentages*, in rank order L→R, including central anomalies.

Do NOT infer every Barbarian death was necessarily caused by the user's musket attack alone. Other player army sources, passive wall rules, phase sequencing and units not represented by a single icon might be relevant.

| R | Barbarian per-cell deaths L→R (— is EMPTY, not zero) | Total | Fourth cell (central special axe) remaining | Fourth cell HP% | Ordinary-melee reserve (image read only) |
|---:|---|---:|---:|---:|---:|
| 80 | 3, 3, 3, 4, 3, 3, 0 | **19** | 45 | 99 | 310 |
| 81 | 8, 15, 15, 8, 15, 15, 8 | **84** | 37 | 99 | 535 |
| 82 | 8, 15, 15, 8, 15, 15, 8 | **84** | 29 | 99 | 459 |
| 83 | 8, 15, 15, 8, 15, 15, 8 | **84** | 21 | 99 | 383 |
| 84 | 15, 15, 15, 5, 15, 15, 8 | **88** | 16 | 97 | 307 |
| 85 | 15, 15, 15, 5, 15, 15, 8 | **88** | 11 | 92 | 224 |
| 86 | 15, 15, 15, 6, 15, 15, 8 | **89** | 5 | 96 | 141 |
| 87 | 15, 15, 15, 5, 15, 15, 8 | **88** | 0 | 0 | 58 |
| 88 | 16, 15, 15, 15, 15, 15, — | **91** | — (no axe) | all occupied cells 100 | 0 |
| 89 | —, 25, 22, 22, 22, —, — | **91** | — (no axe) | all occupied cells 100 | 0 |

**Full 7-cell HP readout reported by owner:** R80–R83 `100/100/100/99/100/100/100`; R84 `100/100/100/97/100/100/100`; R85 `100/100/100/92/100/100/100`; R86 `100/100/100/96/100/100/100`; R87 `100/100/100/0/100/100/100`; R88 and R89: all *occupied* cells displayed 100. **The scope of the UI denominator and the meaning of 100% are NOT verified.**

The whole user-confirmed row-total series sums to **806** displayed deaths from R80 through R89. This is an arithmetic sum of round-specific casualty labels, **not** a claim that the entire battle had only 806 Barbarian casualties; it may have other combat lines/rounds.

**Other screenshot transcriptions, not separately owner-confirmed:** top rear rank seven groups of `50(-0)`; R80 side flanks `40(-0)`; R81–R89 player's on-field seven groups `12(-0)` and seven wall sections `1(-0)`; reserve numbers as above. This secondary visual evidence must retain its weaker provenance classification.

## 2. Conservation checks: a rare way to factor away reinforcement confounding

### A. The central axe group is arithmetically self-contained

Central distinct-image holder's shown survivors R80..87 are:

`45 → 37 → 29 → 21 → 16 → 11 → 5 → 0`

The death labels are `4,8,8,8,5,5,6,5`. The first shown state is compatible with a **49-unit group** (`45+4=49`). All next decreases satisfy `remaining_r − remaining_(r+1) = deaths_(r+1)`. Total deaths **49**. No visible refill is needed to explain this particular unit group over this window; it is not evidence of a general "axe cannot refill" official rule. On R88 that occupant has disappeared and ordinary front units use other positions.

### B. Ordinary-melee reserves balance repeated 15-casualty slots

Separate the central axe from all other front losses on R81–R87:
- R81–R83: each total84 − central8 = **76 ordinary melee casualties**.
- R84–R85: each total88 − central5 = **83 ordinary melee casualties**.
- R86: total89 − central6 = **83 ordinary casualties**.
- R87: total88 − central5 = **83 ordinary casualties**.

Visual ordinary reserve snapshots show:

`535 → 459 → 383 → 307 → 224 → 141 → 58 → 0` for R81→R88.

Adjacent reserve drops for R81→R82 through R86→R87 are exactly `76,76,76,83,83,83`, equal to ordinary losses at those previous turns. The drop R87→R88 is only **58** despite the previous row displaying 83 ordinary losses, **consistent with reserve exhaustion/capped replenishment** and next-round loss of full slot occupancy. The reserve rise R80→R81 `310→535` is a **225-unit increase**, NOT explained by normal losses; R80 shows open field while R81 onward shows a walled setting, so possible reinforcements/re-entry/rebuild need independent analysis.

This excellent arithmetic is **strong evidence** for a reserve-to-front replenishment step, even though it does **not** independently settle the exact snapshot order or official placement/ranking rule.

### C. Front attrition versus redistribution at depleted reserve

R87 has 7 occupied front cells and loses 88 units including the final 5 axe. R88 has **6 occupied cells and loses 91**; R89 has **4 occupied cells and loses 91**, despite the reserve becoming empty. More casualties per surviving physical cell become visible; may reflect **target-address redistribution** as the target set contracts. But other variables might have changed (eligible target set, damage priorities, one-shot caps, ammunition, shooter quantities), so **91 constant is a pattern, not proof of a fixed damage-budget rule**.

### D. Exact endgame population conservation across formation compaction

**A stronger independent arithmetic finding than fixed per-slot death counts:** Screenshot-read ordinary female melee remaining units for R87/R88/R89, combined with user-verified round deaths and visual reserves, reconcile **without losing or inventing a single ordinary melee unit** across R87→R88→R89.

| Stage | Ordinary melee on occupied front slots | Ordinary reserve | Combined |
|---|---:|---:|---:|
| R87 **end** | `35+35+35+35+35+42=217` (axe slot at zero excluded) | **58** | **275** |
| R88 **before round damage**, reconstructed | six slots `25+50+50+50+50+50=275` | **0** | **275** |
| R88 **end** | six slots `9+35+35+35+35+35=184` | **0** | **184** |
| R89 **before round damage**, reconstructed | four slots `34+50+50+50=184` | **0** | **184** |
| R89 **end** | four slots `9+28+28+28=93` | **0** | **93** |

The equations are exact:

```
R87-end visible ordinary 217 + reserve 58 = 275
R88 killed = 16+15+15+15+15+15 = 91
R88-end visible = 9+35+35+35+35+35 = 184 = 275−91
R89 killed = 25+22+22+22 = 91
R89-end visible = 9+28+28+28 = 93 = 184−91
```

Reconstructed R88-before slot counts `25,50,50,50,50,50` and R89-before `34,50,50,50` follow **mechanically** from shown remaining+round deaths; these before-round slot counts were **not directly seen as complete Gameforge target log states**. They suggest **same-type group consolidation across physical positions, then refill/reuse of reserves**, and provide a stringent conservation property for a candidate Land formation-rebuild algorithm. They **do not uniquely determine** Gameforge's target-address sequence or individual HP distribution.

The data could be an especially useful held-out test for code implementing cross-slot compaction: force a model to pass `217+58→275→184→93` with the proper 7→6→4 visible slot identities *without injecting fake units or killing unseen units*. Beware reserve screenshot transcription has not been independently confirmed by owner, and stage labels before/after-round are deductions based on UI interpretation.

### D. Restrictive "84 visible defenders each kill at most one enemy" theory fails

From R81 onward, screenshots show **seven** defender positions labeled `12(-0)`, i.e. **84 visible deployed units** in those positions (unit-type identity and attack source/weapon role not independently established). The Barbarian front-line displayed kills are **84** on R81–83, but increase to **88/89** on R84–87 and **91** on R88–89. Therefore **IF** those 84 were the ONLY damage-dealing source, **IF** each fired exactly ONE hit per round, and **IF** each hit could kill at most one target, totals greater than 84 are impossible. At least one assumption of that overly restrictive mechanism would have to fail: other firing lines, wall damage, multi-shot/extra attack, multi-target effects, casualty phase differences, game UI source semantics, etc. The later owner's wall clarification identifies the **wall as an important plausible additional source** whose effective hits kill one Barbarian. This resolves why a musket-only 84-shot bound is inappropriate as a **complete damage-source model**, but does **not** independently establish a seven-shot wall attack count or actual target distribution.

Crucially **don't assert** these seven `12(-0)` displayed groups are necessarily the player's 84 musketeers or the only attackers. The owner provided musket Workshop ATT11/DEF3 but did not supply a weapon-by-weapon fire ledger. This bound is a **falsifying sanity check on a narrow hypothetical**, not proof of more than 84 musket hits.

### D. Health bar rises as unit count falls

R85 central axe = **11 remaining, HP bar 92%**; R86 central axe = **5 remaining, bar 96%**; R87 unit count0, bar0. If the UI bar represents **average HP of living survivors**, the bar can rise naturally when the worst-wounded individuals die, without any healing. It might instead reflect another aggregation/replacement rule. Treat `92→96` as an important counterexample to naively interpreting bars as cumulative damage to an immutable group.

## 3. Significant confound at R80→R81

R80 appears to be an **open field** setup, with player's seven main slots at `0(-12)` and siege at `0(-6),0(-6),0(-6),0(-1)`, all confirmed casualties. R81 onward pictures show **seven castle wall sections and seven fresh `12(-0)` player units**, so it is NOT a controlled identical-formation repeat of R80. Do not attribute jump `19→84` enemy casualties to a change in Accuracy alone. Evaluate wall appearance, unit lineup, phase changes and actual reinforcement order; official timing must be proven independently.

Player screen reserve reading also suggests 1184 at R80 and 1100 from R81 onward, a drop of 84, matching newly deployed seven groups ×12, but this is **only screenshot transcription** and may indicate refilling rather than new losses. Do not use it to double-count player casualties.

## 4. Candidate model families worth testing independently

1. **Fixed per-slot shot address with replacement:** baseline attacks fixed target slots; ordinary units die and refill up to slot capacity. Predict repeated `35(-15)` and `42(-8)`; check whether reserve moves match previous-round casualties.
2. **Readdress targets after a cell disappears:** with N active physical slots shrinking 7→6→4, rebuild shared `attacking_matrix` and compare visibility of `16`, `25`, `22` kills, subject to casualty cap. Must not repurpose NAVAL model's 16/14 assumption.
3. **Finite-ammo/source-line phase and priority:** identify exact attacking musket position, player's other combat source units and wall source status before attributing 84–91 deaths to one type of shot. Use packaged `calculate_damage` and source unit registry to test quantitative predictions.
4. **Group-health display models:** remaining-HP weighted by live individual units, possibly survivor-only versus initial-unit denominator. Compare the non-monotonic `99,97,92,96,0` center bar. Avoid fabricating per-individual game shot histories.
5. **Reinforcement limitations:** separately audit non-axe melee reserve consumption and central axe no-refill. The observation that reserve drops correlate with non-axe losses is a stronger starting constraint than a presumed global Accuracy parameter.

For every candidate, retain exact scene/round scope, unit-ID mapping confidence, high-vs-low provenance, predicted casualty counts by **slot**, reserve residuals and user-provided health percentages. Mark each compatible / incompatible / underdetermined. Never modify the production engine merely to get 806 casualties.

## 5. Long-lived audit references

- [Issue #71](https://github.com/hun186/Ikariam-Battle-System/issues/71) tracks this **Land** sequence.
- `tests/fixtures/reverse_engineering/land_barbarian_rounds80_89_20261014.json` is the canonical typed numerical evidence; `tests/unit/test_land_barbarian_rounds80_89_research.py` pins confirmed totals, 49 central deaths, and the reserve reconciliation checks.
- Original screenshot filenames are listed in the JSON fixture but **the images are not committed to Hosted GitHub**; preserve them in this ChatGPT conversation. Do not claim an AI in a new conversation can visually inspect them without reattaching/uploading.
- NAVAL model studies remain separate in Draft PR #69 and [Issue #68](https://github.com/hun186/Ikariam-Battle-System/issues/68); do not use inferred naval 74% or F(A,N) as verified Land calculations.
- To resume: verify Hosted main, Land research Draft PR and exact-head review; run `python -m pytest -q tests/unit/test_land_barbarian_rounds80_89_research.py` and then full `python -m pytest -q`; compare current Land engine event traces against observed within-round casualty maps. Observe the rule that a change in front formation or reserve levels is not a change in the target-selection algorithm.

**Status:** Separate user-confirmed observations and research cases. No official focus mechanism has yet been inferred, and no production combat formula changes are authorized.


## 6. Two-target-class AM reconstruction and the owner's seven-bullet reroute insight (2026-10-14)

The owner confirmed actual player **Forge Lv5** (in addition to Workshop ATT11 / DEF3). **Packaged Barbarian profiles**: `barbarian_knifeman` HP360 armor0 and `barbarian_axe_swinger` HP1120 armor20. Player Sulphur Carabineer primary base attack580, Accuracy70, primary ammo3; land Workshop ATT +5/level. Thus `580+11×5=635`, after Forge Lv5 ×1.15 = 730.25, yielding **730 to Knifeman** and **710 to Axe**, after floor and armor. Fresh knife takes one full 730 hit; fresh axe takes two appropriately **concentrated** 710 hits. Forge0 635/615 figures shown in older models are **counterfactual**, not measurements of this battle.

### 6A. R81–R83 exactly matches a two-class, two-source **conditional** model

Current Land `_shot_rows([12]*7)` produces **84 model-addressed hits**, using `land-max` central-first damage-position physical mapping `[6,4,2,1,3,5,7]`. The 12 AM source rows have seven attacks each; damage positions1–5 receive two sets of seven and positions6–7 one, producing **physical L→R address counts `[7,14,14,14,14,14,7]`**. The central physical fourth cell is the special axe; others have knife icon.

User has ALSO separately confirmed the **high-level wall can kill one Barbarian on an effective hit**. **For this research calculation only**, additionally assume all seven visible wall sections fire one successful lethal shot every walled round and each first attacks the directly opposing occupied physical cell, with an unverified fallback for empty facing cells. This one-each wall distribution is **not verified observed Gameforge shot telemetry**. Then:

| R81–83 per-position L→R | 1 knife | 2 knife | 3 knife | 4 axe | 5 knife | 6 knife | 7 knife |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current gun AM source address count | 7 | 14 | 14 | **14** | 14 | 14 | 7 |
| Conditional wall lethal hits | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| Feasible modeled deaths *only with individual Axe paired-hit focus* | 8 | 15 | 15 | **7+1=8** | 15 | 15 | 8 |
| **User-confirmed true round deaths** | **8** | **15** | **15** | **8** | **15** | **15** | **8** |

This is **one feasible** death-vector allocation with confirmed Forge5 730/710 attack values, **14 complete Axe hits paired onto seven distinct fresh Axes**, and independently hypothetical one-effective-wall-hit per physical slot. Assigning one hit each to fourteen fresh axes instead gives **zero** gun Axe deaths. Therefore the exact table arithmetic **does not prove** individual concentration, active firing/ammunition count, game Accuracy, or wall targeting.

### 6B. R84–R87: an extra **seven** knife kills corresponds to **ONE seven-shot AM source row**

Source-observed from R84: `[15,15,15,5,15,15,8]`; R86 central six kills; remaining knife numbers same. If walls still cause exactly **one kill per occupied physical position**, then:
- R81–83 knife deaths `76−6 wall =70` required gun knife kills; 84−70 =14 hypothetical center-addressed full gun hits. **Only with pairwise individual focus** do fourteen 710-point Axe hits kill seven fresh Axes; together with an assumed one-kill wall this yields the observed eight. A fourteen-way spread over healthy Axes does not.
- R84/85/87 knife deaths `83−6 wall =77 gun knife hits`; gun remaining **`84−77=7`** for axes, while observed axe total is **five**.
- R86 similarly knife gun hits77 and remaining axe-directed gun hits7, but user observed **six** axe deaths.
- Of knife positions, **ONLY physical slot1** has seven MORE knife deaths compared with baseline `8→15`; the other five knife positions do not change. The entire seven-hit difference is a single source AM row, not an arbitrary guessed percentage. In the current baseline, central physical slot4 is damage-position1 and receives 7 hits in source row1 **plus seven more in source row8**. Leftmost physical slot1 is damage-position6 and receives only 7 in row6. Readdressing the hypothetical **second group of seven guns (AM row8)** from center physical4 to leftmost physical1 would yield model gun addresses `[14,14,14,7,14,14,7]` and **exactly 83 knife casualties after adding the wall assumption**, while preserving the total 84 full gun shots. This **does not establish WHY a row would be rerouted**. Notably the preceding center axe survivors go from R82 `29` (start R83) to R83 `21` (start R84); this crosses **half of a 50-unit physical first-slot maximum** (29→21), a falsifiable *hypothesis* for reduced target priority, **not** a confirmed game selector.

**Severe after-battle HP constraint:** For center with 7 guns after the hypothetical reroute, assuming a wall directly kills one axe:
- R84/85/87: if all seven center gun attacks deliver full exclusive **Forge5 damage710** and the hypothetical wall independently kills exactly one Axe, four gun Axe deaths with seven attacks require at least **one** Axe with ≥**410** previous damage *under paired individual concentration and no other HP redistribution/source*. This is not a real-game inferred wound.
- R86: similarly five gun Axe deaths with seven exclusive full 710-damage hits require at least **three** previously one-hit-ready axes, each with ≥**410** damage (≥**1230** total), **only in the restricted per-individual full-hit model**, not from observed Gameforge hit logs.
- **Strict additional premises for comparing R83/85/86 ending bars to next-round required injuries:** the prior screenshot and next-round preattack set must represent **the same surviving Axe individual identities carrying unchanged wounds**, with exact compatible phase/snapshot timing; no inter-round RR, SR, IR, healing, replacement, rebuild, or other HP-state transition; and the UI bar must equal **floor of the average HP of those very survivors**. Under *all* these unverified premises, the conditional needed wounds would constrain R83 with 21 axes at99% to max `100×(1−410/(21×1120))≈98.26%` (floor98), R85 with 11 at92% to max `100×(1−1230/(11×1120))≈90.02%` (floor90), and R86 with 5 at96% to max `100×(1−410/(5×1120))≈92.68%` (floor92). R84 with16 at97% could support one 410-injured survivor. These are **conditional mathematical contradictions only**, not falsification of real Gameforge mechanisms.
- The UI aggregation, same-population continuity, RR/SR/IR transitions, exact wall shots and exclusive gun targeting are **not verified**. Consequently the Forge5 restricted seven-hit plus presumed stable-HP model exhibits conditional bar inconsistencies, but **nothing here proves the actual battle lacked a feasible allocation**. Investigate other target distributions, wall aim, hidden source/ammo changes and Gameforge HP bar semantics; do not hardcode a seven-hit AM-row diversion.

### 6C. The same source model reproduces R88/R89 **and** the proposed wall fallback

When the special axe is gone, all visible targets are the one-hit knifemen, and source reserve becomes empty. The 84-shot conditional model redistributes AM **over the remaining occupied target slots**:
- R88 has **six** occupied positions (1–6). The 12 rows each contain 7 source shots; modulo six target addresses makes **14 gun shots per occupied target**. To get the source **`[16,15,15,15,15,15]`** kills, a wall address vector `[2,1,1,1,1,1]` fits **exactly**: 7 successful wall hits total, one facing each of six occupied positions plus one orphaned wall's attack rerouted to leftmost physical1.
- R89 has **four** occupied positions (physical2–5). AM predicts **21 gun shots each**. Proposed wall vector `[4,1,1,1]` gives **`[25,22,22,22]`** exactly: three orphaned wall attacks from missing physical1/6/7 redirected to **leftmost occupied physical2**, on top of its own wall hit. This is a very precise **numerical fit** to the owner's conjecture, not direct evidence of the true wall's target-address priority.

**Counterpoint:** If all seven wall strikes were passed through the present `_shot_rows([1]*7)` shared-source AM, they would all be in source row1 and map to the **first damage-priority cell**, NOT to one directly opposite each wall segment. Therefore the owner's *local-facing wall then fallback* proposal is a distinct candidate mechanic, not a verified reuse of the ordinary AM for a seven-wall formation. The current engine explicitly records `wall_offense_modeled: false`, so this needs a research-specific rule rather than a covert production change.

### 6D. Ammunition / source identity is a serious remaining confound

The packaged Sulphur Carabineer primary ammunition is **3 per unit**, while the images show seven groups labeled12 across many consecutive rounds. If precisely the same 84 musketeers fired their primary once for each of **nine** rounds, their 3-shot-per-unit ammunition pool would be exhausted. This could be explained by fresh waves, rotations, using another weapon, mistaken image-unit identification, unknown shot eligibility/refresh behavior or battle-report semantics, but has **NOT been established** from the screenshots. No conclusion about the universal Accuracy rule should ignore this contradiction. The target-class hit-to-kill and AM row counting above is conditional on 84 *valid effective* long-range attacks every analyzed round, NOT proof those occurred historically.

The independent source-aware executable audit `tools/research/land_round80_89_two_class_am_probe.py` outputs an artifact of all rounds, official-profile HP/attack/ammo, the exact AM+wall breakdown, the proposed one-source-row redirection, minimum pre-existing axe wounds, and conditional comparisons against preceding group HP bars. New regression `tests/unit/test_land_round80_89_two_class_am_probe.py` protects these equations. CI `.github/workflows/land-barbarian-round80-89-focus-research.yml` uploads this artifact without any changes to production targeting/damage code.
