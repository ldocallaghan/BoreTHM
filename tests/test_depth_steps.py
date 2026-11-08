"""Checks of the FORGE 16B bit-depth step classifier on synthetic rig records."""
import numpy as np

from validation.forge16b.sanvean import depth_steps as s

SLIPS = 52.


def still(n=40, depth=1000.37, step=1., hook=30.):
    """A record in the slips with the block still."""
    time = np.arange(n) * step
    return (time, np.full(n, depth), np.full(n, 9000.), np.full(n, 50.),
            np.full(n, hook), np.full(n, SLIPS))


def classes(time, bit, hole, block, hook, threshold):
    return [r["class"] for r in s.classified(time, bit, hole, block, hook, threshold)]


def test_grid():
    assert s.grid(5997.0) == "foot"
    assert s.grid(3145.3) == "tenth"
    assert s.grid(4788.58) == ""
    assert s.grid(np.nan) == ""


def test_typed_entries_to_the_foot_and_to_the_tenth():
    time, bit, hole, block, hook, thr = still()
    bit[10:] = 1488.00
    bit[25:] = 1600.30
    assert classes(time, bit, hole, block, hook, thr) == ["typed_entry", "typed_entry_tenth"]


def test_a_tenth_landing_that_moves_on_is_unresolved():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[:] = 150.
    bit[10:] = 3145.30
    bit[11:] = 3145.30 + 3.86 * np.arange(1, 30)   # the string moves on at once
    block[11:] = 50. - 3.86 * np.arange(1, 30)
    assert classes(time, bit, hole, block, hook, thr) == ["unresolved_entry"]


def test_an_entry_made_as_the_string_is_picked_up():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[10:] = 120.                      # slips to hanging within the sample
    bit[10:] = 658.03                     # entry plus pick-up motion
    block[10:] += 2.03
    assert classes(time, bit, hole, block, hook, thr) == ["pickup_entry"]


def test_a_fast_pull_with_the_block_is_motion():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[:] = 110.
    bit[10:] -= 60.8                      # 6.08 ft/s up, just over the ascent limit
    block[10:] += 27.6                     # the block rises with the bit
    assert classes(time, bit, hole, block, hook, thr) == ["motion"]


def test_block_travel_against_the_bit_step_is_not_motion():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[:] = 90.
    bit[10:] -= 109.87                    # bit up
    block[10:] -= 10.69                   # block down
    assert classes(time, bit, hole, block, hook, thr) == ["unresolved_entry"]


def test_setting_the_bit_to_the_hole_depth_is_an_entry():
    time, bit, hole, block, hook, thr = still()
    hole[:] = 6170.03
    bit[:10] = 6091.81
    bit[10:] = 6170.03
    rows = s.classified(time, bit, hole, block, hook, thr)
    assert [(r["class"], r["landing"]) for r in rows] == [("typed_entry", "hole")]


def test_small_entries_land_on_a_whole_foot_with_the_block_still():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[:] = 150.
    bit[10:] = 1003.00                    # 2.63 ft, block still, flat after
    bit[20:] = 1007.40                    # a tenth landing below the candidates
    bit[30:] = 1010.00
    block[30:] += .6                      # the block moves over the step
    rows = s.classified(time, bit, hole, block, hook, thr)
    assert [(r["class"], r["after_ft"]) for r in rows] == [("typed_entry_small", 1003.0)]


def test_a_split_entry_is_merged_before_testing():
    time, bit, hole, block, hook, thr = still()
    bit[10] = 1031.75                     # interpolated midpoint
    bit[11:] = 1079.00
    rows = s.classified(time, bit, hole, block, hook, thr)
    assert [r["class"] for r in rows] == ["typed_entry"]
    assert rows[0]["merged"] and rows[0]["after_ft"] == 1079.0


def test_reset_to_zero():
    time, bit, hole, block, hook, thr = still()
    bit[10:] = 0.
    assert classes(time, bit, hole, block, hook, thr) == ["zero_reset"]


def test_glitch_and_restore_with_motion_between():
    time, bit, hole, block, hook, thr = still(step=10.)
    hook[:] = 150.                        # hanging, so only speed flags a step
    bit[10:15] = 505.6 + np.arange(5) * .5  # 494.77 ft shallow, string creeping
    bit[15:] = 1000.37 + 2.5 + 5.
    assert classes(time, bit, hole, block, hook, thr) == ["glitch", "restore"]


def test_a_step_across_a_long_gap_is_unresolved():
    time, bit, hole, block, hook, thr = still()
    time[20:] += 60.                      # one step spans 61 s
    hook[:] = 150.
    bit[20:] = 1500.                      # 500 ft in 61 s passes the speed test
    assert classes(time, bit, hole, block, hook, thr) == ["gap"]


def test_an_entry_mixed_with_motion_in_the_slips_is_unresolved():
    time, bit, hole, block, hook, thr = still(step=10.)
    bit[10:] = 1141.73 + 5.58             # entry plus 5.58 ft of motion in the sample
    block[10:] -= 5.58
    assert classes(time, bit, hole, block, hook, thr) == ["unresolved_entry"]


def test_pason_takes_the_sanvean_class_when_one_event_matches():
    pason = [dict(end=1000., cls="other"), dict(end=5000., cls="other"), dict(end=9000., cls="other")]
    pason = [dict(end=p["end"], **{"class": p["cls"]}) for p in pason]
    sanvean = {17: (0., 6000., [dict(end=993., after_ft=4783.0, **{"class": "typed_entry"})])}
    rows = s.match_sanvean(pason, sanvean, {17: 7})
    assert [r["final_class"] for r in rows] == ["typed_entry", "unmatched_in_sanvean", "other"]
    assert rows[0]["sanvean_after_ft"] == 4783.0
