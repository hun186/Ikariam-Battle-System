# P0 — Local image-byte integrity bindings for unverified naval R1/R2 archives

**Issue #73, research only.** Continues after owner-merged PR #88 (main 3a1852dc847c4abfb29506ff2d428b35796de3ba).

PR #88 calculates a stable SHA-256 for the **JSON transcription only**, NOT the actual Gameforge screenshot bytes. This follow-on tool calculates SHA-256 of locally supplied original PNG/JPEG file bytes and binds each digest to a declared archival source-reference label. A byte hash neither authenticates Gameforge as the publisher nor demonstrates the image really depicts R1 end, R2 prefire, or that any HP or healing inference is correct. The image is NOT visually interpreted or decoded. Header/signature matching checks are merely format sanity checks.

## Local-only workflow

1. Create an empty image-manifest template:

    PYTHONPATH=. python tools/research/p0_naval_capture_local_image_manifest.py --write-template private-image-EMPTY-manifest.json

2. Prepare an actual PR #88 schema v2 user-transcribed-unverified record. For the new manifest, use source-ref labels already present in the record for R1 end, R2 prefire and fleet setup.

3. Place the actual images in a **private** local folder, outside GitHub. Edit the manifest images array; each entry has exactly source_ref, relative_path and expected_sha256. Supply a lowercase 64-digit SHA-256 only if a trusted prior copy has supplied a comparison digest; otherwise set expected_sha256 to null. Even a matching user-submitted expected digest is not independent provenance.

4. Run locally:

    PYTHONPATH=. python tools/research/p0_naval_capture_local_image_manifest.py --record my-naval-transcription.json --manifest my-image-manifest.json --evidence-root ./private-game-images --output-json my-image-integrity-report.json

Example MANIFEST ENTRY, illustrative source labels ONLY, **no new observed battle**:

    {"source_ref":"my-R1-end","relative_path":"r1.png","expected_sha256":null}

An empty manifest contains schema p0_naval_capture_local_image_manifest_v1, record_kind empty_manifest_no_images, and an empty images array. A filled one declares record_kind user_supplied_unverified_files. The separate original archive record must be a genuine user transcription in PR #88's current v2 format; an empty archive template is not an observed game event.

## Interpretation of results

| Status | Meaning |
| --- | --- |
| LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED | All declared named files opened and hashed locally; one or more expected hashes was absent. Not a provenance claim. |
| LOCAL_HASHES_MATCH_UNAUTHENTICATED | All supplied expected hashes match current file bytes. Still not a Gameforge certificate. |
| UNVERIFIED_PARTIAL_SOURCE_BUNDLE | Archive fields or source files incomplete, with explicit missing reference labels. |
| INVALID_OR_HASH_MISMATCH | Invalid binding, duplicate/ambiguous labels or paths, unsafe file, signature failure, excess size, or hash mismatch. CLI exit 2. |
| INVALID | No valid nonempty archive record was provided. CLI exit 2; automation must treat this as a rejection. |

The result contains source-ref strings, relative paths, byte counts, local file SHA-256 values, raw input-record SHA-256 and diagnostic messages. It NEVER includes original PNG/JPEG bytes or a copied screenshot. The tool NEVER downloads from user-supplied references or uploads them to GitHub, and CI only produces an empty template artifact.

Only PNG/JPEG signatures are accepted; paths must be relative POSIX-style and bounded within the local evidence-root folder. Absolute URLs, traversal, backslashes, symlinked files and symlinked intermediate folders are rejected. Image size is limited to 20 MiB and at most three named stage images. The tool assumes the private local directory is not concurrently being modified by a hostile process; a local byte fingerprint does not protect against an adversary altering both image and declared hash.

## Research boundary

Output flags stay fixed: original_game_screenshots_authenticated=false, source_provenance_independently_verified=false, independently_verified_game_observations=0, independent_holdouts=0, official_game_mechanism_verified=false, game_combat_hypothesis_comparison_performed=false. Existing user-reported Carrier HP bars 53%/65% remain a different unmapped historical battle and are NOT automatically converted to a synthetic Tender=1 validation example. Invented tiny image-header fixtures in tests are NOT actual Gameforge screenshots. No production simulator logic is changed. Issue #73 remains OPEN. Hosted exact-head CI, formal Codex Review and explicit owner approval are required before merging this Draft PR.
