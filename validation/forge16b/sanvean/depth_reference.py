"""Apply dated FORGE 16B depth-reference corrections to derived inputs."""
import csv
from functools import lru_cache
from pathlib import Path

from .build_extracts import timestamp

TABLE = Path(__file__).with_name("depth-reference-corrections.csv")


@lru_cache
def corrections():
    with TABLE.open(encoding="utf-8-sig", newline="") as stream:
        return tuple(csv.DictReader(stream))


def corrected_depth(time, depth, *, clock="pason", assembly=None):
    """Subtract only corrections applicable to this source clock and trip."""
    if clock not in ("pason", "sanvean"):
        raise ValueError("unknown rig clock")
    for row in corrections():
        if assembly is not None and str(assembly) != row["assembly"]:
            continue
        start = row[f"{clock}_start"]
        reset = row[f"{clock}_reset"]
        if start and reset and timestamp(start) <= time < timestamp(reset):
            return depth-float(row["subtract_ft"])
    return depth
