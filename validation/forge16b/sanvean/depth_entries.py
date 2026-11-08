"""Bit depth from the driller's tally entries and a scale on the rig increments.

The rig integrates block travel into bit depth, and the block encoder
drifts by several feet per stand. The driller corrects the drift by typing
depths from the pipe tally. depth_steps.py classifies those entries. This
module takes them as the depth reference off bottom, and the recorded hole
depth on bottom.

Drilling. A drilling sample has the hole advancing by more than 0.1 ft
over the preceding DRILL_WINDOW_S with the bit within 5 ft of it. Its depth
is the recorded hole depth, with no scale on drilled footage. The first
and last samples of each drilling spell are anchors at the hole depth, so
each trip in closes on the bottom and each trip out starts from it. An
entry or unknown jump that lands on a drilling sample gives way to the
hole depth.

Anchors. A typed entry, of any size, fixes the depth at its sample to its
entered value. A Pason entry inside a one-second Sanvean trip is
classified by its Sanvean match. A Sanvean entry with no Pason step,
taken as motion at ten seconds, enters the Pason record on the Pason step
that contains it. Each Sanvean record starts inside a trip, so its first
sample takes the Pason rebuilt depth, matched on recorded depth within
MATCH_WINDOW_S, as an anchor. A pick-up entry is an anchor whose value is
uncertain by the block travel in its sample. A zero reset fixes the depth
at 0 ft. A glitch and its restore are removed and the interval between
them is continuous.

Runs. The record is cut at each turnaround, the shallowest recorded
sample of a trip. A run is the span between two turnarounds: the trip in
of one assembly, its drilling and its trip out. A trip runs from the last
drilling sample before the recorded bit rises TRIP_FT above the hole to
the first drilling sample after it returns. Depth propagates from an
anchor only within its run.

Between two anchors in the same run the depth is the earlier anchor plus
the rig's own increments since it, times the scale

    s = (later value - earlier value) / (rig increments between them)

so it is continuous into the later anchor. The increments exclude the
classified steps. The run median scale is used instead, and the
misclosure at the later anchor reported, when the net increments are under
SHORT_FT, when the rig travels more than ROUND_TRIP times the net
increments (an out-and-back between the anchors), or when s falls outside
SCALE_RANGE. Before the first anchor and after the last in a run, the run
median scale applies. Intervals between two drilling anchors do not set
the run median. Before the closing anchor sets it, the last entry of each
trip in is carried to the hole depth on the median of the run's other
fitted intervals; that closing misclosure is the check on the scale.

A run with no fitted scale borrows the median of the nearest run in time
with the same pipe and at least MIN_DONOR_FITS fitted intervals. Without
one it uses, on the one-second record, the sourced stand length over the
rig's mean complete loaded stroke in the run; at ten seconds the slips
transitions fall between samples and the stroke is undercounted, so the
ten-second record does not. Failing both, the scale is 1.

Gaps and unresolved entries are unknown jumps. The spans on each side are
taken from their own anchors, and the implied jump is reported.

Uncertainty at a sample is the largest of: the anchor value uncertainty;
the misclosure of its interval scaled by the share of rig travel from the
earlier anchor; a rate times the rig travel to the nearest anchor; for
insulated pipe, 1 ft per 119 ft stand over the same travel; and a fixed
term where declared. The rate is half the run's spread of fitted scales
with two or more fits, the largest such spread with one fit, and half the
spread between run medians otherwise. A span with no anchor keeps the
recorded depth; its uncertainty is the rate times the rig travel to the
nearest anchor plus the offset across a bounding unknown jump.

The rebuilt bit is checked against the recorded hole depth plus 5 ft at
every sample, and breaches are reported, not clipped.

It reads time, bit depth, hole depth, block height, hook load and the
slips threshold only.
"""
import argparse
import csv
from pathlib import Path

import numpy as np

from validation.forge16b.sanvean import depth_rebuild as rebuild
from validation.forge16b.sanvean import depth_steps as steps
from validation.forge16b.sanvean.build_extracts import HERE, iso, timestamp

