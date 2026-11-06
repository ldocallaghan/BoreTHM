"""The five built-in sites at the v1.8.0 default physics.

The rows are those of the v1.6.0 table, so the two can be compared directly.
Regenerate with tests/make_golden_v180.py after a deliberate model change."""
import json
from pathlib import Path

import pytest

from borethm import site_evaluation as se
from borethm.studies import release_v134 as release

GOLDEN = Path(__file__).resolve().parent / 'golden' / 'v180_site_table.json'
pytestmark = pytest.mark.default_physics


@pytest.mark.slow
@pytest.mark.parametrize('key', release.SITES)
def test_defaults_match_the_v180_golden(key, evaluated):
    pin = json.loads(GOLDEN.read_text())['sites'][key]
    data = se.result_dict(evaluated(se.find_site(key), circulation='v1.3.4', physics='v1.8.0'))
    release.assert_reviewed(release.reference_row(data), pin)
