# P0 — Low-HP formation timing and casualty-focus acceptance matrix

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

## Remaining P0 implementation gate

- [ ] Get real source-tagged gyrocopter-vs-gyro, gyro-vs-balloon and more asymmetric swordsman casualty/bar screenshots. Keep *Gameforge observations* distinct from above synthetic scenario tests.
- [ ] Reconcile per-slot deaths **AND living HP** with discrete shot allocation, stage start eligibility, source ammo, actual Workshop/Forge, odd/partial AM and cross-round reserve/redistribution.
- [ ] Integrate a bounded experimental kill/distribution selector only when a consistent multi-case model exists; keep official Strict UNKNOWN guard until independent verification.
- [ ] Extend full-heal Doctor/Tender scenarios for round1→round2+ with casualties fixed and repairs excluding dead units; partial-heal rules remain explicitly UNKNOWN until verified.
- [ ] Exact-head Hosted CI & Codex Review and owner permission for any merge.

**This baseline PR does NOT implement or assert the unverified general Gameforge Accuracy, D/P/IR/SR/RR selector.** It protects the already-known firing semantics while prioritizing focused calibration.
