# Naval R1/R2 conditional HP-bar integer bounds

**Issue #73, research-only.** This probe combines PR #95's local R1/R2 image-byte gate with existing exact-integer inverse percentage windows. It does NOT authenticate original Gameforge screenshots, establish actual rounding, physical hull continuity, or prove Tender healing.

Prepare a private archive-v2 transcription, matching private image manifest and source PNG/JPEG files with PR #95. Then supply a separate private JSON with the schema below. **100 HP is an invented example, NOT an official Carrier value:**

```json
{
  "schema": "p0_naval_conditional_hp_assumptions_v1",
  "denominator_assumption": "constant_living_unit_hp_times_same_living_units",
  "unit_hp_by_unit_id": {"carrier": 100}
}
```

The explicit denominator hypothesis assumes each displayed slot percentage means aggregate remaining HP of currently alive units divided by their assumed total uninjured capacity. Enter user-confirmed per-unit HP integers (1..1,000,000); no official value is inferred.

Run **locally only** (private files never uploaded to GitHub):

```sh
PYTHONPATH=. python tools/research/p0_naval_conditional_hp_intervals.py --record private-archive-v2.json --manifest private-image-manifest.json --evidence-root private-images --hp-assumptions private-hp-assumptions.json --output-json private-conditional-hp-intervals.json
```

The tool first rejects unsafe, missing, identical or mismatched R1/R2 screenshot files and invalid pairings. If two locally distinct stage images and unambiguous matched rows remain, and the same nonzero alive count plus unit HP assumption exists, it calls the already audited exact-integer percent_window under three **hypotheses**: floor, nearest_half_up, ceil.

For each compatible display hypothesis it produces closed integer intervals for R1 and R2 *remaining wounds*, plus the possible R1-wounds minus R2-wounds interval. A strictly positive interval is a **conditional net HP increase only** under unchanged capacity and same real surviving hulls. It is NEVER an estimate of proven Tender repair.

If living unit counts change, a unit HP assumption is missing, capacity is too large, or a candidate display percentage cannot exist for the assumed integer denominator, the record is partial/not assessable. An invalid assumption schema or unsafe stage-image gate emits no intervals, CLI exit 2. Image byte hashes establish local integrity only, not screenshot origin or timing.

**Critical limits:** unchanged apparent live-unit counts do not prove stable individual survivors, no Reserve replacement, or actual Gameforge HP display semantics. No production engine formulas were changed, and the CI fixtures use only synthetic bytes/labels; the workflow still uploads only an EMPTY archive template.