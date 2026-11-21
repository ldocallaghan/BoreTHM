"""Classify FORGE 16B bit-depth steps that string motion cannot explain.

The rig bit-depth channel integrates block travel. The driller also types
depths in from the pipe tally. Each typed value replaces the integrated
depth in a single step, with the block still, and lands on a value given
to the foot or to the tenth of a foot. Other steps are resets to zero at
surface, short glitches that the record restores, encoder resets and
steps that cross a data gap.

This module only classifies. It reads bit depth, hole depth, block
height, hook load, the slips threshold and time. It reads no temperature
channel.

The thresholds below were set from the rig channels only.

| Rule | Value |
|---|---|
| Candidate | a step depth_rebuild.tally_resets flags, or any step over 20 ft spanning more than 10 s |
| Merge | consecutive candidates of the same sign form one event |
| Gap | a constituent step spans more than 10 s |
| Encoder reset | the block moves faster than 20 ft/s |
| Zero reset | lands on 0 ft |
| Glitch and restore | an opposite event within 180 s cancels it to within 20 ft plus the string motion between them |
| Typed entry | lands on a whole foot or the hole depth, with under 5 ft of block travel |
| Typed entry, tenth | lands on a tenth of a foot, with under 5 ft of block travel, and holds flat for the next sample |
| Pick-up entry | the hook goes from the slips to hanging within the event, with under 5 ft of block travel; the value is uncertain by that travel |
| Motion | coarser than 2 s, hanging at both ends, more than 5 ft of block travel in the direction of the bit step; not a step |
| Unresolved entry | any other candidate; an entry of unknown value |
| Small entry | any other step of 1 ft or more that lands on a whole foot, moves the block under 0.5 ft and holds flat for the next three samples |
| Clock match | a Pason event inside a Sanvean trip takes the Sanvean class and value when exactly one Sanvean event lies within 15 s of the aligned time |

The classes are tested in the order of the table. Merging comes first
because the one-second Sanvean export sometimes splits a typed entry over
two samples with an interpolated midpoint. Block travel in the direction
of the bit step means the block falls as the bit deepens and rises as it
comes up. A tenth-of-a-foot landing occurs by chance about once in ten
steps, so it needs the flat sample as well. Tenth-of-a-foot landings
outside the candidates are not entries for the same reason.
"""
import argparse
import csv
from pathlib import Path

import numpy as np

from validation.forge16b.sanvean import depth_rebuild as rebuild
from validation.forge16b.sanvean.build_extracts import HERE, iso

OUT = HERE / "depth-steps-2026-11-08"
GAP_S = 10.                  # a step spanning more than this is unresolved
GLITCH_WINDOW_S = 180.       # a restore must follow within this time
RESTORE_TOLERANCE_FT = 20.   # residual allowed beyond string motion
STILL_BLOCK_FT = rebuild.STILL_BLOCK_FT
MATCH_WINDOW_S = rebuild.MATCH_WINDOW_S
SMALL_STEP_FT = 1.           # a smaller step is not tested as a small entry
SMALL_BLOCK_FT = .5          # block movement over the step below this
SMALL_FLAT = 3               # samples the landing value must hold


def grid(value):
    """Return 'foot', 'tenth' or '' for the resolution a value lands on."""
    if not np.isfinite(value):
        return ""
    if abs(value - round(value)) < .005:
        return "foot"
    if abs(10 * value - round(10 * value)) < .05:
        return "tenth"
    return ""


def candidates(time, bit, block, hook, threshold):
    """Boolean mask over sample steps: flagged resets and steps across gaps."""
    time, bit = np.asarray(time, dtype=float), np.asarray(bit, dtype=float)
    gap = (np.diff(time) > GAP_S) & (np.abs(np.diff(bit)) > rebuild.RESET_STEP_FT)
    return rebuild.tally_resets(time, bit, block, hook, threshold) | gap


