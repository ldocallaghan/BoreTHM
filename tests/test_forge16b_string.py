"""The 16B string covers exactly the depth in the hole, including trips."""
import pytest

from borethm.studies import validate_forge16b as v


@pytest.mark.parametrize('run', sorted(v.RUNS))
@pytest.mark.parametrize('bit_ft', [150.0, 700.0, 2000.0, 9000.0])
def test_string_length_equals_bit_depth(run, bit_ft):
    segments = v.string(run, bit_ft, 4.92)
    assert all(s.length > 0 for s in segments)
    assert sum(s.length for s in segments) == pytest.approx(bit_ft*v.FT, rel=1e-12)


@pytest.mark.parametrize('run', sorted(v.RUNS))
def test_shallow_bit_keeps_the_lowest_components(run):
    deep = v.string(run, 9000.0, 4.92)
    shallow = v.string(run, 100.0, 4.92)
    assert len(shallow) == 1 and shallow[0].pipe == deep[-1].pipe