OUT = HERE / "depth-entries-closed-2026-11-08"
SHORT_FT = 190.              # two stands: a shorter interval does not fit a scale
ROUND_TRIP = 2.              # travel over net increments that marks an out-and-back
SCALE_RANGE = (.85, 1.15)    # a fitted scale outside this flags the interval
TRIP_FT = rebuild.TRIP_FT
STAND_FT = 95.12             # 5.5 in S-135, 25 stands as 2,378 ft (GDR 1516 daily report 39)
INSULATED_STAND_FT = 119.    # 10 stands from 9,255 ft to 8,065 ft (daily report 40)
INSULATED_STAND_ERROR_FT = 1.
STROKE_RANGE_FT = (50., 130.)  # a complete loaded stroke of one stand
MIN_STROKES = 10             # fewer strokes do not give a mean
MIN_DONOR_FITS = 2           # a run lends its scale only with this many fitted intervals
DRILL_WINDOW_S = 10.         # the hole advance that marks drilling is taken over this time
# Insulated drill pipe was in the string on assemblies 18 and 19, from the
# trip in on 22 May to the lay-down on 25 May 2023 (daily reports 37 to 40).
INSULATED = (timestamp("2023-05-22 15:00:00"), timestamp("2023-05-25 21:30:00"))
# The run 17 entries sit 35 ft off BHA #17 plus whole stands, unexplained
# by the reported string. Depths before the first run 17 entry carry it.
# BHA #17 was made up from 03:30 on 21 May (daily report 35).
FIXED = ((timestamp("2023-05-21 03:30:00"), timestamp("2023-05-21 06:19:20"), 35.),)
# Runs are checked through the drilling assemblies, to 17 June 2023. Later
# casing, completion and 3.5 in pipe runs neither lend a scale nor set the
# record's spread.
SCOPE_END = timestamp("2023-06-18 00:00:00")
ANCHORS = ("typed_entry", "typed_entry_tenth", "typed_entry_small", "pickup_entry", "zero_reset")
UNKNOWN = ("gap", "unresolved_entry", "encoder_reset", "unmatched_in_sanvean")


def increments(bit, events):
    """Rig increments per sample step, with the classified steps removed."""
    inc = np.nan_to_num(np.diff(np.asarray(bit, dtype=float)))
    for event in events:
        if event["final_class"] == "motion":
            continue
        inc[event["first"]:event["last"]] = 0.
    glitches = {iso(e["end"]): e for e in events if e["final_class"] == "glitch"}
    for event in events:
        if event["final_class"] == "restore":
            pair = glitches.get(event["pair"])
            if pair is not None:
                inc[event["last"] - 1] = pair["step_ft"] + event["step_ft"]
    return inc


def breakpoints(events):
    """Anchors and unknown jumps, in sample order."""
    marks = []
    for event in events:
        kind = event["final_class"]
        if kind in ANCHORS:
            value = 0. if kind == "zero_reset" else float(event["after_ft"])
            error = event["block_travel_ft"] if kind == "pickup_entry" else 0.
            marks.append(dict(first=event["first"], last=event["last"], kind="anchor",
                              cls=kind, value=value, error=error, event=event))
        elif kind in UNKNOWN:
            marks.append(dict(first=event["first"], last=event["last"], kind="unknown",
                              cls=kind, value=np.nan, error=0., event=event))
    return sorted(marks, key=lambda m: m["last"])


def drilling(time, bit, hole):
    """Boolean mask over samples: the hole advancing with the bit on bottom.

    The hole must advance more than depth_rebuild.HOLE_ADVANCE_FT over the
    preceding DRILL_WINDOW_S, so the test does not depend on the sampling
    interval, and the bit must be within DRILLING_GAP_FT of the hole.
    """
    time, bit, hole = (np.asarray(x, dtype=float) for x in (time, bit, hole))
    back = np.searchsorted(time, time - DRILL_WINDOW_S)
    back = np.minimum(back, np.arange(len(time)) - 1).clip(0)
    advance = hole - hole[back]
    advance[0] = 0.
    return (advance > rebuild.HOLE_ADVANCE_FT) & (np.abs(hole - bit) <= rebuild.DRILLING_GAP_FT)


def trip_windows(time, bit, hole):
    """(start, end) sample pairs bracketing each excursion off bottom."""
    bit, hole = np.asarray(bit, dtype=float), np.asarray(hole, dtype=float)
    off = np.nan_to_num(hole - bit) > TRIP_FT
    drill = np.flatnonzero(drilling(time, bit, hole))
    windows, i = [], 0
    while i < len(off):
        if not off[i]:
            i += 1
            continue
        before, after = drill[drill < i], drill[drill > i]
        start = before[-1] if len(before) else 0
        end = after[0] if len(after) else len(bit) - 1
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(end, windows[-1][1]))
        else:
            windows.append((start, end))
        i = max(end, i) + 1
    return windows


def runs(time, bit, hole):
    """Run number per sample: the record cut at each trip's shallowest sample."""
    bit = np.asarray(bit, dtype=float)
    on = drilling(time, bit, hole)
    cuts = []
    for start, end in trip_windows(time, bit, hole):
        # A record that starts or ends inside a trip has no drilling on
        # that side, and its shallowest sample is no turnaround.
        if on[start] and on[end]:
            cuts.append(start + int(np.nanargmin(bit[start:end + 1])))
    run = np.zeros(len(bit), dtype=int)
    for k, cut in enumerate(cuts, 1):
        run[cut:] = k
    return run


