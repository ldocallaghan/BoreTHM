"""Checks of the FORGE 16B trip-depth rebuild on synthetic rig records."""
import numpy as np

from validation.forge16b.sanvean import depth_rebuild as r

SLIPS = 52.


def trip(depth0, depth1, *, stand=90., speed=5., wait=20, step=1.):
    """One-second record of running stands: lower while hanging, then slips."""
    t, bit, block, hook = [], [], [], []
    now, z, b = 0., depth0, 0.
    while z < depth1 - 1e-9:
        lower = min(stand, depth1 - z)
        for _ in range(int(round(lower / speed / step))):
            now += step; z += speed * step; b -= speed * step
            t.append(now); bit.append(z); block.append(b); hook.append(150.)
        n = int(wait / step)
        for k in range(n):                         # set slips, pick up next stand
            now += step
            if 0 < k < n - 1:                      # the block rests at each end
                b += lower / (n - 2)
            t.append(now); bit.append(z); block.append(b); hook.append(30.)
    return [np.array(x) for x in (t, bit, block, hook)]


def drilling_tail(t, bit, block, hook, hole0, n=30):
    """Append drilling samples: hole advances with the bit on bottom."""
    t2 = t[-1] + np.arange(1, n + 1)
    z = hole0 + 0.1 * np.arange(1, n + 1) + 0.2
    return (np.r_[t, t2], np.r_[bit, z], np.r_[block, block[-1] - (z - hole0)],
            np.r_[hook, np.full(n, 150.)], np.r_[np.full(len(t), hole0), z])


def test_trip_in_resets_are_removed_and_anchored_at_bottom():
    t, true, block, hook = trip(1000., 3000.)
    t, true, block, hook, hole = drilling_tail(t, true, block, hook, 3000.)
    recorded = true.copy()
    k1 = np.flatnonzero(hook < SLIPS)[5]           # a reset in the slips
    recorded[k1:] -= 300.
    k2 = np.flatnonzero(hook > SLIPS)[200]          # a reset while hanging
    recorded[k2:] += 300.
    offset, resets = r.offsets(t, recorded, hole, block, hook, np.full(len(t), SLIPS))
    assert resets.sum() == 2
    np.testing.assert_allclose(recorded + offset, true, atol=1e-9)


def test_block_rebuild_follows_hanging_travel_and_skips_encoder_resets():
    t, true, block, hook = trip(1000., 2000.)
    i = np.flatnonzero(hook < SLIPS)[10]
    block = block.copy(); block[i:] += 500.         # encoder reset while in slips
    rebuilt, resets = r.block_rebuild(t, block, hook, np.full(len(t), SLIPS), len(t) - 1, true[-1])
    assert resets.sum() == 1
    np.testing.assert_allclose(rebuilt, true, atol=1e-9)


def test_coarse_sampling_flags_only_impossible_steps():
    t, true, block, hook = trip(1000., 3000., step=1.)
    coarse = slice(None, None, 10)
    t, true, block, hook = t[coarse], true[coarse], block[coarse], hook[coarse]
    assert not r.tally_resets(t, true, block, hook, np.full(len(t), SLIPS)).any()
    recorded = true.copy(); recorded[40:] += 250.   # faster than the string travels
    assert r.tally_resets(t, recorded, block, hook, np.full(len(t), SLIPS)).sum() == 1


def test_trip_out_takes_its_offset_forward_and_connections_keep_the_record():
    # drilling, a connection gap near bottom, drilling, trip out to surface,
    # trip in, drilling. The trip out has a reset; so does the trip in.
    t_in, z_in, b_in, h_in = trip(100., 2000.)
    z_out = z_in[::-1].copy()
    n_out = len(z_out)
    time = np.arange(5 + 20 + 5 + n_out + len(z_in) + 5, dtype=float)
    true = np.r_[np.full(5, 2000.), np.full(20, 1990.), np.full(5, 2000.), z_out, z_in, np.full(5, 2000.)]
    hole = np.full(len(true), 2000.)
    for start, base in ((0, 2000.), (25, 2000.), (len(true) - 5, 2001.)):
        hole[start:start + 5] = base + 0.2 * np.arange(1, 6)   # drilling advances the hole
        true[start:start + 5] = hole[start:start + 5]
    hole[5:25] = hole[4]
    hole[30:len(true) - 5] = hole[29]
    true[30:len(true) - 5] = np.minimum(true[30:len(true) - 5], hole[29])
    block = -true.copy()
    hook = np.full(len(true), 150.)
    recorded = true.copy()
    out_reset, in_reset = 30 + n_out // 2, 30 + n_out + len(z_in) // 2
    recorded[out_reset:] += 200.
    recorded[in_reset:] -= 200.
    offset, _ = r.offsets(time, recorded, hole, block, hook, np.full(len(time), SLIPS))
    np.testing.assert_allclose((recorded + offset)[30:len(true) - 5], true[30:len(true) - 5], atol=1e-9)
    np.testing.assert_allclose(offset[5:25], 0.)    # the connection keeps the record


def test_after_the_last_anchor_only_the_trip_out_is_rebuilt():
    t_in, z_in, _, _ = trip(100., 2000.)
    true = np.r_[2000. + 0.2 * np.arange(1, 6), z_in[::-1], z_in]
    hole = np.r_[true[:5], np.full(len(true) - 5, true[4])]
    time = np.arange(len(true), dtype=float)
    block, hook = -true.copy(), np.full(len(true), 150.)
    recorded = true.copy()
    out_reset, in_reset = 5 + len(z_in) // 2, 5 + len(z_in) + len(z_in) // 2
    recorded[out_reset:] += 200.
    recorded[in_reset:] -= 200.
    offset, _ = r.offsets(time, recorded, hole, block, hook, np.full(len(time), SLIPS))
    out = slice(None, 4 + len(z_in))                  # up to the shallowest point
    np.testing.assert_allclose((recorded + offset)[out], true[out], atol=1e-9)
    np.testing.assert_allclose(offset[5 + len(z_in):], 0.)   # no anchor for the trip in


def test_a_reset_undone_as_drilling_resumes_cancels():
    # One sample reads 500 ft shallow at bottom; the next returns to bottom
    # as the hole advances a few feet. Neither step moves the hole with the bit.
    t, true, block, hook = trip(1000., 3000., step=10.)
    t, true, block, hook, hole = drilling_tail(t, true, block, hook, 3000.)
    t = np.arange(len(t)) * 10.
    recorded = true.copy()
    k = len(true) - 31
    recorded[k] -= 500.
    hole[k + 1:] += 5.
    true[k + 1:] += 5.; recorded[k + 1:] += 5.
    offset, resets = r.offsets(t, recorded, hole, block, hook, np.full(len(t), SLIPS))
    assert resets.sum() == 2
    # At ten seconds the string motion inside the restoring step stays in
    # the offset, so the error is bounded by that motion.
    motion = true[k + 1] - true[k - 1]
    assert np.abs((recorded + offset)[:k] - true[:k]).max() <= motion + 1e-9
