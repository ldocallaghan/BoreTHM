"""The UT Austin (Wu et al. 2025) benchmark, pinned. These hold Model 1's
results fixed so that any change shows; they don't assert agreement with Wu."""
import json

import pytest

from borethm.studies import benchmark_utaustin as b

pytestmark = pytest.mark.slow


@pytest.mark.parametrize('path, hydraulics_model, physics', [
    (b.GOLDEN, 'v1.5.0', None),             # the original calculation, in benchmark dataset 1.0
    (b.GOLDEN_V160, 'v1.6.0', 'v1.7.0'),
    (b.GOLDEN_CURRENT, 'v1.6.0', 'v1.8.0'),
])
def test_benchmark_table_is_unchanged(path, hydraulics_model, physics):
    with open(path) as fh:
        golden = json.load(fh)
    now = b.golden_rows(hydraulics_model, physics)
    assert now.keys() == golden.keys()
    for key, row in golden.items():
        for col, val in row.items():
            assert now[key][col] == pytest.approx(val, abs=0.5), (key, col)


def test_pipe_ranking_matches_wu():
    """Coldest to hottest at the bit: dual-wall, internal, external, conventional."""
    for orient in ("vertical", "horizontal"):
        t = [b.bhct(b.run(b.PIPES[n], horizontal=orient == "horizontal"))
             for n in ("dual-wall", "internal", "external", "conventional")]
        assert t == sorted(t)
