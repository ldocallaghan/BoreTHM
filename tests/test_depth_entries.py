"""Checks of the tally-entry bit depth on synthetic rig records."""
import numpy as np

from validation.forge16b.sanvean import depth_entries as e

SLIPS = 52.
STAND = 95.
ENCODER = 89.          # the encoder reads this much per true stand


def trip_in(start=1000., stands=40, speed=5., wait=20, encoder=ENCODER):
    """One-second trip in: true depth, encoder-recorded depth, block, hook.

    The block travel and the recorded increments follow the encoder, which
    reads `encoder` per true STAND.
    """
    k = encoder / STAND
    t, true, rec, block, hook = [], [], [], [], []
    now, z, r, b = 0., start, start, 0.
    for _ in range(stands):
        for _ in range(int(STAND / speed)):
            now += 1; z += speed; r += speed * k; b -= speed * k
            t.append(now); true.append(z); rec.append(r); block.append(b); hook.append(150.)
        for j in range(wait):
            now += 1
            if 0 < j < wait - 1:
                b += STAND * k / (wait - 2)
            t.append(now); true.append(z); rec.append(r); block.append(b); hook.append(30.)
    return [np.array(x) for x in (t, true, rec, block, hook)]


def enter(true, rec, at):
    """Type the true depth in at sample `at`: the record jumps and continues."""
    rec = rec.copy()
    rec[at:] += true[at] - rec[at]
    return rec


def slips_samples(hook):
    """Last slips sample of each slips spell, where an entry is typed."""
    s = hook < SLIPS
    return np.flatnonzero(s[:-1] & ~s[1:])


def run(t, rec, hole, block, hook):
    thr = np.full(len(t), SLIPS)
    events = e.classified_events(t, rec, hole, block, hook, thr)
    return e.entry_depth(t, rec, hole, block, hook, thr, events), events


def test_encoder_drift_with_entries_is_recovered_exactly():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    for at in ends[[5, 15, 25, 35]]:
        rec = enter(true, rec, at)
    hole = np.full(len(t), 9000.)
    (depth, error, intervals, _), events = run(t, rec, hole, block, hook)
    assert [ev["final_class"] for ev in events] == ["typed_entry"] * 4
    inside = slice(ends[5], ends[35] + 1)
    np.testing.assert_allclose(depth[inside], true[inside], atol=1e-6)
    fitted = [iv["scale"] for iv in intervals if iv["basis"] == "fitted"]
    np.testing.assert_allclose(fitted, STAND / ENCODER)


def test_the_run_median_scale_applies_outside_the_anchors():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    for at in ends[[10, 20, 30]]:
        rec = enter(true, rec, at)
    hole = np.full(len(t), 9000.)
    (depth, *_), _ = run(t, rec, hole, block, hook)
    np.testing.assert_allclose(depth, true, atol=1e-6)


def test_glitch_and_restore_leave_the_depth_continuous():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    for at in ends[[5, 25]]:
        rec = enter(true, rec, at)
    i = ends[15] - 5                       # hanging, just before the slips
    rec[i:i + 30] -= 495.36                # an excursion restored 30 s later
    hole = np.full(len(t), 9000.)
    (depth, *_), events = run(t, rec, hole, block, hook)
    assert [ev["final_class"] for ev in events] == ["typed_entry", "glitch", "restore", "typed_entry"]
    inside = slice(ends[5], ends[25] + 1)
    np.testing.assert_allclose(depth[inside], true[inside], atol=1e-6)


def test_an_entry_that_moves_both_channels_anchors_the_bit():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    hole = np.full(len(t), 9000.)
    for at in ends[[5, 15, 25]]:
        rec = enter(true, rec, at)
    at = ends[15]
    hole[at:] = hole[at] + true[at] - rec[at - 1] + 3000.  # the hole moves too
    (depth, *_), events = run(t, rec, hole, block, hook)
    assert events[1]["final_class"] == "typed_entry"
    inside = slice(ends[5], ends[25] + 1)
    np.testing.assert_allclose(depth[inside], true[inside], atol=1e-6)


