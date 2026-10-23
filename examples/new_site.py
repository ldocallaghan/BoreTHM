"""
The worked example for a new site: build the site from the template,
validate it, evaluate it, and write the result as JSON.

    python examples/new_site.py              # validate, and check against Soultz
    python examples/new_site.py --evaluate   # also evaluate (several minutes)
    python examples/new_site.py --evaluate --json soultz.json

The packaged TOML template contains Soultz's inputs. With --evaluate,
its row of the site table is compared with the reviewed reference
(tests/golden/v134_site_table.json).
"""
import argparse
import json
import os
import sys
from importlib.resources import as_file, files

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tests'))

from borethm import site_evaluation as se          # noqa: E402
from borethm import load_site                    # noqa: E402
from site_helpers import assert_sites_equal      # noqa: E402

GOLDEN = os.path.join(HERE, "..", "tests", "golden", "v134_site_table.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("--evaluate", action="store_true", help="evaluate the site")
    ap.add_argument("--json", help="write the result to this JSON file")
    a = ap.parse_args()

    template = files('borethm').joinpath('templates/site_template.toml')
    with as_file(template) as path:
        site = load_site(path)
    try:
        for w in se.validate_site(site):
            print("warning:", w)
    except ValueError as error:
        ap.error(str(error))
    print(f"{site.name}: inputs valid; {site.tier}")
    assert_sites_equal(site, se.SOULTZ, allow_extra_basis=True)
    print("same inputs as the repository's Soultz: True")
    if not (a.evaluate or a.json):
        return
    o = se.evaluate(site)
    se.report(o)
    if a.json:
        se.export_result(o, a.json)
        print(f"result written to {a.json}")
    if os.path.exists(GOLDEN):
        from borethm.studies.release_v134 import reference_row, assert_reviewed
        with open(GOLDEN, encoding='utf-8') as stream:
            pinned = json.load(stream)['sites']['soultz']
        assert_reviewed(reference_row(se.result_dict(o)), pinned)
        print("the reviewed v1.3.4 Soultz row reproduced: True")


if __name__ == "__main__":
    main()
