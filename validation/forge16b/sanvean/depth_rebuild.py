"""Rebuild FORGE 16B trip bit depths without rig depth-tally corrections.

The rig computes bit depth by integrating block travel while the string
hangs, and the driller occasionally resets that tally. A reset appears in
the record as a bit-depth step with no matching block travel. Between
resets, the recorded increments follow the string. This module keeps the
recorded increments, removes the resets and anchors each trip to the hole
depth where drilling resumes, when the bit is on bottom.

The rebuilt depth is therefore the recorded depth plus a piecewise-constant
offset. The offset changes only at a reset, and it returns to the recorded
difference between hole and bit depth at every drilling sample.

A second rebuild integrates block travel directly while the hook load is
above the rig's recorded slips threshold. It is used as an independent
check on the one-second Sanvean inputs. Block-height steps faster than
the declared limit are encoder resets, not travel.
"""
import argparse
import csv
import gzip
import io
from pathlib import Path
import zipfile

import numpy as np

from validation.forge16b.sanvean.build_extracts import HERE, iso, number, timestamp

OUT = HERE / "depth-rebuild-2026-11-07"
RESET_STEP_FT = 20.          # smallest bit-depth step treated as a tally reset
STILL_BLOCK_FT = 5.          # net block travel below this counts as no travel
BLOCK_SPEED_FT_PER_S = 20.   # one-second block speeds on runs 11-17 reach 19.4 ft/s
BLOCK_RESET_FT_PER_S = BLOCK_SPEED_FT_PER_S
FINE_SAMPLE_S = 2.           # sampling that resolves block strokes
DESCENT_FT_PER_S = 12.       # one-second records: at most 94 ft down in 10 s
ASCENT_FT_PER_S = 6.         # one-second records: at most 47 ft up in 10 s
SLIPS_KLBS = 52.             # Pason Hookload Threshold from 26 April 2023 12:46 on
MATCH_WINDOW_S = 15          # clock alignment is within 7 s (clock-alignment.csv)
HOLE_SHARE = .5              # a hole step above this share of the bit step moves both
TRIP_FT = 500.               # a gap that never lifts the bit this far is not a trip
DRILLING_GAP_FT = 5.         # bit within this distance of hole depth
HOLE_ADVANCE_FT = .1         # hole depth advance that marks drilling
PASON_FIELDS = ("Bit Depth (feet)", "Hole Depth (feet)", "Block Height (feet)",
                "Hook Load (klbs)", "Hookload Threshold (klbs)")


def tally_resets(time, bit, block, hook, threshold):
    """Boolean mask over sample steps that cannot be string motion.

    Every step above RESET_STEP_FT taken in the slips at both ends with
    net block travel below STILL_BLOCK_FT is a reset.

    One-second sampling also resolves block strokes. There, a step is a
    reset when it exceeds what block travel at BLOCK_SPEED_FT_PER_S could
    produce, allowing the block to return part of the way after the slips
    are set: (speed x interval + net block travel) / 2. It is also a reset
    when the hook load stays on one side of the slips threshold and the
    block barely moves.

    Coarser sampling, such as the 10 second Pason record, does not follow
    the block strokes. There, a step is a reset when it is faster than the
    string travels: DESCENT_FT_PER_S down or ASCENT_FT_PER_S up.
    """
    time, bit, block, hook, threshold = (np.asarray(x, dtype=float)
                                         for x in (time, bit, block, hook, threshold))
    dt, step, travel = np.diff(time), np.diff(bit), np.abs(np.diff(block))
    size = np.abs(step)
    hanging = hook > threshold
    in_slips = ~hanging[1:] & ~hanging[:-1] & np.isfinite(hook[1:]) & np.isfinite(hook[:-1])
    still = travel < STILL_BLOCK_FT
    fine = dt <= FINE_SAMPLE_S
    bound = (BLOCK_SPEED_FT_PER_S * dt + travel) / 2
    fine_reset = fine & ((size > bound) | (still & (hanging[1:] == hanging[:-1])))
    coarse_reset = ~fine & ((step > DESCENT_FT_PER_S * dt) | (step < -ASCENT_FT_PER_S * dt))
    return (np.isfinite(step) & (size > RESET_STEP_FT)
            & ((in_slips & still) | fine_reset | coarse_reset))