def test_a_gap_is_an_unknown_jump_with_anchors_on_each_side():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    g = ends[18] + 3                       # hanging, mid stroke
    t = t.copy(); t[g:] += 120.            # two minutes lost
    rec[g:] += 140.                        # and the record jumps unseen
    for at in ends[[5, 12, 25, 35]]:
        rec = enter(true, rec, at)
    hole = np.full(len(t), 9000.)
    (depth, _, intervals, _), events = run(t, rec, hole, block, hook)
    assert "gap" in [ev["final_class"] for ev in events]
    for part in (slice(ends[5], ends[12] + 1), slice(ends[25], ends[35] + 1)):
        np.testing.assert_allclose(depth[part], true[part], atol=1e-6)
    gap = [ev for ev in events if ev["final_class"] == "gap"][0]
    assert np.isfinite(depth[gap["last"]]) and np.isfinite(depth[gap["first"]])


def test_a_short_interval_uses_the_run_median_and_reports_misclosure():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    for at in ends[[5, 15, 17, 30]]:       # 15 to 17 is two stands, 178 ft of rig travel
        rec = enter(true, rec, at)
    rec[ends[15]:ends[17]] -= 20.          # the entry at 15 is typed 20 ft shallow
    hole = np.full(len(t), 9000.)
    (depth, error, intervals, _), events = run(t, rec, hole, block, hook)
    assert [ev["final_class"] for ev in events] == ["typed_entry"] * 4
    short = [iv for iv in intervals if iv["flag"] == "short"]
    assert len(short) == 1
    assert short[0]["basis"] == "run median"
    # The wrong entry also biases the fitted interval before it, and so the
    # run median: misclosure = -20 + rig travel x (median - true scale).
    expected = -20. + short[0]["rig_ft"] * (short[0]["scale"] - STAND / ENCODER)
    assert abs(short[0]["misclosure_ft"] - expected) < 1e-6
    after = slice(ends[17], ends[30] + 1)
    np.testing.assert_allclose(depth[after], true[after], atol=1e-6)
    assert error[ends[17] - 1] > 15.        # the misclosure carries into the interval


def test_an_implausible_scale_is_flagged_and_not_used():
    t, true, rec, block, hook = trip_in()
    ends = slips_samples(hook)
    for at in ends[[5, 15, 25, 35]]:
        rec = enter(true, rec, at)
    rec[ends[25]:] -= 400.                 # an entry typed 400 ft wrong
    rec[ends[35]:] += 400.                 # and corrected at the next entry
    hole = np.full(len(t), 9000.)
    (_, _, intervals, _), _ = run(t, rec, hole, block, hook)
    flags = [iv["flag"] for iv in intervals if iv["flag"]]
    assert len(flags) == 2 and all(f.startswith("implausible scale") for f in flags)


def test_runs_are_cut_at_the_turnaround_and_spans_stay_inside_them():
    drill1 = 3000. + np.arange(6)
    out = np.arange(3005., -1., -50.)
    back = np.arange(5., 3006., 50.)
    drill2 = 3006. + np.arange(6)
    bit = np.r_[drill1, out, back, drill2]
    hole = np.r_[drill1, np.full(len(out) + len(back), 3005.), drill2]
    time = np.arange(len(bit)) * 10.
    run_of = e.runs(time, bit, hole)
    cut = len(drill1) + int(np.argmin(out))
    assert run_of[cut - 1] == 0 and run_of[cut] == 1 and set(run_of) == {0, 1}
    block = np.full(len(bit), 50.)
    hook = np.full(len(bit), 150.)
    thr = np.full(len(bit), SLIPS)
    depth, _, intervals, scales = e.entry_depth(time, bit, hole, block, hook, thr, [])
    assert sorted(scales) == [0, 1]
    for iv in intervals:
        assert run_of[iv["a"]] == run_of[iv["b"]]
        assert any(m is not None and m.get("cls") == "drilling" for m in (iv["left"], iv["right"]))
    np.testing.assert_allclose(depth, bit)


