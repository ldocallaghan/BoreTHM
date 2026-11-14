import importlib

import numpy as np
import pytest

events = importlib.import_module("validation.model-development.entry-15.run17_events")
convergence = importlib.import_module("validation.model-development.entry-15.run17_convergence")

STRING = [(10., .08, .002), (20., .06, .003), (1000., .05, .004)]   # bit upwards


def test_string_volumes_keep_bore_and_displaced_volume():
    faces = np.linspace(0., 60., 13)
    full = np.full(12, np.pi*.1**2*5.)
    bore, annulus = events.string_volumes(faces, full, STRING, 42.)
    # The string occupies 42 m: 10 m bit section, 20 m middle, 12 m top pipe.
    assert bore.sum() == pytest.approx(10*.002+20*.003+12*.004)
    displaced = (full-annulus).sum()
    assert displaced == pytest.approx(np.pi*(10*.08**2+20*.06**2+12*.05**2))
    # Cells wholly below the bit are full hole.
    assert np.allclose(annulus[faces[:-1] >= 42.], full[faces[:-1] >= 42.])


def test_carrier_interval_matches_cell_volumes_at_faces():
    faces = np.linspace(0., 60., 13)
    full = np.full(12, np.pi*.1**2*5.)
    bore, annulus = events.string_volumes(faces, full, STRING, 42.)
    (a0, a1), (b0, b1) = events.carrier_interval((10., 35.), faces, full, STRING, 42.)
    assert a0 == pytest.approx(annulus[:2].sum()) and a1 == pytest.approx(annulus[:7].sum())
    assert b0 == pytest.approx(bore[:2].sum()) and b1 == pytest.approx(bore[:7].sum())
    # Inside a cell the bounds follow the sections, not the cell average.
    (_, a), (_, b) = events.carrier_interval((0., 33.5), faces, full, STRING, 42.)
    assert b == pytest.approx(12*.004+20*.003+1.5*.002)
    assert a == pytest.approx(np.pi*.1**2*33.5-np.pi*(12*.05**2+20*.06**2+1.5*.08**2))


def test_fixed_outer_follows_the_assembly_from_the_bit():
    md = np.array([41.9, 35., 20., 5., 43.])
    assert np.allclose(events.fixed_outer(STRING, 42., md), [.08, .08, .06, .05, 0.])


def test_trip_quantities_use_the_band_centres_and_windows():
    event = dict(id="stage-x", kind="trip_stage", start_t=0., pump_on_t=100.)
    config = events.Config(mixed=False, float_valve=False, cells=80, radial=40, cap_s=1.25)
    t = np.arange(0., 501., 50.)
    # Rows: time, phase, then per sensor (bore fluid, inside steel, mid-wall, outside steel).
    series = [(s, 0, (s, s+1., s+2., s+3.), (s, s+4., s+6., s+8.)) for s in t]
    rows = {(r["sensor"], r["band"]): r for r in events.quantities(event, series, config)}
    assert rows["bit", "centre"]["stage_peak_C"] == pytest.approx(101.)
    assert rows["bit", "high"]["stage_peak_C"] == pytest.approx(102.)
    assert rows["black_box", "centre"]["restart_peak_C"] == pytest.approx(406.)
    assert rows["black_box", "low"]["circulation_end_C"] == pytest.approx(504.)


def test_observed_order_needs_agreeing_signs():
    assert convergence.order(1., 1.5, 1.625) == pytest.approx(2.)
    assert convergence.order(1., 1.5, 1.4) is None
    assert convergence.order(1., 1., 1.) is None


def test_default_radial_grid_is_the_logarithmic_grid():
    from borethm import wall_thermal as wt
    r = wt.Grid(.108, 36., 40).build()[0]
    assert np.array_equal(r, .108*(36./.108)**np.linspace(0., 1., 40))
    fine = wt.Grid(.108, 36., 40, 2.).build()[0]
    assert fine[0] == r[0] and fine[-1] == pytest.approx(r[-1])
    assert fine[1]-fine[0] < (r[1]-r[0])/10


