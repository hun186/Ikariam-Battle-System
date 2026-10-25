# P0 — Naval R1/R2 source archive for *any* fleet (no model-matching claim)

**Issue #73 · research-only**. This follows owner-merged [PR #87](https://github.com/hun186/Ikariam-Battle-System/pull/87) at Hosted `main` `dd7f5fb3cc6cb1abd526b7ffd464ce9e40f55acb`.

## Why another stage is necessary

PR #87's `p0_gameforge_naval_capture_intake.py` deliberately refuses conditional HP comparison unless source data **exactly matches** one invented **naval-max** Tender=1 research control (units, Forge, upgrades, timing and known model Wave labels). Actual Gameforge battles with different fleets or missing setup must **not** be treated as confirming/refuting that synthetic control. But their source transcriptions are still valuable and should not be discarded.

This PR adds a separate, permissive **but provenance-safe archival stage**. It records **user-supplied metadata** about an arbitrary real naval battle, including incomplete observations, WITHOUT trying to fit any game damage/healing model. Neither file existence, underlying PNG bytes, screenshot authenticity nor in-game timestamps are inspected. The historical owner's 53%/65% Carrier bars are from a different **in-sample** case; this tool does not silently create or attach those screenshots.

## Use

```bash
PYTHONPATH=. python tools/research/p0_naval_capture_archive.py \
  --write-template research-output/EMPTY-naval-archive.json

# Fill your own copy using user-transcribed observations and source references.
PYTHONPATH=. python tools/research/p0_naval_capture_archive.py \
  --input real-battle-transcription.json \
  --output-json real-battle-unverified-archive.json
```

Template fields include `record_kind=empty_template_not_an_observation`, `record_id`, three optional source references (`r1_end`, `r2_prefire`, `fleet_setup`), `battle_context` and an initially **empty** observation array. A substantive record must explicitly use `record_kind=user_transcribed_unverified`. Each observation has a known `phase` (`r1_end` or `r2_prefire`), `side`, `unit_id`, `wave_label` (may be unknown), `physical_slot_label` (may be unknown), whole-number `visible_percent` or null, `units_alive` or null and a screenshot `source_ref` (may be unknown).

### Status and evidence policy

| Status | Meaning |
| --- | --- |
| `EMPTY_TEMPLATE` | An empty worksheet, **no battle** |
| `UNVERIFIED_ARCHIVE_READY` | All expected **typed, self-declared** metadata present, **NOT an authenticated game observation** |
| `UNVERIFIED_ARCHIVE_INCOMPLETE` | Typed user transcription retained, with explicit missing or conflicting phase/source/slot fields |
| `INVALID` | Forbidden proof assertions, invalid types or values, inconsistent duplicated physical Slot identities; no submitted record copied into output |

`user_submitted_record` includes the **actual input JSON unchanged**, not observations invented by the program. `missing_for_followup` lists precisely what a researcher can ask the player to supply. `user_record_sha256` is a stable canonical hash of the **JSON transcription text interpreted as data**, NOT a hash of an original Gameforge screenshot; changing the transcription changes the digest but does not make it authentic.

The only automatic source-scope hint, `synthetic_setup_comparison`, reads PR #87's reference control fields and says whether the **submitted setup** matches them. This **does not execute HP model matching** or verify physical game addresses. Source records from entirely different naval fleets can still be archived with a nonmatch. If the user wants the 10 old Tender HP hypotheses screened, they must separately satisfy **all** PR #87 strict intake assumptions, real source identity and user asserted exact model Wave/Slot mapping.

### Fail-closed integrity rules

Reject unsupported fields that purport to prove official Gameforge mechanics, NaN/bool/negative survivor or percent values, invalid phases/sides, nonsensical workshop upgrade types and duplicate **labeled** Slot identities within the same side/wave/phase. A Slot may legitimately appear in both phases. An unlabeled or missing image reference produces a follow-up diagnostic, not a false synthetic game event. Valid input from a different fleet is not `INVALID`.

The output always states `independently_verified_game_observations=0`, `independent_holdouts=0`, `game_screenshot_contents_verified=false`, `official_game_mechanism_verified=false` and `conditional_hp_model_comparison_performed=false`. These counters describe what **this tool verifies**, not a claim that no real game was played.

**No screenshots were obtained for this PR; no official healing, RR, Accuracy, low-HP kill, focus/overkill, Gameforge rounding or target-selection mechanics inferred; no production simulator formula changed.** Issue #73 remains OPEN. Merge only after exact-HEAD Hosted CI and formal Codex Review, with new explicit owner authorization.