def stroke_scale(time, block, hook, threshold, span):
    """Sourced stand length over the mean complete loaded stroke in a span."""
    time = np.asarray(time, dtype=float)[span]
    block, hook, threshold = (np.asarray(x, dtype=float)[span] for x in (block, hook, threshold))
    hanging = hook > threshold
    strokes, start = [], None
    for k in range(len(hanging)):
        if hanging[k] and start is None:
            start = k
        if not hanging[k] and start is not None:
            travel = abs(block[k] - block[start])
            if STROKE_RANGE_FT[0] <= travel <= STROKE_RANGE_FT[1]:
                strokes.append(travel)
            start = None
    if len(strokes) < MIN_STROKES:
        return np.nan, len(strokes)
    middle = time[len(time) // 2]
    stand = INSULATED_STAND_FT if INSULATED[0] <= middle <= INSULATED[1] else STAND_FT
    return stand / float(np.mean(strokes)), len(strokes)


def fine(time):
    return float(np.median(np.diff(time))) <= rebuild.FINE_SAMPLE_S


def drilling_spells(drilling):
    """(first, last) sample pairs of each contiguous run of drilling samples."""
    idx = np.flatnonzero(drilling)
    if not len(idx):
        return []
    return [(int(g[0]), int(g[-1])) for g in np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1)]


def pipe(moment):
    return "insulated" if INSULATED[0] <= moment <= INSULATED[1] else "S-135"


