"""Score entry 14 with the entry 13 scoring procedure on the frozen samples.

The geometry is entry 13's tapered_primary with the v1.8.0 tool defaults on the
tools each assembly records. Everything else runs as entry 13 did, including
the run-in transients with their Dittus-Boelter films. Bulk output stays
outside the repository.
"""
import argparse
from pathlib import Path

from borethm import physics
from forge_tools import HERE, entry13, load, with_tools

ROOT = HERE.parents[2]
scoring = load('entry13_score', HERE.parent/'entry-13/score.py')
base_geometry, base_apply = scoring.candidate_geometry, scoring.apply_geometry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--declaration', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT.resolve()):
        parser.error('Bulk score output must be outside the repository')
    scoring.DECLARATION = args.declaration
    scoring.candidate_geometry = lambda context, sample, variant: with_tools(base_geometry(context, sample, variant))
    scoring.apply_geometry = lambda g, well, variant: with_tools(base_apply(g, well, variant))
    with physics.using('v1.7.0'):
        scoring.run('tapered_primary', args.output/'entry14', args.scratch/'entry14')


if __name__ == '__main__':
    main()
