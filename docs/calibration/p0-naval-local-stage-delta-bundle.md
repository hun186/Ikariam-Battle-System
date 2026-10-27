# P0 Naval: local screenshot-byte gated R1-end/R2-prefire deltas

**Issue #73 — research only, NOT a Gameforge authentication process.**

PR #91 protects against byte-identical captures across distinct stages; PR #92
and #93 produce conservative per-slot user-transcription arithmetic. The tools
previously ran independently. This new local-only CLI calls BOTH the existing
secure original-image binder and the archive-v2 stage-pair comparator on the
SAME user-supplied in-memory record, refusing to publish plausible deltas when
its R1-end or R2-prefire image is absent, tampered, ambiguous or unsafe.

Example (user's real data remains outside GitHub):

    PYTHONPATH=. python tools/research/p0_naval_local_stage_delta_bundle.py --record ./private-archive-v2.json --manifest ./private-image-manifest.json --evidence-root ./private-game-images --output-json ./private-naval-stage-byte-gated-deltas.json

Manifest format is from p0_naval_capture_local_image_manifest_v1. R1/R2 stage
source refs must match the PR #88 archive-v2 input. Local image files must be
regular and nonsymlinked inside the evidence root (secure descriptor-relative
open on POSIX), with basic PNG/JPEG signatures and size <=20 MiB per file.

The tool compares the CURRENT archive transcription digest with the binder's
digest computed from the same input; it never accepts an older external report.
Both stage refs must have local file-byte SHA-256 fingerprints, match any
submitted expected hash, and have distinct actual byte digests. A missing
(optional) fleet-setup image may leave the original binder result partial but
does not prevent R1/R2 byte gating; missing either required R1 or R2 DOES.

## Report statuses

- UNVERIFIED_STAGE_DELTAS_LOCAL_BYTES_BOUND: distinct local bytes are bound
  to the two user-labelled stages, and all stage-pair rows pass the existing
  transcription pairing rules. Neither source nor identity is authenticated.
- UNVERIFIED_PARTIAL_STAGE_DELTAS_LOCAL_BYTES_BOUND: both stage byte files are
  found, but missing or ambiguous observations, uncertain R2 timing, or
  reinforcements leave only partial/no provisional deltas.
- UNVERIFIED_STAGE_BYTES_UNBOUND: required stage refs lack a complete local
  source binding. Never emits provisional deltas; CLI exits 2.
- INVALID_OR_HASH_MISMATCH: archive invalid, malformed local manifest or
  image file, unsafe path/symlink, duplicate stage bytes, supplied-hash
  mismatch or invalid stage bundle. Never emits provisional deltas;
  CLI exits 2.

Output includes current JSON transcription SHA-256, stage-local image-byte
digests, status, conservative source-ref diagnostics, and eligible **arithmetic
differences ONLY**. It never copies image file bytes, image paths or the
submitted whole transcription record. The output itself is private and should
not be committed to GitHub.

**Important:** two different file-byte hashes do not prove two different
authentic in-game stages, Gameforge origin, real ship identity, timing, Tender
healing, round-robin ordering or HP-bar rounding. Every report retains zero
independently verified game observations and independent holdouts. The
synthetic CI examples contain only invented source labels and fake PNG/JPEG
headers, not actual gameplay screenshots. GitHub Actions publishes the old
EMPTY archival template, not any user's images or reports. No production
battle logic changes, Issue #73 stays OPEN.