def entry_depth(time, bit, hole, block, hook, threshold, events, start=None, rates=None):
    """Depth per sample, its uncertainty, the intervals and the run scales.

    start, if given, is (value, error): an anchor at the first sample, for
    a record that begins inside a trip after an entry it does not contain.
    rates, if given, is (within, between): the largest in-scope spread of
    fitted scales within a run and half the spread between run medians,
    from a record with more runs, used where this record has none.
    """
    time, bit, hole = (np.asarray(x, dtype=float) for x in (time, bit, hole))
    n = len(bit)
    inc = increments(bit, events)
    cum = np.r_[0., np.cumsum(inc)]
    travel = np.r_[0., np.cumsum(np.abs(inc))]
    run = runs(time, bit, hole)
    on_bottom = drilling(time, bit, hole)

    # While drilling the bit is the recorded hole depth. Entries and
    # unknown jumps that land on a drilling sample give way to it, and
    # each drilling spell's first and last samples are anchors.
    marks = breakpoints(events)
    yielded = [m for m in marks if on_bottom[m["last"]]]
    marks = [m for m in marks if not on_bottom[m["last"]]]
    for first, last in drilling_spells(on_bottom):
        for k in sorted({first, last}):
            marks.append(dict(first=k, last=k, kind="anchor", cls="drilling",
                              value=float(hole[k]), error=0., event=None))
    if start is not None and not on_bottom[0] and not any(m["last"] == 0 for m in marks):
        marks.append(dict(first=0, last=0, kind="anchor", cls="pason_start",
                          value=float(start[0]), error=float(start[1]), event=None))

    # Spans between consecutive breakpoints, also cut at run boundaries.
    # A span runs from its left breakpoint's anchor sample to the sample
    # before its right breakpoint's step; a drilling anchor has no step, so
    # neighbouring spans share its sample.
    cuts = [dict(first=k, last=k, kind="run start") for k in np.flatnonzero(np.diff(run)) + 1]
    edges = [None] + sorted(marks + cuts, key=lambda m: (m["last"], m["kind"] != "run start")) + [None]
    intervals = []
    for left, right in zip(edges, edges[1:]):
        a = left["last"] if left else 0
        b = right["first"] if right else n - 1
        if right is not None and right["kind"] == "run start":
            b = right["first"] - 1
        if b < a:
            continue
        intervals.append(dict(a=a, b=b, left=left, right=right, run=int(run[a]),
                              rig_ft=cum[b] - cum[a], travel_ft=travel[b] - travel[a],
                              span_ft=np.nan, scale=np.nan, basis="", misclosure_ft=np.nan, flag=""))

    def anchored(mark):
        return mark is not None and mark["kind"] == "anchor"

    def drilled(mark):
        return anchored(mark) and mark["cls"] == "drilling"

    for iv in intervals:
        left, right = iv["left"], iv["right"]
        iv["between_drilling"] = drilled(left) and drilled(right)
        if anchored(left) and anchored(right):
            iv["span_ft"] = right["value"] - left["value"]
            if abs(iv["rig_ft"]) < SHORT_FT:
                iv["flag"] = "short"
            elif iv["travel_ft"] > ROUND_TRIP * abs(iv["rig_ft"]):
                iv["flag"] = "out and back"
            else:
                s = iv["span_ft"] / iv["rig_ft"]
                if SCALE_RANGE[0] <= s <= SCALE_RANGE[1]:
                    iv["scale"], iv["basis"] = s, "fitted"
                else:
                    iv["flag"] = f"implausible scale {s:.3f}"

    # Run scales. Intervals between two drilling anchors do not set them.
    def fits(k, skip=None):
        return [iv["scale"] for iv in intervals if iv["run"] == k and iv["basis"] == "fitted"
                and not iv["between_drilling"] and iv is not skip]

    numbers = np.unique(run)
    centre = {k: float(np.median(time[run == k])) for k in numbers}
    ends = {k: float(time[run == k][-1]) for k in numbers}
    scales = {}
    for k in numbers:
        fitted = fits(k)
        if fitted:
            spread = (max(fitted) - min(fitted)) / 2 if len(fitted) > 1 else np.nan
            scales[k] = dict(scale=float(np.median(fitted)), basis="run median", fitted=len(fitted),
                             half_spread=spread)
    donors = [k for k in scales if scales[k]["fitted"] >= MIN_DONOR_FITS and ends[k] < SCOPE_END]
    for k in numbers:
        if k in scales:
            continue
        same = [d for d in donors if pipe(centre[d]) == pipe(centre[k])]
        if same:
            near = min(same, key=lambda d: abs(centre[d] - centre[k]))
            scales[k] = dict(scales[near], basis=f"borrowed from run {near}", fitted=0)
            continue
        if fine(time):
            s, count = stroke_scale(time, block, hook, threshold, run == k)
            if np.isfinite(s):
                scales[k] = dict(scale=s, basis=f"stand length over mean stroke ({count} strokes)",
                                 fitted=0, half_spread=np.nan)
                continue
        scales[k] = dict(scale=1., basis="scale 1", fitted=0, half_spread=np.nan)
    scoped = [k for k in numbers if ends[k] < SCOPE_END and scales[k]["fitted"]] or \
        [k for k in numbers if scales[k]["fitted"]]
    spreads = [scales[k]["half_spread"] for k in scoped if np.isfinite(scales[k]["half_spread"])]
    default_spread = float(np.max(spreads)) if spreads else 0.
    medians = [scales[k]["scale"] for k in scoped]
    between = (max(medians) - min(medians)) / 2 if len(medians) > 1 else default_spread
    if rates is not None:
        default_spread = default_spread if spreads else rates[0]
        between = between if len(medians) > 1 else rates[1]
    for k, v in scales.items():
        v["pipe"] = pipe(centre[k])
        v["error_rate"] = (v["half_spread"] if v["fitted"] >= 2 and np.isfinite(v["half_spread"])
                           else default_spread if v["fitted"] else max(between, default_spread))
        v["start"], v["end"] = float(time[run == k][0]), float(time[run == k][-1])
        v["anchors"] = sum(1 for m in marks if m["kind"] == "anchor" and m["cls"] != "drilling"
                           and run[m["last"]] == k)

    depth, error = np.full(n, np.nan), np.zeros(n)
    distance = np.full(n, np.inf)
    for iv in intervals:
        a, b, left, right = iv["a"], iv["b"], iv["left"], iv["right"]
        idx = np.arange(a, b + 1)
        k = iv["run"]
        if not iv["basis"]:
            iv["scale"], iv["basis"] = scales[k]["scale"], scales[k]["basis"]
        s = iv["scale"]
        if anchored(left):
            depth[idx] = left["value"] + s * (cum[idx] - cum[a])
            error[idx] = np.maximum(error[idx], left["error"])
            distance[idx] = np.minimum(distance[idx], travel[idx] - travel[a])
            if anchored(right):
                iv["misclosure_ft"] = left["value"] + s * iv["rig_ft"] - right["value"]
                if iv["basis"] != "fitted" and iv["travel_ft"] > 0:
                    share = (travel[idx] - travel[a]) / iv["travel_ft"]
                    error[idx] = np.maximum(error[idx], abs(iv["misclosure_ft"]) * share)
        elif anchored(right):
            # The right event's own steps carry no increment, so cum[b] is
            # also the rig position at the anchor sample.
            depth[idx] = right["value"] - s * (cum[b] - cum[idx])
            error[idx] = np.maximum(error[idx], right["error"])
        if anchored(right):
            distance[idx] = np.minimum(distance[idx], travel[b] - travel[idx])
        if not (anchored(left) or anchored(right)):
            iv["basis"] += "; no anchor in span"
            depth[idx] = bit[idx]
            iv["flag"] = (iv["flag"] + "; " if iv["flag"] else "") + "recorded, no reference"
            iv["unreferenced"] = True
        rate = scales[k]["error_rate"]
        insulated = (time[idx] >= INSULATED[0]) & (time[idx] <= INSULATED[1])
        rate = np.where(insulated, max(rate, INSULATED_STAND_ERROR_FT / INSULATED_STAND_FT), rate)
        iv["rate"] = rate
        finite = np.isfinite(distance[idx])
        error[idx] = np.maximum(error[idx], np.where(finite, rate * np.where(finite, distance[idx], 0.), 0.))
        # Closing misclosure: the last entry of a trip carried to the hole
        # depth at the first drilling sample on the scale of the run's other
        # fitted intervals, before the closing anchor sets it.
        if drilled(right) and anchored(left) and not drilled(left):
            others = fits(k, skip=iv)
            check = float(np.median(others)) if others else scales[k]["scale"]
            iv["closing"] = dict(entry=left["cls"], entry_value=left["value"], rig_ft=iv["rig_ft"],
                                 check_scale=check,
                                 check_basis="other fits" if others else scales[k]["basis"],
                                 predicted_ft=left["value"] + check * iv["rig_ft"],
                                 hole_ft=right["value"])
    depth[on_bottom] = hole[on_bottom]
    error[on_bottom] = 0.
    for start_t, end_t, value in FIXED:
        inside = (time >= start_t) & (time < end_t)
        error[inside] = np.maximum(error[inside], value)

    # A span with no reference keeps the recorded depth. Its uncertainty is
    # the run rate times the rig travel to the nearest anchor, plus the
    # offset of the referenced depth across a bounding unknown jump.
    anchors = np.array(sorted({m["last"] for m in marks if m["kind"] == "anchor"}), dtype=int)
    for i, iv in enumerate(intervals):
        if not iv.get("unreferenced"):
            continue
        idx = np.arange(iv["a"], iv["b"] + 1)
        near = np.full(len(idx), np.inf)
        if len(anchors):
            j = np.searchsorted(anchors, idx)
            before = anchors[np.clip(j - 1, 0, len(anchors) - 1)]
            after = anchors[np.clip(j, 0, len(anchors) - 1)]
            near = np.minimum(np.abs(travel[idx] - travel[before]), np.abs(travel[after] - travel[idx]))
        offsets = []
        if i > 0 and iv["left"] is not None and iv["left"]["kind"] == "unknown":
            p = intervals[i - 1]["b"]
            offsets.append(abs(depth[p] - bit[p]))
        if i + 1 < len(intervals) and iv["right"] is not None and iv["right"]["kind"] == "unknown":
            q = intervals[i + 1]["a"]
            offsets.append(abs(depth[q] - bit[q]))
        jump = max([o for o in offsets if np.isfinite(o)], default=0.)
        error[idx] = np.where(np.isfinite(near), iv["rate"] * near + jump, np.nan)

    # Implied jump at each unknown breakpoint, where both sides have depth.
    for iv, nxt in zip(intervals, intervals[1:]):
        right = iv["right"]
        if right is not None and right["kind"] == "unknown":
            before, after = iv["b"], nxt["a"]
            right["implied_jump_ft"] = float(depth[after] - depth[before])
            right["recorded_step_ft"] = float(bit[after] - bit[before])
    if intervals:
        intervals[0]["yielded"] = yielded
        intervals[0]["rates"] = (default_spread, between)
    return depth, error, intervals, scales


