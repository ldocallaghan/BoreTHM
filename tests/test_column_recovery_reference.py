"""Independent method-of-lines reference for cylindrical recovery."""
import numpy as np
import pytest
from scipy.integrate import solve_ivp
from scipy.sparse import diags

from borethm.run_in_column import RadialColumn
from validation.benchmarks.entry15_recovery import DIFFUSIVITY, HOURS, K_ROCK, R_WALL


def reference(circulation_hours, *, filled=False, cells=1000):
    """Integrate radial heat diffusion with cell-centred fluxes and BDF."""
    radius = R_WALL
    alpha = DIFFUSIVITY
    recovery_times = np.array(HOURS) * 3600.
    end = radius + 12*np.sqrt(alpha*(circulation_hours*3600 + recovery_times[-1]))
    outer_faces = np.geomspace(radius, end, cells + 1)

    def evolve(faces, initial, times, inner_fixed):
        centres = np.sqrt((faces[1:]**2 + faces[:-1]**2)/2)
        volumes = (faces[1:]**2 - faces[:-1]**2)/2
        conductance = alpha*faces[1:-1]/np.diff(centres)
        lower = conductance/volumes[1:]
        upper = conductance/volumes[:-1]
        diagonal = -np.r_[0., lower] - np.r_[upper, 0.]
        if inner_fixed:
            diagonal[0] -= alpha*faces[0]/(centres[0]-faces[0])/volumes[0]
        outer = alpha*faces[-1]/(faces[-1]-centres[-1])/volumes[-1]
        diagonal[-1] -= outer
        matrix = diags((lower, diagonal, upper), (-1, 0, 1), format="csc")
        source = np.zeros_like(initial)
        source[-1] = outer
        result = solve_ivp(lambda _, y: matrix @ y + source, (0., times[-1]), initial,
                           method="BDF", jac=matrix, t_eval=times, atol=1e-9, rtol=1e-7)
        assert result.success, result.message
        return result.y

    cooled = evolve(outer_faces, np.ones(cells), [circulation_hours*3600.], True)[:, -1]
    if filled:
        inner_faces = np.linspace(0., radius, 401)
        faces = np.r_[inner_faces[:-1], outer_faces]
        profile = evolve(faces, np.r_[np.zeros(400), cooled], recovery_times, False)
        centres = np.sqrt((faces[1:]**2 + faces[:-1]**2)/2)
        weight = (radius-centres[399])/(centres[400]-centres[399])
        return (1-weight)*profile[399] + weight*profile[400]
    return evolve(outer_faces, cooled, recovery_times, False)[0]


@pytest.mark.parametrize("circulation", [36, 756])
def test_column_matches_independent_wall_recovery(circulation):
    column = RadialColumn(R_WALL, 1., K_ROCK, K_ROCK/DIFFUSIVITY,
                          (circulation + HOURS[-1])*3600., radial_nodes=400)
    column.circulate(circulation*3600., 0., np.inf)
    calculated = [column.shut_in(interval*3600., 0., 0.).T_wall[-1]
                  for interval in np.diff((0, *HOURS))]
    np.testing.assert_allclose(calculated, reference(circulation), rtol=0., atol=.005)
