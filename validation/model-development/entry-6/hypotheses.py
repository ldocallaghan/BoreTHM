"""The three declared downhole yield-stress hypotheses of entry 6.

Each attaches a Herschel-Bulkley rheology (borethm.fluids.HerschelBulkley)
to a sample's mud and selects annulus_model 'herschel-bulkley'. The mud
report gives PV and YP; the low-shear yield stress tau_0 comes from the
10-s gel in gel_inputs.csv (build_gel.py).

  no-yield      tau_0 = 0: the power-law fit to the same two readings, the
                lowest yield stress the reports allow
  gel           tau_0 = the 10-s gel at every temperature
  gel-rising    tau_0 = the 10-s gel up to T* = 330 K, rising above it as
                exp(E_H (1/T* - 1/T)) with E_H = 2.9e3 K, the values read
                from Alderman et al. (1988, SPE 18035, fig. 8) for their
                unweighted water-based mud
"""
import csv
from pathlib import Path

from borethm import fluids
from borethm import model1_coupled as m1

HERE = Path(__file__).resolve().parent
ALDERMAN_RISE = (330.0, 2.9e3)   # T* [K], E_H [K]; Alderman et al. (1988) fig. 8
HYPOTHESES = {'no-yield': dict(gel_scale=0.0, rise=None),
              'gel': dict(gel_scale=1.0, rise=None),
              'gel-rising': dict(gel_scale=1.0, rise=ALDERMAN_RISE)}


def gels():
    with open(HERE/'gel_inputs.csv', newline='', encoding='utf-8') as f:
        return {(r['well'], r['run']): float(r['gel_10s_lbf_100ft2']) for r in csv.DictReader(f)}


GELS = gels()


def rheology(sample, fluid, yp, name):
    """The hypothesis's Herschel-Bulkley rheology for sample's mud. fluid is
    the fluids.Mud built from the report (its reference PV, or water's when
    the report has none); yp its yield point [lbf/100 ft2]."""
    spec = HYPOTHESES[name]
    gel = GELS[sample['well'], sample['run']]
    return fluids.HerschelBulkley.from_report(fluid.pv_ref*1e3, yp, spec['gel_scale']*gel, spec['rise'])


def solve_continued(frozen, exposure, breaks=(), **kw):
    """Solve the candidate (annulus_model 'herschel-bulkley') starting from
    the converged working calculation. frozen is the working calculation's
    m1.solve_seeded; kw are its keyword arguments, with the candidate's
    fluid (carrying its rheology). A collocation solve converges to the same
    answer from different starting profiles (solve_seeded), and the
    candidate's uniform-exposure seeds need very fine meshes, so the
    working solution is the starting profile; if the candidate does not
    converge from it, the usual seeds are tried."""
    rheology = kw['fluid'].rheology
    kw['fluid'].rheology = None
    try:
        working = frozen(exposure, breaks, **kw)
    finally:
        kw['fluid'].rheology = rheology
    if working['success']:
        result = m1.solve(**kw, exposure=exposure, breaks=breaks, init=working, annulus_model='herschel-bulkley')
        if result['success']:
            result['seed'] = working
            return result
    return frozen(exposure, breaks, annulus_model='herschel-bulkley', **kw)
