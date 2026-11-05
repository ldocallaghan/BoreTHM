"""Check that the package's default route gives the harness calculation.

The score enters each tool default as an explicit figure and runs the frozen
calculation under the v1.7.0 preset. This check solves samples of each well a
second time under the v1.8.0 defaults, with the joint treatment, friction,
annulus model and rheology left to the package and the tools named by class and
collar size. Targets are not read.
"""
import argparse
from dataclasses import replace

from borethm import hydraulic_losses as hl
from borethm import physics, well_geometry as wg
from forge_tools import HERE, OPTIONS, classes, entry13, with_tools
from predict import write


def defaults_only(g):
    """The tapered_primary geometry, with its settings removed so that the preset supplies them."""
    string = []
    for segment in g.string:
        pipe, joint = segment.pipe, segment.pipe.hydraulic_joint
        if joint is not None and joint.transition == 'tapered':
            pipe = replace(pipe, hydraulic_joint=replace(joint, transition=None, taper_angle_deg=None, kind='ordinary'))
        elif joint is not None and joint.transition == 'abrupt':
            pipe = replace(pipe, hydraulic_joint=replace(joint, transition=None, taper_angle_deg=None, kind='insulated' if pipe.name.startswith('IDP,') else 'heavy-weight'))
        trial = segment.pipe.name == OPTIONS['trial_compact_bha']['name']
        collar = OPTIONS['trial_compact_bha']['collar_in'] if trial else 2*segment.pipe.r_out/.0254
        tools = tuple(hl.DownholeTool(c, collar) for c in classes(segment.pipe.name))
        string.append(replace(segment, pipe=pipe, tools=tools))
    return wg.WellGeometry(string, g.hole, g.survey)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=HERE/'predictions')
    parser.add_argument('--samples', type=int, default=4)
    args = parser.parse_args()
    with physics.using('v1.7.0'):
        calc = entry13.diagnosis.Calculation()
    chosen, seen = [], set()
    for sample in calc.plan['samples']:
        if (sample['well'], sample['run']) not in seen:
            seen.add((sample['well'], sample['run']))
            chosen.append(sample)
    chosen = chosen[:: max(1, len(chosen)//args.samples)]
    base = entry13.geometry
    rows = []
    for sample in chosen:
        entry13.geometry = lambda c, s, v: with_tools(base(c, s, 'tapered_primary'))
        with physics.using('v1.7.0'):
            harness = entry13.solve(calc, sample, 'tapered_primary')
        entry13.geometry = lambda c, s, v: defaults_only(base(c, s, 'tapered_primary'))
        with physics.using('v1.8.0'):
            package = entry13.solve(calc, sample, 'tapered_primary')
        row = dict(well=sample['well'], assembly=sample['run'], sample_id=sample['id'])
        for key in ('spp_psi', 'bit_C', 'return_C', 'model_hydraulic_kW'):
            row[key+'_harness'], row[key+'_package'], row[key+'_difference'] = harness[key], package[key], package[key]-harness[key]
        rows.append(row)
        print(row, flush=True)
    write(args.output/'default-route-check.csv', rows)


if __name__ == '__main__':
    main()
