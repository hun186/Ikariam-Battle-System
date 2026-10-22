# P0 — Low-HP formation timing and casualty-focus acceptance matrix

## Current merged baseline and follow-up (2026-10-23)

**GitHub canonical status:** Land PR [#74](https://github.com/hun186/Ikariam-Battle-System/pull/74) and Naval PR [#69](https://github.com/hun186/Ikariam-Battle-System/pull/69) are **both merged** to `main`; current merged head at start of this workstream: `c0021d83bc115ba15b9427ee935734d70786d5fd`. Naval combined-head Hosted Actions #39530374551 Attempt 2 passed **607 passed / 3 expected xfailed**; Codex clean at `9013f0d586`. Older references below to Draft #69/#74 are **historical research checkpoints**, not current PR status. Their bounded Experimental hypotheses have entered `main`, but **their official Gameforge correctness has NOT been established**; Strict still guards unverified mechanisms.

**NEW draft follow-up PR #75** (`research/p0-land-doctor-multiround-20261023`) fills a different acceptance gap using *real engine execution on invented synthetic armies*, not historical combat reports:

- Real `simulate()` Round1→Round2 mirrored three-Gyrocopter / three-Swordsman combat with synthetic 350-Hoplite filler. Compare identical defenses with **zero Doctors** and **50 Doctors**; Round1 losses and HP must be identical.
- Both simulations must reach Round2 and still emit actual Gyrocopter shots. Full-clear Doctor healing must happen at the Round2 boundary, repair damaged **human Swordsmen** and other eligible Humans, exclude **machine Gyrocopters**, and never raise dead units' live counts.
- Direct insufficient Doctor case uses 80 live Swordsmen with **6000 pre-existing HP wounds** versus one Doctor's **4000 HP reference capacity**. Output must preserve original wounds, emit `UNKNOWN-HEALING-ALLOCATION` / `EXP-HEAL-NONE-001` and **not** fabricate a partially healed survivor.
- Dedicated Hosted CI runs targeted Land Doctor, Land HP ledger and Naval Tender multi-round tests, followed by full pytest and compile. This PR modifies **tests / documentation / workflow only**, no `ikariam_battle` combat formula.
- Still **out of scope**: exact partial-heal allocation, Doctor/Tender Healing-versus-RR ordering, source-observed per-slot/game HP shots, general asymmetric Swordsman kill-selector proof, and official Gameforge Accuracy / P / IR / SR selectors. Do not use synthetic outcomes to claim these are solved.


Related: [Issue #73](https://github.com/hun186/Ikariam-Battle-System/issues/73), naval [Issue #68](https://github.com/hun186/Ikariam-Battle-System/issues/68) / [Draft PR #69](https://github.com/hun186/Ikariam-Battle-System/pull/69). This Land baseline starts from **merged main** commit `9a8d20feb517a71e44f5b7be9ccf4c0bae63ced2`; naval PR #69 is separate and **NOT merged**.

## Known timing versus unknown casualty formula

The in-game Art of Warfare Help (current `legacy-community-land-targeting` profile) establishes this Land firing order:

`anti-balloon → balloon → third → flank → second → first`.

**Same formation is simultaneous**: Gyrocopter ↔ Gyrocopter (both `anti-balloon`), or Swordsman ↔ Swordsman (both `flank`) get simultaneous firing eligibility snapshots. Attacker-versus-defender iteration MUST NOT let earlier side's same-phase kills suppress reciprocal shots. **Different formations are sequential**: Gyrocopter anti-balloon can kill Bombardiers before the later balloon formation phase, suppressing a dead Bombardier's fire. Do NOT apply this suppression to Gyro ↔ Gyro or Swordsman ↔ Swordsman.

| Class | HP | Weapon | Accuracy | Ammo | Production status |
| --- | ---: | ---: | ---: | ---: | --- |
| Gyrocopter | 580 | base ATK340 | 80 | 4 | Experimental within-slot Accuracy, no class-specific fully calibrated kill selector |
| Bombardier / land Balloon | 800 | base ATK960 | 20 | 2 | Experimental within-slot Accuracy, Gyro phase comes earlier |
| Swordsman | 360 | base ATK200 | 90 | infinite (registry) | Bounded symmetric two-hit full-Flank P/M hypothesis only |

These are packaged pre-upgrade/current nominal base figures. Actual damage varies with Workshop/Forge/target armor. Low HP + first-shot kill is a **model requirement**, NOT evidence that every earlier individual shot cancels later shots inside the same formation.

### Critical baseline scenarios (synthetic, NOT actual Gameforge observations)

Research regression `tests/unit/test_p0_low_hp_initiative_baseline.py`:

1. **Mirror Gyrocopter anti-balloon × anti-balloon**: identical source armies must both emit `anti-balloon` damage and suffer symmetric losses in Round1; use `hoplite` First fillers solely to keep the synthetic battle active. No claimed observed real kills.
2. **Gyrocopter anti-balloon vs Bombardier balloon**: enough gyro damage to kill the one bomber in earlier phase; bomber emits NO damage in later `balloon` phase. Paired control without gyro demonstrates bomber normally fires when alive.
3. **Swordsman full-Flank duel**: both sides produce Flank attacks, retain the existing bounded user-calibrated symmetric 2-hit mode under its exact fixture setup. A 2-hit/3-hit reciprocal controlled `swordsman_flank_kill_adjustment` input MUST reject the special-mode shortcut.
4. All above in `experimental` policy; do not make Strict silently claim calibrated Accuracy.

### Compounding healing interaction

- **Land Doctor** healing eligibility is **Human combat units**, not Gyrocopter/Bombardier `air/machine`; Swordsman is Human. Exact allocation with insufficient heal capacity and RR/Healing order remain unresolved. No casualty resurrection.
- **Naval Tender** provides **4000 HP per Tender per round** according to current v17 derived profile. Only the full-clear subset is executable: enough capacity clears surviving naval combat damage at round boundary. Insufficient capacity emits named unimplemented/experimental guard (`EXP-TENDER-HEAL-NONE-001`), NOT a correct partial-healing result. First-round casualties permanently change later ships able to fire; equal total damage != equal future strength.
- For Naval focus, the **existing separate Draft PR #69** contains conditional first-hull aggregate F(A,N), T=74 focus candidates and actual observed first-round carrier 2/2/1 vs synthetic model 2/2/2. These cannot be treated as official or code-ported into main.

### 2026-10-20 — Actual Round-1 land HP ledger tests (synthetic)

Added `tests/unit/test_p0_low_hp_hp_ledger.py` on **Draft PR #74 only**. It now
exercises the real `simulate()` damage/casualty events and Round-1 slot HP rather
than checking only timing. Synthetic mirrored 3-Gyrocopter armies with invented
350-Hoplite First-line filler must have both sides fire in `anti-balloon`,
**one casualty and 340 HP of nonzero survivor wounds on each side**, and integer conservation
`gross successful-hit damage = dead units × unit HP + surviving wounds + discarded overkill`
for both target sides. Synthetic Gyro-before-Bombardier also verifies
one 800-HP bomber casualty, correct discarded lethal overkill, and **no**
late `balloon` shot when it was already destroyed.

A direct real-engine support subset test seeds **one pre-existing death**
in both the human Swordsman and machine Gyrocopter state waves (three originally,
two living, zero reserve), proving that two Doctors clear **only** the live
human Swordsman's 200-HP wound, not the mechanically classed
Gyrocopter's 300-HP wound; live counts remain two after healing.
insufficient Doctor capacity and exact Healing/RR allocation remain UNKNOWN.
This is a **baseline conservation and eligibility guarantee**, not proof that
the underlying low-HP Gameforge Accuracy, D/P/IR/RR or attack concentration
selector is correct. No official real-game low-HP death/HP fixture was invented.

Historical code+test checkpoint `b25a2e9314427564c0ebb8d6515abf227e8ec546`:
[Hosted Actions #39353600201](https://github.com/hun186/Ikariam-Battle-System/actions/runs/39353600201)
SUCCESS — 544 passed, 3 expected xfailed (including the six original
phase-order baseline tests). Subsequent doc commits require their own
exact-Head validation and Codex Review. No merge authorization.

## Remaining P0 implementation gate

- [ ] Get real source-tagged gyrocopter-vs-gyro, gyro-vs-balloon and more asymmetric swordsman casualty/bar screenshots. Keep *Gameforge observations* distinct from above synthetic scenario tests.
- [ ] Reconcile per-slot deaths **AND living HP** with discrete shot allocation, stage start eligibility, source ammo, actual Workshop/Forge, odd/partial AM and cross-round reserve/redistribution.
- [ ] Integrate a bounded experimental kill/distribution selector only when a consistent multi-case model exists; keep official Strict UNKNOWN guard until independent verification.
- [ ] Extend full-heal Doctor/Tender scenarios for round1→round2+ with casualties fixed and repairs excluding dead units; partial-heal rules remain explicitly UNKNOWN until verified.
- [ ] Exact-head Hosted CI & Codex Review and owner permission for any merge.

**This baseline PR does NOT implement or assert the unverified general Gameforge Accuracy, D/P/IR/SR/RR selector.** It protects the already-known firing semantics while prioritizing focused calibration.

**2026-10-20 review follow-up:** Codex exact-head review of `bf1592205e` raised two P2 test-strength findings (zero gyro survivor wounds in 30v30; absent pre-existing casualties in Doctor fixture). Both corrected in `2a048c73e8a4803930aaf343323a8355afe6603c`: 3v3 exact HP ledger (1 kill, 340 HP living wounds, 1020 gross and 100 discarded excess per side), human/machine waves now each start with one historical casualty and cannot be resurrected by full-clear healing. [Hosted #39362861171](https://github.com/hun186/Ikariam-Battle-System/actions/runs/39362861171) PASS 544/3 expected xfailed. Current exact-head review status must be checked separately; these remain **synthetic**, not Gameforge observations.
