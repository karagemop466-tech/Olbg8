#!/usr/bin/env python3
"""Read captured raw payloads, plain or gzip-compressed."""
from __future__ import annotations

import gzip
from pathlib import Path

RAW = Path(__file__).resolve().parent / "raw"


def read_text(path: Path) -> str:
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    return path.read_text(encoding="utf-8", errors="replace")


def find(name: str) -> Path | None:
    """Locate a capture by stem, tolerating .txt, .txt.gz and hyphen/underscore variants."""
    stem = name.replace("-", "_")
    for cand in (RAW / f"{name}.txt", RAW / f"{name}.txt.gz", RAW / f"{stem}.txt", RAW / f"{stem}.txt.gz"):
        if cand.exists():
            return cand
    return None


def read(name: str) -> str:
    p = find(name)
    return read_text(p) if p else ""


def glob(prefix: str) -> list[Path]:
    out = []
    for p in sorted(RAW.glob("*.txt*")):
        stem = p.name.split(".txt")[0]
        if stem.startswith(prefix):
            out.append(p)
    return out
