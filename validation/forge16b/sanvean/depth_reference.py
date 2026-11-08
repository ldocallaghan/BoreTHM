"""Bit depths for FORGE 16B replay inputs.

entry_depth applies the linear maps from depth_entries.py, which take the
driller's tally entries as the depth reference and scale the rig
increments between them. It supersedes rebuilt_depth, which removed the
entries as resets. rebuilt_depth and corrected_depth are kept so the
earlier archives can be rebuilt.

rebuilt_depth applies the dated offsets from depth_rebuild.py, which
remove rig depth-tally resets and anchor each trip at the drilling
bottom. It supersedes corrected_depth, the constant subtractions of the
first screen, which a stand count and the block-travel rebuild did not
support. corrected_depth is kept so the earlier archive can be rebuilt.
"""
import bisect
import csv
from functools import lru_cache
from pathlib import Path

from .build_extracts import timestamp

TABLE = Path(__file__).with_name("depth-reference-corrections.csv")
OFFSETS = Path(__file__).with_name("depth-rebuild-2026-11-07") / "offsets.csv"
ENTRY_SEGMENTS = Path(__file__).with_name("depth-entries-2026-11-08") / "segments.csv"


@lru_cache
def corrections():
    with TABLE.open(encoding="utf-8-sig", newline="") as stream:
        return tuple(csv.DictReader(stream))


def corrected_depth(time, depth, *, clock="pason", assembly=None):
    """Superseded: subtract the first screen's constant offsets."""
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


@lru_cache
def _segments(clock, assembly):
    with OFFSETS.open(encoding="utf-8-sig", newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["clock"] == clock
                and (clock == "pason" or r["assembly"] == str(assembly))]
    rows.sort(key=lambda r: timestamp(r["start"]))
    return ([timestamp(r["start"]) for r in rows], [timestamp(r["end"]) for r in rows],
            [float(r["offset_ft"]) for r in rows])


def rebuilt_depth(time, depth, *, clock="pason", assembly=None):
    """Return the recorded depth plus the rebuilt offset at this time.

    Pason offsets cover the whole record. Sanvean offsets are per run,
    so the assembly must be given for the Sanvean clock.
    """
    if clock not in ("pason", "sanvean"):
        raise ValueError("unknown rig clock")
    if clock == "sanvean" and assembly is None:
        raise ValueError("the Sanvean clock needs the assembly")
    starts, ends, values = _segments(clock, None if clock == "pason" else int(assembly))
    i = bisect.bisect_right(starts, time) - 1
    if i >= 0 and time <= ends[i]:
        return round(depth + values[i], 6)
    return depth


@lru_cache
def _entry_segments(clock, assembly):
    with ENTRY_SEGMENTS.open(encoding="utf-8-sig", newline="") as stream:
        rows = [r for r in csv.DictReader(stream) if r["clock"] == clock
                and (clock == "pason" or r["assembly"] == str(assembly))]
    rows.sort(key=lambda r: timestamp(r["start"]))
    return ([timestamp(r["start"]) for r in rows],
            [(float(r["scale"]), float(r["intercept_ft"])) for r in rows])


def entry_depth(time, depth, *, clock="pason", assembly=None):
    """Return the tally-entry depth for a recorded depth at this time.

    Each segment maps the recorded depth linearly, depth = intercept +
    scale x recorded, from its start until the next segment starts.
    Pason segments cover the whole record. Sanvean segments are per run,
    so the assembly must be given for the Sanvean clock.
    """
    if clock not in ("pason", "sanvean"):
        raise ValueError("unknown rig clock")
    if clock == "sanvean" and assembly is None:
        raise ValueError("the Sanvean clock needs the assembly")
    starts, maps = _entry_segments(clock, None if clock == "pason" else int(assembly))
    i = bisect.bisect_right(starts, time) - 1
    if i < 0:
        return depth
    scale, intercept = maps[i]
    return round(intercept + scale * depth, 6)