## Formal Codex Review round 1 — archive completeness repairs

Formal Codex review of initial PR #88 HEAD `72a01e483fc943340760509dd78f6eb61aa24d36` **completed with two P2 findings**, despite prior Hosted CI being all green:

1. **Omitted setup keys crash archive:** Missing `battle_context.battlefield_id`, `attacker_forge_level` or `defender_forge_level` were correctly allowed as partial user transcriptions, but the informational `_compare_setup()` read them by `ctx[...] ` and crashed with `KeyError` before writing the result. The comparison now uses `ctx.get(...)` and safe nested workshop/defender dict access. The result remains `UNVERIFIED_ARCHIVE_INCOMPLETE`, the omitted data is not invented, and the informational old-control match is **false**.
2. **Nonempty containers concealed missing nested setup values:** A declared unit with `quantity=null`, a Workshop entry with `attack=null` / `armor=null`, or `workshop_upgrades={"carrier": {}}` was treated as fully complete because only the parent dict was checked. After validating allowed types, archival readiness now includes **per-unit quantity and per-Workshop attack and armor** follow-up diagnostics. Those are preserved as unknown and yield `UNVERIFIED_ARCHIVE_INCOMPLETE`, not `INVALID`, since the source record remains valuable.

Regression tests cover omitted or explicit-null battlefield/Forges, nested unknown attack/defense population and upgrades, empty workshop entry, and unchanged complete records. These fixes are **research data-integrity only**; they do not authenticate images or modify the simulator. A new exact-HEAD Hosted CI and **fresh Codex Review** are required after these fixes. Do not mistake the first completed review for approval.


### Formal Codex review round 2: missing per-Slot survivor counts (P2)

A second formal review of HEAD `22460f777f634a0a7841661c9fd48cbe6bfacde7` **completed with one new P2**, after both earlier P2s were fixed. The reviewer found that an R1/R2 observation could omit `units_alive` or declare `units_alive: null` and still receive `UNVERIFIED_ARCHIVE_READY`. This made the source appear complete even though the per-Slot living unit count was unknown. The archival validator now adds **`observations[i].units_alive`** to `missing_for_followup` for either absent or explicit-null population, retains the original manual transcription and classifies it as **`UNVERIFIED_ARCHIVE_INCOMPLETE`**. Any reported population must remain a positive integer; zero, negative, boolean, decimal and string are still INVALID. Regression tests cover both R1 and R2 for missing/explicit-null values, invalid typed input and filled-count READY records.

Neither old nor new P2 findings establish authentic Gameforge mechanics or source provenance. This is a **research archival completeness** correction only. Updated exact-HEAD Hosted CI and a fresh formal Codex Review are required before any owner-approved Merge.


### Formal Codex review round 3: whitespace-only archival labels and references (P2)

Formal Codex review of former HEAD `0fa4f8f8fb19790439ab939c1617710c2e68b915` **completed with one new P2** even though the 13 current-HEAD Hosted checks were green and the prior three P2s had been corrected and resolved. The archival completeness check used Python truthiness on source-reference fields, `wave_label` and `physical_slot_label`; a supplied string consisting only of spaces or tabs counted as present. Even the same physically unknown blank-wave/blank-slot observation repeated could produce `UNVERIFIED_ARCHIVE_READY` with no follow-up.

The updated research archival rule uses one `_nonblank` predicate for record/source references and per-R1/R2 observation source/Wave/Slot labels. Whitespace-only fields remain **preserved verbatim** in user-supplied JSON and its transcription-only SHA-256 but count as **missing** for follow-up, producing `UNVERIFIED_ARCHIVE_INCOMPLETE`. Duplicate unknown labels do not silently prove unique physical-slot identity. The prior duplicate *nonblank* labeled Slot protection remains. New adversarial regression tests cover whitespace-only record IDs, three screenshot/fleet references, per-phase observation references, both Wave/Slot labels, coordinated whitespace source refs, duplicate whitespace-only Wave/Slot transcriptions and genuinely populated READY observations.

There were **no new independent Gameforge observations or real PNG images**. All original 53%/65% Carrier history remains separate from invented test fixtures, the game simulator is unchanged, and a NEW exact-source Hosted CI and formal Codex review are required before any owner-authorized Merge. This third-round review **does not approve** the corrected source.
