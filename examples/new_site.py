"""
The worked example for a new site: build the site from the template,
validate it, evaluate it, and write the result as JSON.

    python examples/new_site.py              # validate, and check against Soultz
    python examples/new_site.py --evaluate   # also evaluate (several minutes)
    python examples/new_site.py --evaluate --json soultz.json

The template holds Soultz's inputs, so the site it builds is Soultz's, and
with --evaluate its row of the site table is compared with the pinned one
(tests/golden/v133_site_table.json).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from borethm import comparative_sites as cs        # noqa: E402
from borethm import site_evaluation as se          # noqa: E402
from site_template import make_site   # noqa: E402

GOLDEN = os.path.join(HERE, "..", "tests", "golden", "v134_site_table.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    ap.add_argument("--evaluate", action="store_true", help="evaluate the site")
    ap.add_argument("--json", help="write the result to this JSON file")
    a = ap.parse_args()

    site = make_site()
    try:
        for w in se.validate_site(site):
            print("warning:", w)
    except ValueError as error:
        ap.error(str(error))
    print(f"{site.name}: inputs valid; {site.tier}")
    print("same inputs as the repository's Soultz:", site == se.SOULTZ)
    if not (a.evaluate or a.json):
        return
    o = se.evaluate(site)
    se.report(o)
    if a.json:
        se.export_result(o, a.json)
        print(f"result written to {a.json}")
    if site == se.SOULTZ and os.path.exists(GOLDEN):
        from borethm.studies.release_v134 import reference_row, assert_reviewed
        pinned = json.load(open(GOLDEN))['sites']['soultz']
        assert_reviewed(reference_row(se.result_dict(o)), pinned)
        print("the reviewed v1.3.4 Soultz row reproduced: True")


if __name__ == "__main__":
    main()