def closing_rows(time, intervals):
    """Closing misclosure per trip in, from the intervals that close on the hole."""
    for iv in intervals:
        c = iv.get("closing")
        if c is None:
            continue
        yield dict(run=iv["run"], last_entry=iso(time[iv["a"]]), bottom=iso(time[iv["b"]]),
                   entry=c["entry"], entry_ft=round(c["entry_value"], 2),
                   rig_ft=round(float(c["rig_ft"]), 2), check_scale=round(c["check_scale"], 4),
                   check_basis=c["check_basis"], predicted_ft=round(float(c["predicted_ft"]), 2),
                   hole_ft=round(c["hole_ft"], 2),
                   misclosure_ft=round(float(c["predicted_ft"] - c["hole_ft"]), 2),
                   closing_scale=round(float(iv["scale"]), 4), closing_basis=iv["basis"], flag=iv["flag"])


def yielded_rows(time, intervals):
    """Entries and unknown jumps that landed on a drilling sample."""
    for m in (intervals[0].get("yielded", []) if intervals else []):
        ev = m["event"]
        yield dict(time=iso(time[m["last"]]), cls=m["cls"],
                   before_ft=round(float(ev["before_ft"]), 2), after_ft=round(float(ev["after_ft"]), 2))


def bound_breaches(time, bit, hole, depth, tolerance=5.):
    """Spans where the rebuilt bit is more than `tolerance` below the hole."""
    excess = depth - hole - tolerance
    idx = np.flatnonzero(np.isfinite(excess) & (excess > 0))
    if not len(idx):
        return
    for group in np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1):
        yield dict(start=iso(time[group[0]]), end=iso(time[group[-1]]), samples=len(group),
                   max_below_hole_ft=round(float(np.max(depth[group] - hole[group])), 2),
                   hole_ft=round(float(hole[group[0]]), 2))