def test_wall_concentrated_grid_converges_on_a_short_recovery():
    from borethm.run_in_column import RadialColumn

    def recovered(n, power):
        column = RadialColumn(.108, 200., 2.8, 2.4e6, 1.5e7, radial_nodes=n, grid_power=power)
        column.circulate(3*86400., 60., 800.)
        column.shut_in(300., 4.18e6*np.pi*(.108**2-.0635**2), np.inf)
        return column.temperature_C
    assert abs(recovered(80, 2.)-recovered(40, 2.)) < .01
    assert abs(recovered(80, 1.)-recovered(40, 1.)) > abs(recovered(80, 2.)-recovered(40, 2.))


def test_bit_faces_mark_the_deepest_bit_of_each_spell_and_event_starts():
    time = np.arange(0., 100., 10.)
    bit = np.array([100., 110., 120., 120., 125., 125., 140., 150., 150., 150.])
    flow = np.array([0., 300., 300., 0., 0., 300., 300., 0., 0., 0.])
    record = (time, bit, bit+10., flow, np.full(10, 60.))
    # The event starts at 35 s: the spell before it reached 120 ft and the
    # restart spell inside its window reached 140 ft.
    assert events.bit_faces(record, [(35., 70.)]) == [120., 125., 140.]


def test_grid_merges_bit_depths_closer_than_the_tolerance():
    class Geometry:
        md_bit = 1e9

        def at(self, md):
            return {"r_wall": np.full(len(md), .1), "tvd": md}

    class Profiles:
        form = staticmethod(lambda tvd: 100.)

        def event_geometry(self, bottom):
            return Geometry()
    grid = events.Grid(Profiles(), 100., 4, [40.25224, 40.2524, 40.2524+1e-12, 60.], grade=0)
    assert np.all(np.diff(grid.faces) > 0)
    assert list(grid.faces_ft) == [0., 25., 40.2524+1e-12, 50., 60., 75., 100.]


def test_grid_grades_cells_above_fixed_faces_and_halves_them():
    def faces(cells):
        return events.Grid(GridProfiles(), 160., cells, [90.], grade=2).faces_ft
    # Spacing 40 ft: graded faces 20 and 10 ft above the bit face; the
    # uniform face at 80 ft is 10 ft from 90 ft and kept.
    assert list(faces(4)) == [0., 40., 70., 80., 90., 120., 160.]
    fine = faces(8)
    assert list(fine) == [0., 20., 40., 60., 80., 85., 90., 100., 120., 140., 160.]
    # Next to the bit face the cell halves with the cell count.
    assert 90.-fine[fine < 90.][-1] == (90.-faces(4)[faces(4) < 90.][-1])/2


class GridProfiles:
    class Geometry:
        md_bit = 1e9

        def at(self, md):
            return {"r_wall": np.full(len(md), .1), "tvd": md}
    form = staticmethod(lambda tvd: 100.)

    def event_geometry(self, bottom):
        return self.Geometry()


def test_model_pump_on_is_the_switch_nearest_the_event():
    event = dict(pump_on_t=100.)
    phases = ["static"]*3+["restart"]*2+["static"]*2+["restart"]*3
    times = [0., 50., 93., 94., 95., 96., 160., 161., 162., 163.]
    series = [(t, p) for t, p in zip(times, phases)]
    # Switches at 93 s and 160 s; the recorded flow came on 7 s early.
    assert events.model_pump_on(event, series) == 93.
    assert events.model_pump_on(dict(pump_on_t=300.), series) == 300.


def test_replayed_rows_are_written_once_and_combine_identically(tmp_path):
    rows = [dict(event="stage-01", band="high", stage_peak_C=101.23456789012345, restart_peak_C=float("nan")),
            dict(event="stage-01", band="low", stage_peak_C=1e-17, restart_peak_C=88.1)]
    calls = []

    def compute():
        calls.append(1)
        return [dict(row) for row in rows]
    key = events.replay_key("stage-01", True, False)
    assert key == "stage-01-fast-open"
    first = events.replayed_rows(tmp_path, key, compute)
    again = events.replayed_rows(tmp_path, key, compute)
    assert len(calls) == 1 and (tmp_path/f"{key}.csv").exists()
    assert not list(tmp_path.glob("*.tmp"))
    events.write_csv(tmp_path/"direct.csv", first)
    events.write_csv(tmp_path/"reread.csv", again)
    assert (tmp_path/"direct.csv").read_bytes() == (tmp_path/"reread.csv").read_bytes()
    assert events.replayed_rows(None, key, compute) == rows and len(calls) == 2
