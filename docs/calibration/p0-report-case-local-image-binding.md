# Browser report-case local image-byte binding (research-only)

**Issue #73.** The browser report-case library exports a JSON v1 case,
pending physical-slot review CSV, and per-round source notes. Previously the
local image-byte binder served only specialized Naval R1/R2 stage archives.
This new CLI fingerprints locally chosen PNG/JPEG files against exact
captured-round IDs for an arbitrary 1–100 round browser-case backup.

**A file hash never proves Gameforge source authenticity, battle timing or
the depicted units/HP bars.** The tool neither decodes images nor infers
battle formulas. Do not commit private screenshots or derived private
receipt paths to GitHub.

## Operation on a trusted Linux/POSIX workstation

Run from the cloned repo root with Python 3.11+ and Node available.
The secure local file reader requires POSIX `O_NOFOLLOW` and
directory-relative `os.open(..., dir_fd=...)`. It deliberately fails closed
on unsupported systems, including most native Windows setups.

1. Export a JSON case from the browser and store original screenshots
   outside GitHub.
2. Create an EMPTY manifest worksheet:

       python -m tools.research.p0_report_case_local_image_binding \
         --write-template private-image-manifest.json

### Case-bound worksheet (recommended; Draft PR #112)

Instead of manually copying opaque capture IDs, generate a **case-bound
draft worksheet** from the actual browser JSON backup. The canonical JS
validator rejects invalid cases *before creating any worksheet*:

    python -m tools.research.p0_report_case_local_image_binding \
      --case private-browser-case.json \
      --write-case-worksheet NEW-private-capture-worksheet.json

This produces exactly the normal manifest top-level keys and captures
**all manually captured rounds, sorted numerically**, with each row's
`capture_id`, `capture_round`, `capture_phase`, and deliberately
`relative_path=null`, `expected_sha256=null`. For example, an R80
end-of-round transcription appears with its actual opaque ID and
`capture_round=80`, `capture_phase=round_end`. It does NOT copy
private `round.source` note text, inspect images or claim that any
file exists. The generated `record_kind` is
`draft_capture_worksheet_not_evidence`: passing the unedited worksheet
to the image binder is **INVALID** and reads zero local image bytes.

To finalize, enter real relative PNG/JPEG paths for whichever captured
rounds actually have files; delete unfilled rows when only a partial
bundle is available. Then explicitly change `record_kind` to
`user_supplied_unverified_files`. The binder checks that the optional
`capture_round` **and** `capture_phase` match the original case for
each `capture_id`; it rejects incorrect or partially supplied metadata
before reading images. Old manifests using only `capture_id`,
`relative_path` and `expected_sha256` remain valid.

As with other CLI outputs, an existing worksheet, screenshot,
case backup or symlink/hard link is never overwritten, even when
chosen as `--write-case-worksheet` output. Do not share worksheets
containing private case IDs without reviewing them.

3. For the older empty-template route, edit it locally. Change `record_kind` to
   `user_supplied_unverified_files`, set `case_id` to the JSON case ID,
   and fill entries with exact `rounds[].id` capture IDs (not merely round
   numbers), relative file paths below the evidence root, and an optional
   `expected_sha256` (null unless already fingerprinted).

   Example placeholders, **not any observed battle**:

       {
         "schema": "p0_report_case_local_image_manifest_v1",
         "record_kind": "user_supplied_unverified_files",
         "case_id": "copied-case-id",
         "captures": [
           {"capture_id": "R80-ID", "relative_path": "R80-end.png",
            "expected_sha256": null},
           {"capture_id": "R81-ID", "relative_path": "subdir/R81-prefire.jpeg",
            "expected_sha256": null}
         ]
       }

4. Fingerprint the private local files without uploading them:

       python -m tools.research.p0_report_case_local_image_binding \
         --case private-browser-case.json \
         --manifest private-image-manifest.json \
         --evidence-root private-game-images \
         --output-json private-byte-receipt.json

**Write output to a NEW unused filename.** The CLI atomically refuses to
overwrite any existing path (including previous receipts, case backups,
manifests, screenshot image files, symlinks and hard links). On rejection it
exits 2 without modifying the old file. Save new verification runs to a
different filename, not over the prior output. This explicitly addresses
formal Codex P2 findings: template creation had a missing status key;
the first implementation could also replace source evidence when
`--output-json` accidentally pointed to an original screenshot.

Inspect the generated receipt before sharing: it contains capture IDs,
relative paths, actual SHA-256 values and file sizes, but no image bytes,
absolute local paths or original user-entered `round.source` note text.

## Verified scope and statuses

The v1 JSON is structurally validated by the canonical JS
`battle-cases-model.js` `validateCase()` through Node. This is NOT a
Gameforge authenticity check or geometry verification against optional
battlefield metadata. Case input <=64 MiB, manifest <=256 KiB; each
image <=20 MiB, secure regular file, safe relative POSIX path, matching
basic PNG/JPEG signature and streamed SHA-256. No download or upload.

| Status | Meaning |
| --- | --- |
| `LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED` | All captured rounds bound to distinct readable local bytes; optional expected digest missing. |
| `LOCAL_HASHES_MATCH_UNAUTHENTICATED` | All captures bound and all submitter-supplied expected hashes match. This is not original-game certification. |
| `UNVERIFIED_PARTIAL_SOURCE_BUNDLE` | Some rounds missing or not bound; exact capture IDs/rounds/phases listed. |
| `INVALID_OR_HASH_MISMATCH` | Unsafe or ambiguous manifest/file, invalid source hash, distinct rounds with byte-identical images; exit 2. |
| `INVALID` | Invalid v1 case, unavailable Node validator or invalid manifest declaration; exit 2. |

Different names do not imply distinct images: if two capture IDs have
identical SHA-256 bytes, both bindings become ambiguous, not evidence of
forgery. Conversely, different bytes do not independently prove screenshot
origin, timing or contents. `round.source` records only whether manually
typed note text is present; it is never an authenticated file claim.

Outputs always retain `original_game_screenshots_authenticated=false`,
`source_provenance_independently_verified=false`, zero independent
verified game observations/holdouts, and no official Gameforge
mechanism proof. No change to the browser JSON v1 schema, localStorage,
combat engine, Reserve HP, targeting, damage, Accuracy or healing.

CI fixtures are intentionally invented minimal image headers, NOT real
Gameforge screenshots. They test source IDs, partial/full receipts,
hash mismatch, duplicates, malformed JSON, forged proof declarations,
unsafe/symlink paths and CLI nonzero failures. Issue #73 remains OPEN
pending independently corroborated original battle screenshots.
