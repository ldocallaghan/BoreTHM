"""Bit depth from the driller's tally entries and a scale on the rig increments.

The rig integrates block travel into bit depth, and the block encoder
drifts by several feet per stand. The driller corrects the drift by typing
depths from the pipe tally. depth_steps.py classifies those entries. This
module takes them as the depth reference.

Anchors. A typed entry fixes the depth at its sample to its entered value.
A Pason entry inside a one-second Sanvean trip is classified by its
Sanvean match. A Sanvean entry with no Pason step, taken as motion at ten
seconds, enters the Pason record at the next Pason sample with the
Sanvean recorded depth there. Each Sanvean record starts inside a trip,
so its first sample takes the Pason rebuilt depth, matched on recorded
depth within MATCH_WINDOW_S, as an anchor. A pick-up entry is an anchor whose value is uncertain by
the block travel in its sample. A zero reset fixes the depth at 0 ft. A
glitch and its restore are removed and the interval between them is
continuous.

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
median scale applies.

A run with no fitted scale uses, on the one-second record, the sourced
stand length over the rig's mean complete loaded stroke in that run. At
ten seconds the slips transitions fall between samples and the stroke is
undercounted, so the ten-second record does not use it. A run with
neither borrows the median of the nearest run in time that has a fitted
scale.

Gaps and unresolved entries are unknown jumps. The spans on each side are
taken from their own anchors, and the implied jump is reported. Drilling
samples are a check. They anchor the depth only in a run with no other
anchor, and every such use is reported.

Uncertainty at a sample is the largest of: the anchor value uncertainty;
the misclosure of its interval scaled by the share of rig travel from the
earlier anchor; half the run's spread of fitted scales times the rig
travel to the nearest anchor (the largest spread in the record where a
run has fewer than two fitted scales); for insulated pipe, 1 ft per 119
ft stand over the same travel; and a fixed term where declared. A span
with no anchor and no drilling reference keeps the recorded depth and has
no stated uncertainty.

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

OUT = HERE / "depth-entries-2026-11-08"
SHORT_FT = 190.              # two stands: a shorter interval does not fit a scale
ROUND_TRIP = 2.              # travel over net increments that marks an out-and-back
SCALE_RANGE = (.85, 1.15)    # a fitted scale outside this flags the interval
TRIP_FT = rebuild.TRIP_FT
STAND_FT = 95.12             # 5.5 in S-135, 25 stands as 2,378 ft (GDR 1516 daily report 39)
INSULATED_STAND_FT = 119.    # 10 stands from 9,255 ft to 8,065 ft (daily report 40)
INSULATED_STAND_ERROR_FT = 1.
STROKE_RANGE_FT = (50., 130.)  # a complete loaded stroke of one stand
MIN_STROKES = 10             # fewer strokes do not give a mean
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
ANCHORS = ("typed_entry", "typed_entry_tenth", "pickup_entry", "zero_reset")
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


def trip_windows(bit, hole):
    """(start, end) sample pairs bracketing each excursion off bottom."""
    bit, hole = np.asarray(bit, dtype=float), np.asarray(hole, dtype=float)
    off = np.nan_to_num(hole - bit) > TRIP_FT
    drill = np.flatnonzero(rebuild.drilling(bit, hole))
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


def runs(bit, hole):
    """Run number per sample: the record cut at each trip's shallowest sample."""
    bit = np.asarray(bit, dtype=float)
    drilling = rebuild.drilling(bit, hole)
    cuts = []
    for start, end in trip_windows(bit, hole):
        # A record that starts or ends inside a trip has no drilling on
        # that side, and its shallowest sample is no turnaround.
        if drilling[start] and drilling[end]:
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