def drill(t0, true0, rec0, block0, n=12, rate=.2):
    """One-second drilling: hole and true depth advance; the record follows
    the encoder and stays within a few feet of the hole."""
    k = np.arange(1, n + 1)
    true = true0 + rate * k
    return (t0 + k, true, rec0 + rate * k * .99, block0 - rate * k, np.full(n, 150.), true)


def round_trip(entries_in, encoder=94.5):
    """Drill, trip out to surface, trip in with entries, drill again.

    Returns time, true, recorded, block, hook, hole and the trip-in entry
    samples. The encoder drifts by STAND - encoder ft per stand.
    """
    t1, true1, rec1, block1, hook1 = trip_in(start=200., stands=30, encoder=encoder)
    top = true1[-1]
    d1 = drill(-13., top - 12 * .2, top - 12 * .2, 0.)
    out = slice(None, None, -1)
    t_out = d1[0][-1] + t1
    rec_out = top - (rec1[-1] - rec1[out])
    t_in = t_out[-1] + t1
    rec_in = rec_out[-1] + (rec1 - rec1[0]) + (rec1[0] - 200.)
    d2 = drill(t_in[-1], true1[-1], rec_in[-1], block1[-1])
    time = np.r_[d1[0], t_out, t_in, d2[0]]
    true = np.r_[d1[1], true1[out], true1, d2[1]]
    rec = np.r_[d1[2], rec_out, rec_in, d2[2]]
    block = np.r_[d1[3], block1[out], block1, d2[3]]
    hook = np.r_[d1[4], hook1[out], hook1, d2[4]]
    hole = np.r_[d1[5], np.full(len(t_out) + len(t_in), top), d2[5]]
    offset = len(d1[0]) + len(t_out)
    slips = hook < SLIPS
    ends = np.flatnonzero(~slips[:-1] & slips[1:]) + 1     # first slips sample of each spell
    ends = ends[(ends > offset) & (ends < offset + len(t_in))]
    at = ends[entries_in]
    for k in at:
        rec = enter(true, rec, k)
    rec[offset + len(t_in):] = d2[2] - d2[2][0] + rec[offset + len(t_in) - 1] + .2 * .99
    return time, true, rec, block, hook, hole, at, offset + len(t_in)


def test_drilled_footage_follows_the_hole_and_the_trip_closes_on_it():
    time, true, rec, block, hook, hole, at, bottom = round_trip([5, 15, 25])
    (depth, error, intervals, scales), events = run(time, rec, hole, block, hook)
    assert all(ev["final_class"] == "typed_entry_small" for ev in events)
    drilling = e.drilling(time, rec, hole)
    assert drilling[bottom:].any()
    np.testing.assert_allclose(depth[drilling], hole[drilling])
    np.testing.assert_allclose(error[drilling], 0.)
    trip_in_part = slice(at[0], bottom)
    np.testing.assert_allclose(depth[trip_in_part], true[trip_in_part], atol=1e-2)
    closing = [iv for iv in intervals if iv.get("closing")]
    assert len(closing) == 1 and closing[0]["basis"] == "fitted"
    rows = list(e.closing_rows(time, intervals))
    assert abs(rows[0]["misclosure_ft"]) < 1e-6
    assert not list(e.bound_breaches(time, rec, hole, depth))


def test_the_bound_reports_a_bit_below_the_hole():
    time = np.arange(10.)
    hole = np.full(10, 5000.)
    depth = hole - 50.
    depth[4:6] = hole[4:6] + 12.
    rows = list(e.bound_breaches(time, depth, hole, depth))
    assert len(rows) == 1 and rows[0]["samples"] == 2 and rows[0]["max_below_hole_ft"] == 12.


def test_a_run_borrows_only_from_a_run_with_two_fits():
    time, true, rec, block, hook, hole, at, bottom = round_trip([5, 15, 25])
    (_, _, _, scales), _ = run(time, rec, hole, block, hook)
    assert scales[1]["fitted"] >= 2
    assert scales[0]["basis"] == "borrowed from run 1"
    time, true, rec, block, hook, hole, at, bottom = round_trip([25])
    (_, _, _, scales), _ = run(time, rec, hole, block, hook)
    assert scales[1]["fitted"] == 1
    assert not scales[0]["basis"].startswith("borrowed")