def describe(first, last, time, bit, hole, block, hook, threshold):
    """One event row for the step from sample first to sample last."""
    dblock = np.diff(block[first:last + 1])
    return dict(
        first=first, last=last,
        start=time[first], end=time[last], span_s=time[last] - time[first],
        samples=last - first, longest_step_s=float(np.max(np.diff(time[first:last + 1]))),
        before_ft=bit[first], after_ft=bit[last], step_ft=bit[last] - bit[first],
        block_travel_ft=float(np.abs(dblock).sum()),
        block_change_ft=float(block[last] - block[first]),
        holds_flat=bool(last + 1 < len(bit) and bit[last + 1] == bit[last]),
        block_speed_ft_per_s=float(np.max(np.abs(dblock) / np.diff(time[first:last + 1]))),
        hook_before=hook[first], hook_after=hook[last],
        hanging_before=bool(hook[first] > threshold[first]),
        hanging_after=bool(hook[last] > threshold[last]),
        hole_step_ft=hole[last] - hole[first], hole_ft=hole[last],
        landing=grid(bit[last]), small=False)


def small_entries(time, bit, block, mask):
    """Sample steps outside the candidates that are typed entries of any size.

    The step is at least SMALL_STEP_FT, lands on a whole foot, moves the
    block less than SMALL_BLOCK_FT and holds flat for SMALL_FLAT samples.
    """
    step = np.diff(bit)
    n = len(step)
    whole = np.abs(bit[1:] - np.round(bit[1:])) < .005
    still = np.abs(np.diff(block)) < SMALL_BLOCK_FT
    flat = np.ones(n, dtype=bool)
    for k in range(1, SMALL_FLAT + 1):
        later = np.full(n, np.nan)
        later[:n - k] = bit[1 + k:]
        flat &= later == bit[1:]
    return (~mask & np.isfinite(step) & (np.abs(step) >= SMALL_STEP_FT) & whole & still & flat)


