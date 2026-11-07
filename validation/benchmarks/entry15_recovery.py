"""Compare a radial column with Kutasov and Eppelbaum (2014), Well #4.

Source: https://pangea.stanford.edu/ERE/pdf/IGAstandard/SGW/2014/Kutasov.pdf
See the benchmark README for the benchmark limitations.
"""
import csv
import sys

import numpy as np

from borethm.run_in_column import RadialColumn
from borethm.wall_thermal import NU_LAMINAR

HOURS = (2, 4, 6, 8, 10, 14, 18, 20, 30, 40)
PUBLISHED = {
    36: (.202, .338, .424, .485, .532, .600, .649, .669, .740, .784),
    756: (.119, .200, .253, .292, .323, .370, .406, .421, .479, .520),
}
R_WALL = 8.5 * .0254 / 2
R_LINER = 5.5 * .0254 / 2
K_ROCK = 1.46 * 4184 / 3600
DIFFUSIVITY = .0041 / 3600
WATER_CAPACITY = 4.18e6
WATER_CONDUCTIVITY = .60


def compare(nodes, liner, multiplier):
    """Use a prescribed cold wall during circulation and a static liquid node."""
    inner = R_LINER if liner else 0.
    capacity = WATER_CAPACITY * np.pi * (R_WALL**2 - inner**2)
    film = multiplier * NU_LAMINAR * WATER_CONDUCTIVITY / (2 * (R_WALL - inner))
    for circulation_hours, published in PUBLISHED.items():
        column = RadialColumn(R_WALL, 1., K_ROCK, K_ROCK / DIFFUSIVITY,
                              (circulation_hours + HOURS[-1]) * 3600, radial_nodes=nodes)
        column.circulate(circulation_hours * 3600, 0., np.inf)
        previous = 0
        for hours, reference in zip(HOURS, published):
            column.shut_in((hours - previous) * 3600, capacity, film)
            fraction = column.temperature_C
            yield (nodes, liner, multiplier, circulation_hours, hours, reference,
                   fraction, fraction - reference)
            previous = hours


if __name__ == "__main__":
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("radial_nodes", "liner", "film_multiplier", "circulation_h",
                     "shut_in_h", "reference_fraction", "calculated_fraction",
                     "error_fraction"))
    for nodes in (200, 400):
        for liner, multiplier in ((False, 1.), (True, 1.), (False, 10000.), (True, 10000.)):
            writer.writerows(compare(nodes, liner, multiplier))