def stand_counts(time, bit, block, hook, threshold, events, depth):
    """Stands run between consecutive slips entries against the entered change.

    One-second records only. A stand is a hanging spell with a complete
    loaded stroke in STROKE_RANGE_FT. The sourced stand length times the
    count is compared with the change in entered depth.
    """
    hook, threshold, block = (np.asarray(x, dtype=float) for x in (hook, threshold, block))
    slips = hook <= threshold
    entries = [ev for ev in events if ev["final_class"] in ("typed_entry", "typed_entry_tenth")
               and slips[ev["last"]]]
    for left, right in zip(entries, entries[1:]):
        a, b = left["last"], right["first"]
        count, start = 0, None
        for k in range(a, b + 1):
            if not slips[k] and start is None:
                start = k
            if slips[k] and start is not None:
                if STROKE_RANGE_FT[0] <= abs(block[k] - block[start]) <= STROKE_RANGE_FT[1]:
                    count += 1
                start = None
        stand = INSULATED_STAND_FT if INSULATED[0] <= time[a] <= INSULATED[1] else STAND_FT
        entered = right["after_ft"] - left["after_ft"]
        yield dict(start=iso(time[a]), end=iso(time[right["last"]]), stands=count,
                   entered_ft=round(float(entered), 2), stand_length_ft=stand,
                   count_times_stand_ft=round(count * stand, 2),
                   difference_ft=round(float(entered - count * stand), 2),
                   entered_per_stand_ft=round(float(entered / count), 2) if count else "")


def matched(p_time, p_bit, s_time, s_bit, shift):
    """For each Pason sample in the Sanvean span, the Sanvean sample within
    MATCH_WINDOW_S of the aligned time whose recorded depth is nearest.

    Matching on recorded depth keeps both clocks on the same side of an
    entry and removes the string motion inside the clock alignment error.
    """
    shifted = s_time + shift
    inside = np.flatnonzero((p_time >= shifted[0]) & (p_time <= shifted[-1]))
    pairs = []
    for i in inside:
        lo = np.searchsorted(shifted, p_time[i] - steps.MATCH_WINDOW_S)
        hi = np.searchsorted(shifted, p_time[i] + steps.MATCH_WINDOW_S, side="right")
        if hi > lo:
            pairs.append((i, lo + int(np.argmin(np.abs(s_bit[lo:hi] - p_bit[i])))))
    return pairs


def start_anchor(p_time, p_bit, p_depth, p_error, s_time, s_bit, shift):
    """Pason rebuilt depth at the first Sanvean sample, matched on recorded depth."""
    lo = np.searchsorted(p_time, s_time[0] + shift - steps.MATCH_WINDOW_S)
    hi = np.searchsorted(p_time, s_time[0] + shift + steps.MATCH_WINDOW_S, side="right")
    if hi <= lo:
        return None
    i = lo + int(np.argmin(np.abs(p_bit[lo:hi] - s_bit[0])))
    return p_depth[i] + (s_bit[0] - p_bit[i]), p_error[i]


def pason_against_sanvean(pason, sanvean, align):
    """Pason rebuilt depth against the Sanvean rebuilt depth on runs 11 to 17."""
    p_time, p_bit, p_depth = pason
    for run, (s_time, s_bit, s_depth) in sanvean.items():
        pairs = matched(p_time, p_bit, s_time, s_bit, align[run])
        if not pairs:
            continue
        i, j = (np.array(x) for x in zip(*pairs))
        diff = np.abs((p_depth[i] - p_bit[i]) - (s_depth[j] - s_bit[j]))
        diff = diff[np.isfinite(diff)]
        if len(diff):
            yield dict(assembly=run, samples=len(diff), median_abs_ft=round(float(np.median(diff)), 2),
                       p95_abs_ft=round(float(np.percentile(diff, 95)), 2),
                       max_abs_ft=round(float(diff.max()), 2))


