"""Bind locally supplied naval screenshot BYTES to an unverified PR #88 archive.

Research-only: this establishes a SHA-256 fingerprint of named local files,
NOT image authenticity, Gameforge provenance, date, slot mapping, or mechanics.
Never download references or publish/attach user screenshots.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import stat

from tools.research import p0_naval_capture_archive as archive_module

SCHEMA = "p0_naval_capture_local_image_manifest_v1"
RESULT_SCHEMA = "p0_naval_capture_local_image_binding_result_v1"
MAX_IMAGE_BYTES = 20 * 1024 * 1024
ALLOWED_FORMATS = frozenset(("png", "jpeg"))


def blank_manifest() -> dict:
    """Explicitly EMPTY worksheet, not evidence of a real battle."""
    return {"schema": SCHEMA, "record_kind": "empty_manifest_no_images", "images": []}


def _nonblank(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _digest(value) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(ch in "0123456789abcdef" for ch in value))


def _safe_relative(value: str) -> bool:
    if (not _nonblank(value) or value != value.strip()
            or "\\" in value or ":" in value or "\x00" in value
            or len(value) > 240):
        return False
    pp = PurePosixPath(value)
    # Do not normalize-away dot/dotdot, absolute, repeated or empty components.
    parts = value.split("/")
    return (not pp.is_absolute() and all(p not in ("", ".", "..") for p in parts)
            and all(not p.startswith("~") for p in parts))


def _file_digest(root: Path, relative_path: str) -> dict:
    """Hash local bytes below the chosen root without following path-swap symlinks.

    POSIX directory descriptors anchor each lookup to the directory actually
    opened, not to a pathname checked earlier. Fail closed where these
    guarantees are unavailable. This is byte integrity, not image provenance.
    """
    if not _safe_relative(relative_path):
        raise ValueError("unsafe relative image path (no absolute, parent, URI, or backslashes)")
    if (not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY")
            or os.open not in getattr(os, "supports_dir_fd", ())):
        raise ValueError("secure directory-relative nofollow opens unavailable on this platform")
    if not root.is_dir() or root.is_symlink():
        raise ValueError("evidence root must be an existing nonsymlink directory")

    flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_BINARY", 0)
    directory_flags = flags | os.O_DIRECTORY
    # Even if the named root is replaced after the prior is_dir check,
    # O_NOFOLLOW refuses a replacement symlink at this final component.
    root_fd = os.open(root, directory_flags)
    parent_fd = root_fd
    parts = relative_path.split("/")
    try:
        # Never reconstruct a full child path: all later opens use the
        # directory FD already opened on the preceding component.
        for part in parts[:-1]:
            child_fd = os.open(part, directory_flags, dir_fd=parent_fd)
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = child_fd
        # Nonblocking protects against an attacker swapping in a FIFO just
        # before opening; fstat below admits regular files only.
        fd = os.open(parts[-1], flags | getattr(os, "O_NONBLOCK", 0),
                     dir_fd=parent_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("evidence source must be a local regular nonsymlink file")
            if info.st_size <= 0 or info.st_size > MAX_IMAGE_BYTES:
                raise ValueError("empty or oversized evidence image")
            hasher = sha256()
            prefix = b""
            tail = b""
            seen = 0
            while True:
                block = os.read(fd, 65536)
                if not block:
                    break
                seen += len(block)
                if seen > MAX_IMAGE_BYTES:
                    raise ValueError("image exceeds per-file size limit")
                hasher.update(block)
                if len(prefix) < 24:
                    prefix += block[:24 - len(prefix)]
                tail = (tail + block)[-2:]
            if not seen:
                raise ValueError("empty image")
            suffix = Path(parts[-1]).suffix.lower()
            if (suffix == ".png" and prefix.startswith(b"\x89PNG\r\n\x1a\n")
                    and len(prefix) >= 24 and prefix[12:16] == b"IHDR"):
                kind = "png"
            elif (suffix in (".jpg", ".jpeg") and prefix.startswith(b"\xff\xd8\xff")
                  and tail == b"\xff\xd9"):
                kind = "jpeg"
            else:
                raise ValueError("file extension and basic PNG/JPEG signature inconsistent")
            return {
                "sha256_file_bytes": hasher.hexdigest(),
                "byte_size": seen,
                "basic_signature_matches_extension": True,
                "format_signature_only": kind,
                "image_decoded_or_visually_inspected": False,
            }
        finally:
            os.close(fd)
    finally:
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)


def bind_files(record: dict, manifest: dict, evidence_root: Path) -> dict:
    """Return source/byte-integrity diagnostics, never empirical validation."""
    errors: list[str] = []
    missing: list[str] = []
    checked: list[dict] = []
    report = {
        "schema": RESULT_SCHEMA,
        "status": "INVALID",
        "manual_transcription_status": "NOT_EVALUATED",
        "manual_transcription_sha256": None,
        "files": checked,
        "missing_or_unbound_source_refs": missing,
        "invalid_manifest_or_file_errors": errors,
        "local_file_bytes_read": 0,
        "original_game_screenshots_authenticated": False,
        "source_provenance_independently_verified": False,
        "independently_verified_game_observations": 0,
        "independent_holdouts": 0,
        "official_game_mechanism_verified": False,
        "game_combat_hypothesis_comparison_performed": False,
        "notes": [
            "Local file hashing shows byte identity/integrity only, NOT that the image comes from Gameforge.",
            "PNG/JPEG header checks are NOT full image decoding or visual interpretation.",
            "A user-entered expected hash is NOT an independent provenance anchor.",
            "No image file bytes or full paths are included in the JSON result or uploaded to GitHub.",
        ],
    }
    if not isinstance(record, dict):
        errors.append("record: expected archive object")
        return report
    try:
        archive_result = archive_module.archive(record)
    except (KeyError, TypeError, AttributeError, ValueError):
        errors.append("record: malformed transcription could not pass archive validation")
        return report
    report["manual_transcription_status"] = archive_result["status"]
    report["manual_transcription_sha256"] = archive_result["user_record_sha256"]
    if archive_result["status"] not in (
            "UNVERIFIED_ARCHIVE_READY", "UNVERIFIED_ARCHIVE_INCOMPLETE"):
        errors.append("record: valid nonempty user_transcribed_unverified archive required")
        return report
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "record_kind", "images"}:
        errors.append("manifest: only schema, record_kind, images allowed")
        report["status"] = "INVALID_OR_HASH_MISMATCH"
        return report
    if manifest["schema"] != SCHEMA or manifest["record_kind"] != "user_supplied_unverified_files":
        errors.append("manifest: wrong schema or source classification")
        report["status"] = "INVALID_OR_HASH_MISMATCH"
        return report
    images = manifest["images"]
    if not isinstance(images, list) or len(images) > 3:
        errors.append("manifest: images must be an array of at most 3 entries")
        report["status"] = "INVALID_OR_HASH_MISMATCH"
        return report
    refs = record.get("source_refs")
    if not isinstance(refs, dict):
        errors.append("record: invalid source_refs")
        return report
    declared = [v for v in refs.values() if _nonblank(v)]
    if len(set(declared)) != len(declared):
        errors.append("record: ambiguous duplicate source_ref across R1/R2/fleet stages")
        report["status"] = "INVALID_OR_HASH_MISMATCH"
        return report
    known = set(declared)
    seen_refs: set[str] = set()
    bound_refs: set[str] = set()
    seen_paths: set[str] = set()
    for i, entry in enumerate(images):
        label = f"images[{i}]"
        if not isinstance(entry, dict) or set(entry) != {"source_ref", "relative_path", "expected_sha256"}:
            errors.append(f"{label}: requires exactly source_ref, relative_path, expected_sha256")
            continue
        source, relative, expected = (
            entry["source_ref"], entry["relative_path"], entry["expected_sha256"])
        if not _nonblank(source) or source not in known:
            errors.append(f"{label}: source_ref does not match a declared nonblank source stage")
            continue
        if source in seen_refs:
            errors.append(f"{label}: duplicate source_ref entry")
            continue
        seen_refs.add(source)
        if not isinstance(relative, str) or not _safe_relative(relative):
            errors.append(f"{label}: unsafe relative_path")
            continue
        if relative in seen_paths:
            errors.append(f"{label}: same image path bound to multiple stage refs")
            continue
        seen_paths.add(relative)
        if expected is not None and not _digest(expected):
            errors.append(f"{label}: expected_sha256 must be lowercase SHA-256 hex or null")
            continue
        try:
            verified = _file_digest(Path(evidence_root), relative)
        except (ValueError, OSError) as exc:
            errors.append(f"{label}: unreadable / malformed local image ({type(exc).__name__})")
            continue
        report["local_file_bytes_read"] += verified["byte_size"]
        checked_entry = {
            "source_ref": source,
            "relative_path": relative,
            **verified,
            "expected_sha256_supplied": expected is not None,
            "supplied_hash_matches_actual_bytes": (
                None if expected is None else expected == verified["sha256_file_bytes"]
            ),
        }
        checked.append(checked_entry)
        if expected is not None and expected != verified["sha256_file_bytes"]:
            errors.append(f"{label}: expected SHA-256 does not match local bytes")
        else:
            bound_refs.add(source)
    # Different local file paths can be copies or hard links of the SAME
    # image bytes. Such byte-identical inputs cannot independently distinguish
    # R1-end from R2-prefire (or setup) source stages even if the submitter
    # supplied a matching expected hash for each. Reject ALL ambiguous stage
    # bindings, without asserting that legitimate scenes cannot look alike.
    digest_refs: dict[str, set[str]] = {}
    for file_entry in checked:
        digest_refs.setdefault(file_entry["sha256_file_bytes"], set()).add(
            file_entry["source_ref"]
        )
    for stage_refs in digest_refs.values():
        if len(stage_refs) > 1:
            errors.append(
                "identical image bytes attached to distinct source stages: "
                + ", ".join(sorted(stage_refs))
                + "; confirm separate captures (same SHA-256)"
            )
            bound_refs.difference_update(stage_refs)
    # Mark a stage bound ONLY after its local bytes have been successfully
    # read and its optional expected digest has matched.
    for ref in sorted(known - bound_refs):
        missing.append(ref)
    if errors:
        report["status"] = "INVALID_OR_HASH_MISMATCH"
    elif missing or archive_result["status"] == "UNVERIFIED_ARCHIVE_INCOMPLETE":
        report["status"] = "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    elif not images:
        report["status"] = "UNVERIFIED_PARTIAL_SOURCE_BUNDLE"
    elif all(entry["expected_sha256_supplied"] for entry in checked):
        report["status"] = "LOCAL_HASHES_MATCH_UNAUTHENTICATED"
    else:
        report["status"] = "LOCAL_BYTES_FINGERPRINTED_UNAUTHENTICATED"
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-template", type=Path)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--manifest", type=Path)
    ap.add_argument("--evidence-root", type=Path)
    ap.add_argument("--output-json", type=Path)
    args = ap.parse_args()
    if args.write_template is not None:
        if any(x is not None for x in (
                args.record, args.manifest, args.evidence_root, args.output_json)):
            ap.error("--write-template cannot be combined with binding arguments")
        dest, result = args.write_template, blank_manifest()
    else:
        if any(x is None for x in (
                args.record, args.manifest, args.evidence_root, args.output_json)):
            ap.error("provide --record --manifest --evidence-root --output-json")
        dest = args.output_json
        result = bind_files(
            json.loads(args.record.read_text(encoding="utf-8")),
            json.loads(args.manifest.read_text(encoding="utf-8")),
            args.evidence_root,
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status", "EMPTY_TEMPLATE"), "output": str(dest)}))
    if args.write_template is None and result["status"] in ("INVALID", "INVALID_OR_HASH_MISMATCH"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