def entry_depth(time, bit, hole, block, hook, threshold, events, start=None):
    """Depth per sample, its uncertainty, the intervals and the run scales.

    start, if given, is (value, error): an anchor at the first sample, for
    a record that begins inside a trip after an entry it does not contain.
    """
    time, bit, hole = (np.asarray(x, dtype=float) for x in (time, bit, hole))
    n = len(bit)
    inc = increments(bit, events)
    cum = np.r_[0., np.cumsum(inc)]
    travel = np.r_[0., np.cumsum(np.abs(inc))]
    run = runs(bit, hole)
    drilling = rebuild.drilling(bit, hole)
    marks = breakpoints(events)
    if start is not None and not (marks and marks[0]["first"] == 0):
        marks.insert(0, dict(first=0, last=0, kind="anchor", cls="pason_start",
                             value=float(start[0]), error=float(start[1]), event=None))

    # Spans between consecutive breakpoints, also cut at run boundaries.
    # A span runs from the sample after its left breakpoint's step to the
    # sample before its right breakpoint's step.
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

    for iv in intervals:
        left, right = iv["left"], iv["right"]
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

    scales = {}
    for k in np.unique(run):
        fitted = [iv["scale"] for iv in intervals if iv["run"] == k and iv["basis"] == "fitted"]
        if fitted:
            spread = (max(fitted) - min(fitted)) / 2 if len(fitted) > 1 else np.nan
            scales[k] = dict(scale=float(np.median(fitted)), basis="run median", fitted=len(fitted),
                             half_spread=spread)
    for k in np.unique(run):
        if k in scales or not fine(time):
            continue
        s, count = stroke_scale(time, block, hook, threshold, run == k)
        if np.isfinite(s):
            scales[k] = dict(scale=s, basis=f"stand length over mean stroke ({count} strokes)",
                             fitted=0, half_spread=np.nan)
    centre = {k: float(np.median(time[run == k])) for k in np.unique(run)}
    ends = {k: float(time[run == k][-1]) for k in np.unique(run)}
    donors = [k for k in scales if scales[k]["fitted"] and ends[k] < SCOPE_END]
    donors = donors or [k for k in scales if scales[k]["fitted"]]
    for k in np.unique(run):
        if k in scales:
            continue
        if donors:
            near = min(donors, key=lambda d: abs(centre[d] - centre[k]))
            scales[k] = dict(scales[near], basis=f"borrowed from run {near}", fitted=0)
        else:
            scales[k] = dict(scale=1., basis="no scale available", fitted=0, half_spread=np.nan)
    spreads = [scales[k]["half_spread"] for k in donors if np.isfinite(scales[k]["half_spread"])]
    default_spread = float(np.max(spreads)) if spreads else 0.
    # A scale not fitted in its own run carries the spread between runs.
    medians = [scales[k]["scale"] for k in donors]
    between = (max(medians) - min(medians)) / 2 if len(medians) > 1 else default_spread
    for k, v in scales.items():
        v["error_rate"] = (v["half_spread"] if v["fitted"] and np.isfinite(v["half_spread"])
                           else default_spread if v["fitted"] else max(between, default_spread))
    for k, v in scales.items():
        v["start"], v["end"] = float(time[run == k][0]), float(time[run == k][-1])
        v["anchors"] = sum(1 for m in marks if m["kind"] == "anchor" and run[m["last"]] == k)

    has_anchor = {k: scales[k]["anchors"] > 0 for k in scales}
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
            if not has_anchor[k]:
                bottom = idx[drilling[idx]]
                if len(bottom):
                    j = bottom[0]
                    depth[idx] = hole[j] + s * (cum[idx] - cum[j])
                    distance[idx] = np.abs(travel[idx] - travel[j])
                    iv["flag"] = (iv["flag"] + "; " if iv["flag"] else "") + \
                        f"drilling anchor at {iso(time[j])}"
            if np.isnan(depth[idx]).all():
                depth[idx] = bit[idx]
                iv["flag"] = (iv["flag"] + "; " if iv["flag"] else "") + "recorded, no reference"
                iv["unreferenced"] = True
        rate = scales[k]["error_rate"]
        insulated = (time[idx] >= INSULATED[0]) & (time[idx] <= INSULATED[1])
        rate = np.where(insulated, max(rate, INSULATED_STAND_ERROR_FT / INSULATED_STAND_FT), rate)
        finite = np.isfinite(distance[idx])
        error[idx] = np.maximum(error[idx], np.where(finite, rate * np.where(finite, distance[idx], 0.), 0.))
    for start, end, value in FIXED:
        inside = (time >= start) & (time < end)
        error[inside] = np.maximum(error[inside], value)
    for iv in intervals:
        if iv.get("unreferenced"):
            error[iv["a"]:iv["b"] + 1] = np.nan     # no reference, so no stated bound

    # Implied jump at each unknown breakpoint, where both sides have depth.
    for iv, nxt in zip(intervals, intervals[1:]):
        right = iv["right"]
        if right is not None and right["kind"] == "unknown":
            before, after = iv["b"], nxt["a"]
            right["implied_jump_ft"] = float(depth[after] - depth[before])
            right["recorded_step_ft"] = float(bit[after] - bit[before])
    return depth, error, intervals, scales


def bottom_misclosures(time, bit, hole, depth):
    """Rebuilt minus hole depth at the first drilling sample after each trip."""
    drilling = rebuild.drilling(bit, hole)
    for start, end in trip_windows(bit, hole):
        if drilling[end]:
            yield dict(trip_start=iso(time[start]), bottom=iso(time[end]),
                       hole_ft=round(float(hole[end]), 2), recorded_ft=round(float(bit[end]), 2),
                       rebuilt_ft=round(float(depth[end]), 2),
                       misclosure_ft=round(float(depth[end] - hole[end]), 2))