def events(time, bit, hole, block, hook, threshold):
    """Merge consecutive candidate steps and describe each event.

    An event runs from sample `first` to sample `last`, so its step is
    bit[last] - bit[first]. Small typed entries outside the candidates are
    single-step events marked small.
    """
    time, bit, hole, block, hook = (np.asarray(x, dtype=float)
                                    for x in (time, bit, hole, block, hook))
    threshold = np.asarray(threshold, dtype=float)
    mask = candidates(time, bit, block, hook, threshold)
    rows, i = [], 0
    while i < len(mask):
        if not mask[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(mask) and mask[j + 1] and np.sign(bit[j + 2] - bit[j + 1]) == np.sign(bit[i + 1] - bit[i]):
            j += 1
        rows.append(describe(i, j + 1, time, bit, hole, block, hook, threshold))
        i = j + 1
    for k in np.flatnonzero(small_entries(time, bit, block, mask)):
        rows.append(describe(k, k + 1, time, bit, hole, block, hook, threshold) | dict(small=True))
    return sorted(rows, key=lambda row: row["first"])


def classify(rows, time, bit, block):
    """Add a class to each event row, in place, and return the rows."""
    time, bit, block = (np.asarray(x, dtype=float) for x in (time, bit, block))
    for row in rows:
        row["merged"] = row["samples"] > 1
        row["hole_moved"] = abs(row["hole_step_ft"]) >= rebuild.HOLE_SHARE * abs(row["step_ft"])
        row["pair"] = ""
        if row["small"]:
            row["class"] = "zero_reset" if row["after_ft"] == 0 else "typed_entry_small"
        elif row["longest_step_s"] > GAP_S:
            row["class"] = "gap"
        elif row["block_speed_ft_per_s"] > rebuild.BLOCK_RESET_FT_PER_S:
            row["class"] = "encoder_reset"
        elif row["after_ft"] == 0:
            row["class"] = "zero_reset"
        else:
            row["class"] = ""
    for k, row in enumerate(rows):
        if row["class"]:
            continue
        for later in rows[k + 1:]:
            if later["start"] - row["end"] > GLITCH_WINDOW_S:
                break
            if later["class"] or np.sign(later["step_ft"]) == np.sign(row["step_ft"]):
                continue
            between = slice(row["last"], later["first"] + 1)
            motion = abs(bit[between][-1] - bit[between][0])
            if abs(row["step_ft"] + later["step_ft"]) <= RESTORE_TOLERANCE_FT + motion:
                row["class"], later["class"] = "glitch", "restore"
                row["pair"], later["pair"] = iso(later["end"]), iso(row["end"])
            break
    for row in rows:
        if row["class"]:
            continue
        if abs(row["after_ft"] - row["hole_ft"]) < .005:
            row["landing"] = "hole"
        still = row["block_travel_ft"] < STILL_BLOCK_FT
        with_block = np.sign(row["block_change_ft"]) == -np.sign(row["step_ft"])
        if still and row["landing"] in ("foot", "hole"):
            row["class"] = "typed_entry"
        elif still and row["landing"] == "tenth" and row["holds_flat"]:
            row["class"] = "typed_entry_tenth"
        elif still and not row["hanging_before"] and row["hanging_after"]:
            row["class"] = "pickup_entry"
        elif (row["longest_step_s"] > rebuild.FINE_SAMPLE_S and row["hanging_before"]
              and row["hanging_after"] and not still and with_block):
            row["class"] = "motion"
        else:
            row["class"] = "unresolved_entry"
    return rows


def classified(time, bit, hole, block, hook, threshold):
    return classify(events(time, bit, hole, block, hook, threshold), time, bit, block)


def match_sanvean(pason_rows, sanvean_rows, align):
    """Give each Pason event inside a Sanvean trip the matching Sanvean class.

    sanvean_rows maps run to (trip start, trip end, rows) on the Sanvean
    clock. align maps run to Pason minus Sanvean seconds.
    """
    for row in pason_rows:
        row["sanvean_class"] = row["sanvean_after_ft"] = row["sanvean_end"] = ""
        row["final_class"] = row["class"]
        for run, (start, end, rows) in sanvean_rows.items():
            shift = align[run]
            if not start + shift <= row["end"] <= end + shift + MATCH_WINDOW_S:
                continue
            near = [s for s in rows if abs(s["end"] + shift - row["end"]) <= MATCH_WINDOW_S]
            if len(near) == 1:
                s = near[0]
                row["sanvean_class"], row["sanvean_after_ft"] = s["class"], s["after_ft"]
                row["sanvean_end"] = iso(s["end"])
                row["final_class"] = s["class"]
            elif not near:
                row["final_class"] = "unmatched_in_sanvean"
    return pason_rows


FIELDS = ("clock", "assembly", "start", "end", "span_s", "longest_step_s", "samples", "merged", "small",
          "before_ft", "after_ft", "step_ft", "landing", "holds_flat", "block_travel_ft",
          "block_change_ft",
          "block_speed_ft_per_s", "hook_before", "hook_after", "hanging_before",
          "hanging_after", "hole_step_ft", "hole_ft", "hole_moved", "class", "pair",
          "sanvean_class", "sanvean_after_ft", "sanvean_end", "final_class")


def output_row(row, **label):
    out = dict(label) | {k: row.get(k, "") for k in FIELDS if k not in label}
    out["start"], out["end"] = iso(row["start"]), iso(row["end"])
    for key in ("span_s", "before_ft", "after_ft", "step_ft", "block_travel_ft", "block_change_ft",
                "block_speed_ft_per_s", "hook_before", "hook_after", "hole_step_ft", "hole_ft"):
        out[key] = round(float(row[key]), 2)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="16B_Pason.zip from GDR 1516")
    args = parser.parse_args()
    align = {int(r["eow_bha"]): int(r["pason_minus_sanvean_s"])
             for r in csv.DictReader((HERE / "clock-alignment.csv").open(encoding="utf-8-sig"))}
    sanvean, out = {}, []
    for run in range(11, 18):
        time, bit, hole, block, hook = rebuild.sanvean_inputs(run)
        rows = classified(time, bit, hole, block, hook, np.full(len(time), rebuild.SLIPS_KLBS))
        sanvean[run] = (time[0], time[-1], rows)
        out += [output_row(r, clock="sanvean", assembly=run) | dict(final_class=r["class"])
                for r in rows]
    time, bit, hole, block, hook, threshold = rebuild.pason_inputs(args.archive)
    pason = match_sanvean(classified(time, bit, hole, block, hook, threshold), sanvean, align)
    out = [output_row(r, clock="pason", assembly="") for r in pason] + out
    rebuild.write(OUT / "steps.csv", out)


if __name__ == "__main__":
    main()
