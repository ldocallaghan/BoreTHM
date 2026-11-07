"""Compare the insulated rock wall with Kutasov and Eppelbaum, Table 1."""
import numpy as np

from borethm import wall_thermal
from validation.benchmarks.entry15_recovery import DIFFUSIVITY, HOURS, K_ROCK, PUBLISHED, R_WALL
from validation.benchmarks.run_circulation import write_csv
from pathlib import Path


def compare():
    for nodes in (200, 400):
        for circulation, published in PUBLISHED.items():
            states = [wall_thermal.State("fixed", circulation * 3600, T_wall=0.)]
            states.extend(wall_thermal.State("static", duration * 3600, C=0.)
                          for duration in np.diff((0, *HOURS)))
            result = wall_thermal.run(states, 1., R_WALL, K_ROCK,
                                      K_ROCK / DIFFUSIVITY, n=nodes)
            for hours, ref, (_, wall, _) in zip(HOURS, published, result.ends[1:]):
                yield dict(nodes=nodes, circulation_h=circulation, shut_in_h=hours,
                           reference_fraction=ref, wall_fraction=wall,
                           error_fraction=wall-ref, passed=abs(wall-ref) <= .05)


if __name__ == "__main__":
    write_csv(Path(__file__).with_name("entry15-wall.csv"), compare())
