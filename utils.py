from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from typing import Iterable, Sequence, TypeVar


def utc_now_iso() -> str:
    """UTC timestamp for DB storage (ISO-8601, seconds precision)."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


_slug_re = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = _slug_re.sub("-", text).strip("-")
    return text or "item"


def normalize_platform(p: str) -> str:
    return slugify(p).replace("-", "")


T = TypeVar("T")


def choose_distinct(seq: Sequence[T], k: int, rng: random.Random) -> list[T]:
    if k <= 0:
        return []
    if k >= len(seq):
        return list(seq)
    return rng.sample(list(seq), k)


def one_of(options: Sequence[str], rng: random.Random) -> str:
    return options[rng.randrange(0, len(options))]


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def compact_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def ensure_sentence_end(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    if s[-1] in ".!?":
        return s
    return s + "."


def chunks(it: Iterable[T], size: int) -> list[list[T]]:
    size = max(1, size)
    out: list[list[T]] = []
    buf: list[T] = []
    for x in it:
        buf.append(x)
        if len(buf) >= size:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out