def tally_resets_on_trip(time, bit, hole, block, hook, threshold):
    """Tally resets of the bit depth alone.

    A step that moves the hole depth by a comparable amount re-references
    both, as in a drilling-depth correction, and the anchors absorb it.
    A bit step back to bottom as drilling resumes moves the hole by a few
    feet only, and stays a reset.
    """
    bit, hole = np.asarray(bit, dtype=float), np.asarray(hole, dtype=float)
    alone = np.abs(np.diff(hole)) < HOLE_SHARE * np.abs(np.diff(bit))
    return tally_resets(time, bit, block, hook, threshold) & alone


def reset_sizes(time, bit, block, hook, threshold):
    """Size of the reference change at each step, net of string motion.

    Where the sampling resolves strokes and the string hangs at either end
    of the step, block travel gives the motion during the step. Elsewhere
    the whole step is taken as the reset: a ten-second reset is found only
    in the slips or at an impossible speed, and the median of the
    neighbouring steps, tried as an estimate of the motion, matched the
    one-second rebuild less well.
    """
    time, bit, block, hook, threshold = (np.asarray(x, dtype=float)
                                         for x in (time, bit, block, hook, threshold))
    step = np.diff(bit)
    hanging = (hook[1:] > threshold[1:]) | (hook[:-1] > threshold[:-1])
    fine = np.diff(time) <= FINE_SAMPLE_S
    motion = np.where(fine & hanging, -np.diff(block), 0.)
    return step - np.nan_to_num(motion)


def drilling(bit, hole):
    """Boolean mask over samples: hole depth advancing with the bit on bottom."""
    advance = np.r_[False, np.diff(hole) > HOLE_ADVANCE_FT]
    return advance & (np.abs(hole - bit) <= DRILLING_GAP_FT)


def offsets(time, bit, hole, block, hook, threshold, fixed=None):
    """Return the rebuilt-minus-recorded offset at each sample and the reset mask.

    Anchors are drilling samples, where the offset is hole minus bit, and
    the samples in fixed, whose known offsets take precedence. If the bit
    stays within TRIP_FT of the hole depth between two anchors, the gap
    is a connection or stop and keeps the recorded depth. Otherwise the
    string goes out of the hole and back in between them. The trip out
    takes its offset forward from the earlier anchor and the trip in
    backward from the later one, split at the shallowest recorded depth
    between them. Each propagation follows the recorded increments with
    tally resets removed. Samples before the first anchor take the
    backward offset. After the last anchor, the trip out takes the forward
    offset up to its shallowest recorded depth, and later samples keep the
    record.
    """
    bit, hole = (np.asarray(x, dtype=float) for x in (bit, hole))
    resets = tally_resets_on_trip(time, bit, hole, block, hook, threshold)
    size = reset_sizes(time, bit, block, hook, threshold)
    fixed = fixed or {}
    anchor_value = {int(i): hole[i] - bit[i] for i in np.flatnonzero(drilling(bit, hole))}
    anchor_value.update(fixed)
    n = len(bit)
    backward, forward = np.full(n, np.nan), np.full(n, np.nan)
    current = np.nan
    for i in range(n - 1, -1, -1):
        if i in anchor_value:
            current = anchor_value[i]
        elif np.isfinite(current) and i < n - 1 and resets[i]:
            # Step i -> i+1 is a reset: before it, the record is offset by
            # minus the step relative to the record after it.
            current += size[i]
        backward[i] = current
    current = np.nan
    for i in range(n):
        if i in anchor_value:
            current = anchor_value[i]
        elif np.isfinite(current) and i > 0 and resets[i - 1]:
            current -= size[i - 1]
        forward[i] = current
    offset = np.where(np.isfinite(backward), backward, forward)
    marks = sorted(anchor_value)
    for left, right in zip(marks, marks[1:]):
        if right - left < 2:
            continue
        gap = slice(left + 1, right)
        recorded = bit[gap]
        if not np.isfinite(recorded).any():
            continue
        if np.nanmax(hole[gap] - recorded) < TRIP_FT:
            # The bit stayed near bottom: a connection or stop, not a trip.
            offset[gap] = 0.
            continue
        turn = left + 1 + int(np.nanargmin(recorded))
        offset[left + 1:turn] = forward[left + 1:turn]
    if marks and marks[-1] < n - 1 and np.isfinite(bit[marks[-1] + 1:]).any():
        # After the last anchor only the trip out has a reference. Later
        # samples, such as another string run in without drilling, keep
        # the record.
        turn = marks[-1] + 1 + int(np.nanargmin(bit[marks[-1] + 1:]))
        offset[turn:] = 0.
    return np.nan_to_num(offset), resets