def segment_rows(time, bit, hole, depth, error, intervals, label):
    """Maps from the recorded depth, one row per constant piece.

    Off bottom, depth = intercept + scale x recorded bit. A drilling spell
    is one row that follows the recorded hole depth.
    """
    on_bottom = drilling(time, bit, hole)
    rows = []
    for first, last in drilling_spells(on_bottom):
        rows.append(dict(label, start=iso(time[first]), end=iso(time[last]), scale="", intercept_ft="",
                         follows_hole=1, run="", basis="drilling", max_uncertainty_ft=0.))
    for iv in intervals:
        a, b, s = iv["a"], iv["b"], iv["scale"]
        idx = np.arange(a, b + 1)
        idx = idx[np.isfinite(bit[idx]) & np.isfinite(depth[idx]) & ~on_bottom[idx]]
        if not len(idx):
            continue
        slope = s if "recorded, no reference" not in iv["flag"] else 1.
        intercept = depth[idx] - slope * bit[idx]
        # Glitch excursions shift the intercept, and drilling samples split a
        # span; emit one row per constant, contiguous run.
        breaks = np.flatnonzero((np.abs(np.diff(intercept)) > 1e-6) | (np.diff(idx) != 1)) + 1
        for piece in np.split(np.arange(len(idx)), breaks):
            errs = error[idx[piece]]
            rows.append(dict(label, start=iso(time[idx[piece[0]]]), end=iso(time[idx[piece[-1]]]),
                             scale=round(float(slope), 6), intercept_ft=round(float(intercept[piece[0]]), 4),
                             follows_hole=0, run=iv["run"], basis=iv["basis"],
                             max_uncertainty_ft=round(float(np.max(errs)), 2) if np.isfinite(errs).all() else ""))
    rows.sort(key=lambda r: (r["start"], r["follows_hole"]))
    return rows


def interval_rows(time, intervals, label):
    def describe(mark, default):
        if mark is None:
            return default
        if mark["kind"] == "run start":
            return "run start"
        if mark["kind"] == "unknown":
            jump = mark.get("implied_jump_ft")
            return f"{mark['cls']}" + (f" (implied jump {jump:.2f})" if jump is not None else "")
        return f"{mark['cls']} {mark['value']:.2f}"

    for iv in intervals:
        yield dict(label, start=iso(time[iv["a"]]), end=iso(time[iv["b"]]), run=iv["run"],
                   left=describe(iv["left"], "record start"),
                   right=describe(iv["right"], "record end"),
                   rig_ft=round(float(iv["rig_ft"]), 2), travel_ft=round(float(iv["travel_ft"]), 2),
                   span_ft=round(float(iv["span_ft"]), 2), scale=round(float(iv["scale"]), 4),
                   basis=iv["basis"], misclosure_ft=round(float(iv["misclosure_ft"]), 2), flag=iv["flag"])


def classified_events(time, bit, hole, block, hook, threshold):
    rows = steps.classified(time, bit, hole, block, hook, threshold)
    for row in rows:
        row.setdefault("final_class", row["class"])
    return rows


def sanvean_record(run):
    time, bit, hole, block, hook = rebuild.sanvean_inputs(run)
    threshold = np.full(len(time), rebuild.SLIPS_KLBS)
    return time, bit, hole, block, hook, threshold, classified_events(time, bit, hole, block, hook, threshold)


def alignment():
    return {int(r["eow_bha"]): int(r["pason_minus_sanvean_s"])
            for r in csv.DictReader((HERE / "clock-alignment.csv").open(encoding="utf-8-sig"))}


def imported_entries(time, bit, block, events, sanvean, align):
    """Sanvean anchors that the ten-second record takes as motion.

    A Sanvean entry made while the string hangs can fall inside a Pason
    sample with string motion and pass the ten-second rules. It enters the
    Pason record as an anchor on the Pason step that contains it: the
    largest step in the entry's direction within MATCH_WINDOW_S of the
    aligned time. Its value is the Sanvean recorded depth, after the
    entry, nearest the Pason recorded depth at that sample.
    """
    matched = {(row.get("sanvean_end"), row.get("sanvean_after_ft")) for row in events}
    taken = {i for row in events for i in range(row["first"], row["last"] + 1)}
    extra = []
    for run, rec in sanvean.items():
        s_time, s_bit = rec[0], rec[1]
        for s in rec[6]:
            if s["final_class"] not in ANCHORS or (iso(s["end"]), s["after_ft"]) in matched:
                continue
            centre = s["end"] + align[run]
            lo = max(int(np.searchsorted(time, centre - steps.MATCH_WINDOW_S)), 1)
            hi = int(np.searchsorted(time, centre + steps.MATCH_WINDOW_S, side="right"))
            if hi <= lo:
                continue
            candidates = np.arange(lo, hi)
            i = int(candidates[np.argmax(np.sign(s["step_ft"]) * np.diff(bit)[candidates - 1])])
            if i in taken or i - 1 in taken:
                continue
            after = np.arange(s["last"], min(len(s_time), s["last"] + 2 * int(steps.MATCH_WINDOW_S) + 1))
            j = int(after[np.argmin(np.abs(s_bit[after] - bit[i]))])
            extra.append({"first": i - 1, "last": i, "start": time[i - 1], "end": time[i],
                          "step_ft": bit[i] - bit[i - 1], "before_ft": bit[i - 1],
                          "after_ft": float(s_bit[j]), "block_travel_ft": abs(block[i] - block[i - 1]),
                          "hole_step_ft": 0., "class": "imported", "final_class": s["final_class"],
                          "sanvean_class": s["final_class"], "sanvean_after_ft": s["after_ft"],
                          "sanvean_end": iso(s["end"]), "pair": ""})
    return extra


