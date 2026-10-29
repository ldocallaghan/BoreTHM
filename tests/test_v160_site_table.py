"""The five built-in sites in the default mode, with the v1.6.0 calculation.

The rows are those of the v1.3.4 release table, so the two can be compared
directly. Regenerate with tests/make_golden_v160.py after a deliberate
model change."""
import json
from pathlib import Path

import pytest

from borethm import site_evaluation as se
from borethm.studies import release_v134 as release

GOLDEN = Path(__file__).resolve().parent / 'golden' / 'v160_site_table.json'


@pytest.mark.slow
@pytest.mark.parametrize('key', release.SITES)
def test_current_mode_matches_the_v160_golden(key, evaluated):
    pin = json.loads(GOLDEN.read_text())['sites'][key]
    data = se.result_dict(evaluated(se.find_site(key), circulation='v1.3.4'))
    release.assert_reviewed(release.reference_row(data), pin)
