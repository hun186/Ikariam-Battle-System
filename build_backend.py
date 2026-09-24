"""Small zero-dependency PEP 517 backend for this pure-Python project."""
from __future__ import annotations

import base64
import csv
import hashlib
from io import StringIO
from pathlib import Path
import tarfile
from zipfile import ZIP_DEFLATED, ZipFile

NAME, VERSION = "ikariam_battle_system", "0.2.0"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"


def _files():
    root = Path(__file__).parent
    for folder in ("ikariam_battle", "api"):
        for path in (root / folder).rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc": yield path
    for name in ("asgi.py", "web_simulator.py", "simulator.py"):
        yield root / name


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    filename = f"{NAME}-{VERSION}-py3-none-any.whl"
    target = Path(wheel_directory) / filename
    root = Path(__file__).parent
    metadata = f"Metadata-Version: 2.1\nName: ikariam-battle-system\nVersion: {VERSION}\nRequires-Python: >=3.11\n"
    wheel = "Wheel-Version: 1.0\nGenerator: repository-build-backend\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    entries: list[tuple[str, bytes]] = [(str(path.relative_to(root)), path.read_bytes()) for path in _files()]
    entries += [(f"{DIST_INFO}/METADATA", metadata.encode()), (f"{DIST_INFO}/WHEEL", wheel.encode())]
    rows = []
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for name, content in entries:
            archive.writestr(name, content)
            digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
            rows.append((name, f"sha256={digest}", str(len(content))))
        output = StringIO(); writer = csv.writer(output, lineterminator="\n"); writer.writerows(rows)
        writer.writerow((f"{DIST_INFO}/RECORD", "", "")); archive.writestr(f"{DIST_INFO}/RECORD", output.getvalue())
    return filename


def build_sdist(sdist_directory, config_settings=None):
    filename = f"{NAME}-{VERSION}.tar.gz"; root = Path(__file__).parent
    with tarfile.open(Path(sdist_directory) / filename, "w:gz") as archive:
        for path in [*_files(), root / "pyproject.toml", root / "build_backend.py"]:
            archive.add(path, arcname=f"{NAME}-{VERSION}/{path.relative_to(root)}")
    return filename