def pason_record(archive, sanvean):
    time, bit, hole, block, hook, threshold = rebuild.pason_inputs(archive)
    events = classified_events(time, bit, hole, block, hook, threshold)
    trips = {run: (rec[0][0], rec[0][-1], rec[6]) for run, rec in sanvean.items()}
    align = alignment()
    steps.match_sanvean(events, trips, align)
    events = sorted(events + imported_entries(time, bit, block, events, sanvean, align),
                    key=lambda row: row["first"])
    return time, bit, hole, block, hook, threshold, events


def records(archive):
    """The Pason record and the seven Sanvean records, each rebuilt.

    Each Sanvean record starts inside a trip. Its first sample takes the
    Pason rebuilt depth as an anchor, matched on recorded depth, and its
    uncertainty rates come from the Pason runs.
    """
    sanvean = {run: sanvean_record(run) for run in range(11, 18)}
    pason = pason_record(archive, sanvean)
    p_result = entry_depth(*pason)
    yield "pason", "", pason, p_result
    align = alignment()
    rates = p_result[2][0]["rates"]
    for run, rec in sanvean.items():
        start = start_anchor(pason[0], pason[1], p_result[0], p_result[1], rec[0], rec[1], align[run])
        yield "sanvean", run, rec, entry_depth(*rec, start=start, rates=rates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="16B_Pason.zip from GDR 1516")
    args = parser.parse_args()
    segments, table, scale_rows, closings, breaches, yielded, stands = [], [], [], [], [], [], []
    rebuilt = {}
    for clock, run, rec, (depth, error, intervals, scales) in records(args.archive):
        time, bit, hole = rec[:3]
        label = dict(clock=clock, assembly=run)
        rebuilt[(clock, run)] = (time, bit, depth)
        if clock == "sanvean":
            stands += [dict(label, **row) for row in stand_counts(time, bit, rec[3], rec[4], rec[5], rec[6], depth)]
        segments += segment_rows(time, bit, hole, depth, error, intervals, label)
        table += list(interval_rows(time, intervals, label))
        scale_rows += [dict(label, run=k, start=iso(v["start"]), end=iso(v["end"]), pipe=v["pipe"],
                            anchors=v["anchors"], fitted=v["fitted"], scale=round(v["scale"], 4),
                            basis=v["basis"], error_rate=round(float(v["error_rate"]), 4),
                            half_spread=round(v["half_spread"], 4) if np.isfinite(v["half_spread"]) else "")
                       for k, v in sorted(scales.items())]
        closings += [dict(label, **row) for row in closing_rows(time, intervals)]
        breaches += [dict(label, **row) for row in bound_breaches(time, bit, hole, depth)]
        yielded += [dict(label, **row) for row in yielded_rows(time, intervals)]
    rebuild.write(OUT / "segments.csv", segments)
    rebuild.write(OUT / "intervals.csv", table)
    rebuild.write(OUT / "run-scales.csv", scale_rows)
    rebuild.write(OUT / "closing-misclosure.csv", closings)
    if breaches:
        rebuild.write(OUT / "bit-below-hole.csv", breaches)
    else:
        (OUT / "bit-below-hole.csv").write_bytes(
            b"clock,assembly,start,end,samples,max_below_hole_ft,hole_ft\n")
    rebuild.write(OUT / "entries-on-drilling.csv", yielded)
    rebuild.write(OUT / "stand-counts.csv", stands)
    sanvean = {run: rebuilt[("sanvean", run)] for run in range(11, 18)}
    rebuild.write(OUT / "pason-against-sanvean.csv",
                  pason_against_sanvean(rebuilt[("pason", "")], sanvean, alignment()))


if __name__ == "__main__":
    main()