def drilling_check(time, bit, hole, depth):
    """Rebuilt depth minus hole depth over the drilling samples of each run.

    While drilling the bit is on bottom, so the rebuilt depth should
    stay within a few feet of the hole depth. The hole depth advances on
    the same encoder, and the driller sets it from the tally; this check
    shows how far the run's scale carries the bit from it.
    """
    drilling = rebuild.drilling(bit, hole)
    run = runs(bit, hole)
    for k in np.unique(run):
        on = np.flatnonzero(drilling & (run == k))
        if not len(on):
            continue
        diff = depth[on] - hole[on]
        diff = diff[np.isfinite(diff)]
        if not len(diff):
            continue
        yield dict(run=int(k), first=iso(time[on[0]]), last=iso(time[on[-1]]), samples=len(on),
                   drilled_ft=round(float(hole[on[-1]] - hole[on[0]]), 2),
                   first_diff_ft=round(float(diff[0]), 2), last_diff_ft=round(float(diff[-1]), 2),
                   max_abs_diff_ft=round(float(np.max(np.abs(diff))), 2))


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


def segment_rows(time, bit, depth, error, intervals, label):
    """Linear maps depth = intercept + scale * recorded, one row per constant piece."""
    rows = []
    for iv in intervals:
        a, b, s = iv["a"], iv["b"], iv["scale"]
        idx = np.arange(a, b + 1)
        ok = np.isfinite(bit[idx]) & np.isfinite(depth[idx])
        if not ok.any():
            continue
        slope = s if "recorded, no reference" not in iv["flag"] else 1.
        intercept = depth[idx][ok] - slope * bit[idx][ok]
        # Glitch excursions shift the intercept; emit one row per constant run.
        breaks = np.flatnonzero(np.abs(np.diff(intercept)) > 1e-6) + 1
        times, errs = time[idx][ok], error[idx][ok]
        for piece in np.split(np.arange(ok.sum()), breaks):
            rows.append(dict(label, start=iso(times[piece[0]]), end=iso(times[piece[-1]]),
                             scale=round(float(slope), 6), intercept_ft=round(float(intercept[piece[0]]), 4),
                             run=iv["run"], basis=iv["basis"],
                             max_uncertainty_ft=round(float(np.max(errs[piece])), 2)))
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
    Pason rebuilt depth as an anchor, matched on recorded depth.
    """
    sanvean = {run: sanvean_record(run) for run in range(11, 18)}
    pason = pason_record(archive, sanvean)
    p_result = entry_depth(*pason)
    yield "pason", "", pason, p_result
    align = alignment()
    for run, rec in sanvean.items():
        start = start_anchor(pason[0], pason[1], p_result[0], p_result[1], rec[0], rec[1], align[run])
        yield "sanvean", run, rec, entry_depth(*rec, start=start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="16B_Pason.zip from GDR 1516")
    args = parser.parse_args()
    segments, table, scale_rows, bottoms, stands, drilled = [], [], [], [], [], []
    rebuilt = {}
    for clock, run, rec, (depth, error, intervals, scales) in records(args.archive):
        time, bit, hole = rec[:3]
        label = dict(clock=clock, assembly=run)
        rebuilt[(clock, run)] = (time, bit, depth)
        if clock == "sanvean":
            stands += [dict(label, **row) for row in stand_counts(time, bit, rec[3], rec[4], rec[5], rec[6], depth)]
        segments += segment_rows(time, bit, depth, error, intervals, label)
        table += list(interval_rows(time, intervals, label))
        scale_rows += [dict(label, run=k, start=iso(v["start"]), end=iso(v["end"]), anchors=v["anchors"],
                            fitted=v["fitted"], scale=round(v["scale"], 4), basis=v["basis"],
                            half_spread=round(v["half_spread"], 4) if np.isfinite(v["half_spread"]) else "")
                       for k, v in sorted(scales.items())]
        bottoms += [dict(label, **row) for row in bottom_misclosures(time, bit, hole, depth)]
        drilled += [dict(label, **row) for row in drilling_check(time, bit, hole, depth)]
    rebuild.write(OUT / "segments.csv", segments)
    rebuild.write(OUT / "intervals.csv", table)
    rebuild.write(OUT / "run-scales.csv", scale_rows)
    rebuild.write(OUT / "bottom-misclosure.csv", bottoms)
    rebuild.write(OUT / "stand-counts.csv", stands)
    rebuild.write(OUT / "drilling-check.csv", drilled)
    sanvean = {run: rebuilt[("sanvean", run)] for run in range(11, 18)}
    rebuild.write(OUT / "pason-against-sanvean.csv",
                  pason_against_sanvean(rebuilt[("pason", "")], sanvean, alignment()))


if __name__ == "__main__":
    main()