def block_rebuild(time, block, hook, threshold, anchor_index, anchor_depth):
    """Integrate block travel while hanging, anchored at one sample."""
    time, block, hook, threshold = (np.asarray(x, dtype=float)
                                    for x in (time, block, hook, threshold))
    step = np.diff(block)
    reset = np.abs(step) > BLOCK_RESET_FT_PER_S * np.diff(time)
    hanging = (hook[1:] > threshold[1:]) | (hook[:-1] > threshold[:-1])
    travel = np.where(hanging & ~reset & np.isfinite(step), -step, 0.)
    total = np.r_[0., np.cumsum(travel)]
    return anchor_depth + total - total[anchor_index], reset


def segments(time, offset, label):
    """Compress a piecewise-constant offset to rows with nonzero offset."""
    rows, start = [], None
    for i in range(len(time) + 1):
        value = offset[i] if i < len(time) else 0.
        if start is not None and (i == len(time) or value != offset[start]):
            rows.append(dict(label, start=iso(time[start]),
                             end=iso(time[i] - 1 if i < len(time) else time[i - 1]),
                             offset_ft=round(float(offset[start]), 2)))
            start = None
        if start is None and i < len(time) and abs(value) > 1e-9:
            start = i
    return rows


def reset_rows(time, bit, block, hole, resets, label):
    for i in np.flatnonzero(resets):
        yield dict(label, time=iso(time[i + 1]), recorded_before_ft=bit[i],
                   recorded_after_ft=bit[i + 1], step_ft=round(bit[i + 1] - bit[i], 2),
                   block_before_ft=block[i], block_after_ft=block[i + 1],
                   hole_ft=hole[i + 1])


