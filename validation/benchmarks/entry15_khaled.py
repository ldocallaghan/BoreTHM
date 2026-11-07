"""Conditional comparison with Khaled et al. (2023), Table 3.

Geometry and properties follow the benchmark README. The initial rock
state assumes a prescribed 114 °C wall throughout the 3.5 h exposure.
The static capacity is that of the annulus with the drill pipe in place.
"""
import argparse
import csv
import sys

import numpy as np
from scipy.optimize import brentq

from borethm.run_in_column import RadialColumn
from borethm.wall_thermal import NU_LAMINAR


def compare(*, well_mixed=False):
    wall = 8.75 * .0254 / 2
    pipe = 5 * .0254 / 2
    capacity = np.pi * (wall**2 - pipe**2) * 1067 * 3750
    film = NU_LAMINAR * .75 / (2 * (wall - pipe))
    if well_mixed:
        film = np.inf
    column = RadialColumn(wall, 40 + .0691 * 2657, 2.31, 2800 * 930,
                          27.5 * 3600)
    column.circulate(3.5 * 3600, 114., np.inf)
    previous = 0
    for minutes, reference in zip(
        (5, 10, 15, 30, 60, 120, 240, 480, 960, 1440),
        (119, 124, 129, 141, 162, 185, 201, 213, 219, 220),
    ):
        column.shut_in((minutes - previous) * 60, capacity, film)
        yield minutes, reference, column.temperature_C
        previous = minutes


def published_start():
    """Use a circulating film inferred solely from the published pump-off state."""
    radius, pipe = 8.75*.0254/2, 5*.0254/2
    capacity = np.pi*(radius**2-pipe**2)*1067*3750
    floor = NU_LAMINAR*.75/(2*(radius-pipe))

    def circulate(film):
        column = RadialColumn(radius, 40+.0691*2657, 2.31, 2800*930,
                              27.5*3600)
        column.circulate(3.5*3600, 114., film)
        return column

    circulating_film = brentq(lambda film: circulate(film).rock[0]-153., 0., 1e4)
    slow = circulate(circulating_film)
    fast = circulate(circulating_film)
    yield 0, 114, 153, slow.temperature_C, slow.rock[0], fast.temperature_C, fast.rock[0], circulating_film
    previous = 0
    for minutes, fluid, wall in (
        (5, 119, 158), (10, 124, 162), (15, 129, 173), (30, 141, 176),
        (60, 162, 191), (120, 185, 199), (240, 201, 206), (480, 213, 215),
        (960, 219, 219), (1440, 220, 220),
    ):
        dt = (minutes-previous)*60
        slow.shut_in(dt, capacity, floor)
        fast.shut_in(dt, capacity, np.inf)
        yield minutes, fluid, wall, slow.temperature_C, slow.rock[0], fast.temperature_C, fast.rock[0], circulating_film
        previous = minutes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limits", action="store_true")
    parser.add_argument("--published-start", action="store_true")
    args = parser.parse_args()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    if args.published_start:
        writer.writerow(("shut_in_min", "reference_fluid_C", "reference_wall_C",
                         "slow_fluid_C", "slow_wall_C", "fast_fluid_C", "fast_wall_C",
                         "initial_circulating_film_W_m2_K"))
        writer.writerows(published_start())
    elif args.limits:
        writer.writerow(("shut_in_min", "reference_C", "slow_C", "fast_C"))
        writer.writerows((*slow, fast[-1]) for slow, fast in
                         zip(compare(), compare(well_mixed=True), strict=True))
    else:
        writer.writerow(("shut_in_min", "reference_C", "calculated_C"))
        writer.writerows(compare())
