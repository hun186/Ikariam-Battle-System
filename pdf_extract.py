from __future__ import annotations

import re
import zlib
from pathlib import Path

STREAM = re.compile(br"stream\r?\n")
ARR = re.compile(br"\[(.*?)\]\s*TJ", re.S)
PARENS = re.compile(br"\((.*?)\)", re.S)
SINGLE = re.compile(br"\((.*?)\)\s*Tj", re.S)


def extract_text(pdf_path: Path, max_streams: int | None = None) -> str:
    b = pdf_path.read_bytes()
    lines: list[str] = []
    seen = 0
    for m in STREAM.finditer(b):
        s = m.end()
        e = b.find(b"endstream", s)
        if e < 0:
            continue
        raw = b[s:e].rstrip(b"\r\n")
        try:
            dec = zlib.decompress(raw)
        except zlib.error:
            continue
        if b"BT" not in dec:
            continue
        seen += 1
        if max_streams is not None and seen > max_streams:
            break

        # Parse whole decoded stream directly (faster than nested BT..ET regex)
        for a in ARR.finditer(dec):
            parts = PARENS.findall(a.group(1))
            if parts:
                lines.append("".join(p.decode("latin1", "ignore") for p in parts))
        for t in SINGLE.finditer(dec):
            lines.append(t.group(1).decode("latin1", "ignore"))

    cleaned: list[str] = []
    for line in lines:
        line = line.replace("\\050", "(").replace("\\051", ")").replace("\\034", "fi")
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            cleaned.append(line)
    return "\n".join(cleaned)


def main() -> None:
    out = Path("ikariam_battle_system_extracted.txt")
    text = extract_text(Path("ikariam battle system.pdf"), max_streams=220)
    out.write_text(text, encoding="utf-8")
    print(f"Extracted {len(text)} chars to {out}")


if __name__ == "__main__":
    main()