def sanvean_inputs(run):
    with gzip.open(HERE / f"bha-{run}-inputs.csv.gz", "rt", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    keep = [r for r in rows if r["bit_depth_ft"] and r["block_height_ft"] and r["hook_load_klbs"]]
    return (np.array([timestamp(r["time"]) for r in keep]),
            *(np.array([number(r[k]) for r in keep]) for k in
              ("bit_depth_ft", "hole_depth_ft", "block_height_ft", "hook_load_klbs")))


def pason_inputs(archive):
    with zipfile.ZipFile(archive) as source, source.open("10 Second Data.csv") as raw:
        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
        header = next(reader)
        positions = [header.index(field) for field in PASON_FIELDS]
        data = []
        for row in reader:
            values = [number(row[i]) if row[i] != "-999.25" else np.nan for i in positions]
            if all(np.isfinite(values[:3])):
                data.append((timestamp(row[0] + " " + row[1]), *values))
    return np.array(data).T


def write(path, rows):
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        if not rows:
            return
        fields = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sanvean(threshold=SLIPS_KLBS):
    seg, res, checks = [], [], []
    for run in range(11, 18):
        time, bit, hole, block, hook = sanvean_inputs(run)
        slips = np.full(len(time), threshold)
        offset, resets = offsets(time, bit, hole, block, hook, slips)
        label = dict(clock="sanvean", assembly=run)
        seg += segments(time, offset, label)
        res += list(reset_rows(time, bit, block, hole, resets, label))
        anchors = np.flatnonzero(drilling(bit, hole))
        if not len(anchors):
            checks.append(label | dict(status="no drilling anchor"))
            continue
        first = anchors[0]
        rebuilt = bit + offset
        by_block, block_resets = block_rebuild(time, block, hook, slips, first, hole[first])
        trip = slice(0, first + 1)
        diff = np.abs(by_block[trip] - rebuilt[trip])
        checks.append(label | dict(
            status="checked", first_drilling=iso(time[first]),
            recorded_start_ft=bit[0], rebuilt_start_ft=round(rebuilt[0], 2),
            block_start_ft=round(by_block[0], 2),
            max_abs_block_minus_rebuilt_ft=round(float(np.nanmax(diff)), 2),
            tally_resets=int(resets[:first].sum()),
            block_encoder_resets=int(block_resets[:first].sum()),
            max_abs_offset_ft=round(float(np.max(np.abs(offset[trip]))), 2)))
    return seg, res, checks


def sanvean_trip_offsets():
    """One-second offsets over each Sanvean trip, keyed by run."""
    trips = {}
    for run in range(11, 18):
        time, bit, hole, block, hook = sanvean_inputs(run)
        offset, _ = offsets(time, bit, hole, block, hook, np.full(len(time), SLIPS_KLBS))
        first = np.flatnonzero(drilling(bit, hole))[0]
        trips[run] = (time[:first + 1], bit[:first + 1], offset[:first + 1])
    return trips


def pason(archive):
    """Pason offsets, taking the Sanvean one-second offsets where they exist.

    Over each Sanvean trip the Pason offset is the Sanvean offset at the
    clock-aligned time. The first such sample anchors the backward
    propagation through the earlier Pason-only part of the trip.
    """
    time, bit, hole, block, hook, threshold = pason_inputs(archive)
    align = {int(r["eow_bha"]): int(r["pason_minus_sanvean_s"])
             for r in csv.DictReader((HERE / "clock-alignment.csv").open(encoding="utf-8-sig"))}
    fixed = {}
    for run, (t, recorded, off) in sanvean_trip_offsets().items():
        shifted = t + align[run]
        inside = np.flatnonzero((time >= shifted[0]) & (time <= shifted[-1]))
        for i in inside:
            # Take the offset from the nearby one-second sample whose recorded
            # depth matches, so both clocks agree on which side of a reset
            # this sample lies.
            near = np.flatnonzero(np.abs(shifted - time[i]) <= MATCH_WINDOW_S)
            if len(near):
                j = near[np.argmin(np.abs(recorded[near] - bit[i]))]
                fixed[int(i)] = float(off[j])
    offset, resets = offsets(time, bit, hole, block, hook, threshold, fixed)
    label = dict(clock="pason")
    return (segments(time, offset, label),
            list(reset_rows(time, bit, block, hole, resets, label)),
            float(np.nanmedian(threshold)),
            list(pason_checks(time, bit, hole, block, hook, threshold, align)))


def pason_checks(time, bit, hole, block, hook, threshold, align):
    """Compare a Pason-only rebuild with the one-second rebuild per trip.

    The Pason-only rebuild uses no Sanvean offsets, so it shows what the
    ten-second record alone gives where no one-second data exist.
    """
    alone, _ = offsets(time, bit, hole, block, hook, threshold)
    for run, (t, recorded, off) in sanvean_trip_offsets().items():
        shifted = t + align[run]
        inside = np.flatnonzero((time >= shifted[0]) & (time <= shifted[-1]))
        errors = []
        for i in inside:
            near = np.flatnonzero(np.abs(shifted - time[i]) <= MATCH_WINDOW_S)
            if len(near) and np.isfinite(bit[i]):
                j = near[np.argmin(np.abs(recorded[near] - bit[i]))]
                errors.append(abs(bit[i] + alone[i] - recorded[j] - off[j]))
        if errors:
            errors = np.array(errors)
            yield dict(assembly=run, samples=len(errors),
                       median_abs_ft=round(float(np.median(errors)), 2),
                       p95_abs_ft=round(float(np.percentile(errors, 95)), 2),
                       max_abs_ft=round(float(errors.max()), 2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="16B_Pason.zip from GDR 1516")
    args = parser.parse_args()
    pason_segments, pason_resets, threshold, pason_check = pason(args.archive)
    sanvean_segments, sanvean_resets, checks = sanvean(threshold)
    write(OUT / "offsets.csv", pason_segments + sanvean_segments)
    write(OUT / "tally-resets.csv", pason_resets + sanvean_resets)
    write(OUT / "sanvean-block-check.csv", (c | dict(slips_threshold_klbs=threshold) for c in checks))
    write(OUT / "pason-only-check.csv", pason_check)


if __name__ == "__main__":
    main()
