"""Circulating temperature and ECD at the bit on FORGE 58-32.

A model calculation on three drilling windows of the 58-32 thermal forecast.
For each window the circulation is solved again with the committed inputs, and
the return temperature is checked against the committed v1.9.0 prediction to
within 0.01 C. The bottom-hole pressure while drilling and the ECD at the bit
are then calculated with the same mud under three temperature treatments:

  A  the mud as reported: density at fluids.T_REF (20 C) and the plastic
     viscosity at the report's reference temperature, 48.9 C in the forecast;
  B  the static formation temperature at each depth (the PT118 profile the
     forecast uses as its geotherm);
  C  the circulating bore and annulus temperatures of the solve.

Each ECD is split into the static column and the annular friction. The
deepest window also gives the profile against depth and the change in ECD
when the annulus temperature profile is shifted by 2 and 10 C each way. As
sensitivities, cases A and C are repeated with the plastic viscosity at
T_REF, and the shifts with the plastic viscosity fixed at T_REF, so that only
density follows the temperature.

No pressure measurement is read. The thermal samples carry the mean Pason pump
pressure of each window, and the forecast's part D values are calculated from
it. Both files are read through a list of named columns that leaves those
values out, and the pump-pressure extract is not opened.

Run from the repository root:

    python -m borethm.studies.ecd_temperature
"""
import argparse
import copy
import csv
import gzip
from importlib import import_module
from pathlib import Path
import sys

import numpy as np

from borethm import fluids, model1_coupled as m1, pressure
from borethm._paths import repository_root, require_path

WELL = Path('validation/forge58-32')
OUTPUT = WELL/'ecd-temperature'
SAMPLES = WELL/'thermal/samples/conditions.csv'
PREDICTIONS = WELL/'predictions-v1.9.0/predictions.csv'
RIG = WELL/'rig_inputs_10s.csv.gz'
FLOW = 'primary'
PREDICTED = 'primary_v1.9.0_return_C'
# The only columns read from each input file.
SAMPLE_COLUMNS = ('sample_id', 'time', 'bha', 'bit_ft', 'tvd_ft', 'hole_ft', 'tfa_in2', 'flow_primary_gpm',
                  'inlet_C', 'density_ppg', 'mud_sample', 'pv_cP', 'yp', 'rheology_sample', 'input_status')
PREDICTION_COLUMNS = ('sample_id', 'primary_mass_flow_kg_s', 'primary_v1.9.0_status', PREDICTED,
                      'primary_v1.9.0_bit_C')
RIG_COLUMNS = ('time', 'hole_depth_ft', 'flow_gpm')
REPRODUCTION_C = 0.01
SHIFTS_C = (-10., -2., 2., 10.)
CASES = {'A': 'surface temperature, viscosity as reported', 'B': 'static formation temperature',
         'C': 'circulating temperature'}
# Sensitivity cases: the plastic viscosity at T_REF (20 C).
A20 = 'A with viscosity at 20 C'
C20 = 'C with viscosity at 20 C'


def columns(path, names, opener=open):
    """Rows of a CSV file with only the named columns kept."""
    with opener(path, 'rt', encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = set(names) - set(reader.fieldnames)
        if missing:
            raise ValueError(f'{path}: missing columns {sorted(missing)}')
        return [{name: row[name] for name in names} for row in reader]


class FixedViscosity(fluids.Mud):
    """The mud with its density at the local temperature and pressure and its
    plastic viscosity at the temperature viscosity_T and the local pressure."""

    viscosity_T = fluids.T_REF

    def props(self, T, P):
        rho, cp, _, k = super().props(T, P)
        T_mu, P = np.broadcast_arrays(np.full(np.shape(T), self.viscosity_T), np.asarray(P, float))
        return rho, cp, super().props(T_mu, P)[2], k


def fixed_viscosity(fluid, T=fluids.T_REF):
    copied = copy.copy(fluid)
    copied.__class__ = FixedViscosity
    copied.viscosity_T = float(T)
    return copied


def column_mean_T(case):
    """Mean temperature [C] of the annulus column over true vertical depth."""
    return float(np.trapezoid(case['Tu'], case['tvd'])/case['tvd'][-1])


def iapws_column(rho_surface, tvd, P_abs):
    """Hand check: the static column [Pa] of the barite mud at T_REF, with
    water's density from IAPWS-97 at each pressure and the mud's barite mass
    fraction, by the trapezium rule."""
    from iapws import IAPWS97
    T_K = fluids.T_REF+273.15
    rho_w0 = IAPWS97(T=T_K, P=fluids.P_ATM/1e6).rho
    x = (rho_surface-rho_w0)/(fluids.BARITE_RHO-rho_w0)*fluids.BARITE_RHO/rho_surface
    rho = np.array([1./(x/fluids.BARITE_RHO+(1.-x)/IAPWS97(T=T_K, P=p/1e6).rho) for p in P_abs])
    return float(np.sum(0.5*(rho[1:]+rho[:-1])*m1.G_GRAV*np.diff(tvd))), float(rho_w0)


def thermal_modules(root):
    """The forecast's own setup code, with its state built from inputs only."""
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    common = import_module('validation.forge58-32.thermal.common')
    forecast = import_module('validation.forge58-32.thermal.predict_thermal')
    rig = columns(root/RIG, RIG_COLUMNS, gzip.open)
    history = dict(time=np.array([np.datetime64(r['time']) for r in rig]),
                   flow_gpm=np.array([common.number(r['flow_gpm']) for r in rig]),
                   hole_depth_ft=np.array([common.number(r['hole_depth_ft']) for r in rig]))
    # predict_thermal.initialize() also loads the pump pressure; Clock uses only
    # time, flow and hole depth, so the state is built here from those.
    forecast.STATE = dict(clock=common.Clock(history), survey=common.survey(), form=common.formation())
    return common, forecast


def choose_windows(samples, predictions):
    """The deepest scored window and those nearest a half and a quarter of its
    bit depth; equal distances take the earlier sample."""
    predicted = {r['sample_id']: r for r in predictions if r['primary_v1.9.0_status'] == 'converged'}
    scored = [r for r in samples if r['input_status'] == 'complete' and r['sample_id'] in predicted]
    depth = lambda r: float(r['bit_ft'])
    deepest = max(scored, key=lambda r: (depth(r), -scored.index(r)))
    nearest = lambda target: min(scored, key=lambda r: (abs(depth(r)-target), scored.index(r)))
    chosen = [('shallow', nearest(depth(deepest)/4)), ('mid-depth', nearest(depth(deepest)/2)),
              ('deepest', deepest)]
    return [(label, row, predicted[row['sample_id']]) for label, row in chosen], len(scored)


def solve_window(common, forecast, row):
    fluid = forecast.fluid_for(row)
    exposure, kw, flags = forecast.setup(row['bha'], common.number(row['bit_ft']), common.number(row['hole_ft']),
                                         row['time'], common.number(row['flow_primary_gpm']),
                                         common.number(row['inlet_C']), common.number(row['tfa_in2']), fluid)
    result = forecast.solve(exposure, kw, None)
    if not result['success']:
        raise SystemExit(f"{row['sample_id']}: the circulation solve failed")
    return result, kw, flags


def budget(result, kw, Tu, Td, fluid):
    """Bottom-hole pressure while drilling at the bit, with the column and the
    annulus at the given temperatures [C] on the solve's depth grid."""
    geometry = result['geometry']
    tvd = geometry.survey.tvd(result['z'])
    run = dict(result, Tu=np.asarray(Tu, float), Td=np.asarray(Td, float))
    hyd = m1.hydraulics(kw['m_dot'], geometry, run, tfa=kw['tfa'], fluid=fluid)
    P_surface = pressure.backpressure(float(run['Tu'][0]))
    bit_tvd = float(geometry.survey.tvd(geometry.md_bit))
    bhp = pressure.bottomhole_pressure('drilling', bit_tvd, temperatures=(tvd, run['Tu']), fluid=fluid,
                                       run=dict(hyd=hyd), P_surface=P_surface)
    # bottomhole_pressure reads the annulus friction at its depth argument,
    # which is a true vertical depth; the loss to the bit is taken at the
    # bit's measured depth and the difference is kept.
    friction = pressure.annulus_friction(dict(hyd=hyd), geometry.md_bit)
    per_sg = pressure.sg_per_pa(bit_tvd)
    return dict(bit_md_m=geometry.md_bit, bit_tvd_m=bit_tvd, P_surface=P_surface,
                hydrostatic_Pa=bhp['P_static']-P_surface, friction_Pa=friction,
                friction_at_tvd_Pa=bhp['friction'], bhp_Pa=bhp['P_static']+friction,
                hydrostatic_SG=(bhp['P_static']-P_surface)/per_sg, friction_SG=friction/per_sg,
                ECD_SG=(bhp['P_static']-P_surface+friction)/per_sg, hyd=hyd, tvd=tvd, Tu=run['Tu'])


def profile(result, case):
    """ECD [SG] against true vertical depth from a budget()."""
    tvd = case['tvd']
    static = pressure.column(tvd, case['Tu'], result['fluid'], case['P_surface']) - case['P_surface']
    md = np.asarray(result['z'], float)
    friction = np.interp(md, case['hyd']['annulus_profile']['md'], case['hyd']['annulus_profile']['dp'])
    with np.errstate(divide='ignore', invalid='ignore'):
        ecd = (static+friction)/pressure.sg_per_pa(tvd)
    return tvd, ecd


def units(common, sg_or_pa, tvd=None):
    """SG, ppg and psi of an ECD part given in SG."""
    return dict(SG=sg_or_pa, ppg=sg_or_pa*1000./common.PPG, psi=sg_or_pa*pressure.sg_per_pa(tvd)/common.PSI)


def case_row(common, label, sample, name, b):
    out = dict(window=label, sample_id=sample, case=name, bit_md_ft=b['bit_md_m']/common.FT,
               bit_tvd_ft=b['bit_tvd_m']/common.FT)
    for part, key in (('ECD', 'ECD_SG'), ('hydrostatic', 'hydrostatic_SG'), ('friction', 'friction_SG')):
        for unit, value in units(common, b[key], b['bit_tvd_m']).items():
            out[f'{part}_{unit}'] = value
    out['bhp_psi'] = b['bhp_Pa']/common.PSI
    out['friction_at_tvd_psi'] = b['friction_at_tvd_Pa']/common.PSI
    out['annulus_regimes'] = ';'.join(sorted({p['annulus_regime'] for p in b['hyd']['pieces']}))
    return out


def difference_row(common, label, sample, name, high, low):
    out = dict(window=label, sample_id=sample, difference=name)
    for part, key in (('ECD', 'ECD_SG'), ('hydrostatic', 'hydrostatic_SG'), ('friction', 'friction_SG')):
        for unit, value in units(common, high[key]-low[key], high['bit_tvd_m']).items():
            out[f'{part}_{unit}'] = value
    return out


def write(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: (f'{v:.6g}' if isinstance(v, float) else v) for k, v in row.items()})


def figure(path, deepest, cases):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colours = {'A': '#2a78d6', 'B': '#eb6834', 'C': '#1baf7a'}
    styles = {'A': '-', 'B': '--', 'C': '-'}
    fig, (left, right) = plt.subplots(1, 2, figsize=(8.0, 4.6), sharey=True)
    for name, (tvd_ft, ecd, T) in cases.items():
        keep = tvd_ft >= 300.
        left.plot(ecd[keep], tvd_ft[keep], styles[name], color=colours[name], lw=2, label=f'{name}: {CASES[name]}')
        right.plot(T, tvd_ft, styles[name], color=colours[name], lw=2, label=f'{name}: {CASES[name]}')
    left.set_xlabel('ECD (SG)')
    left.set_ylabel('True vertical depth (ft)')
    right.set_xlabel('Fluid temperature (°C)')
    left.invert_yaxis()
    for ax in (left, right):
        ax.grid(alpha=.25, lw=.6)
        ax.set_axisbelow(True)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
    handles, labels = right.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8.5, loc='lower center', ncol=3)
    fig.suptitle(f"FORGE 58-32, window {deepest['sample_id']}, bit at {float(deepest['bit_ft']):,.0f} ft MD",
                 fontsize=11)
    fig.tight_layout(rect=(0, .06, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=None, help='repository root (default: this checkout)')
    args = parser.parse_args(argv)
    root = require_path(args.root or repository_root(), 'The 58-32 ECD study')
    common, forecast = thermal_modules(root)
    samples = columns(root/SAMPLES, SAMPLE_COLUMNS)
    predictions = columns(root/PREDICTIONS, PREDICTION_COLUMNS)
    windows, n_scored = choose_windows(samples, predictions)
    out = root/OUTPUT
    out.mkdir(parents=True, exist_ok=True)

    window_rows, case_rows, difference_rows, sensitivity_rows = [], [], [], []
    for label, row, predicted in windows:
        sample = row['sample_id']
        result, kw, flags = solve_window(common, forecast, row)
        result['fluid'] = kw['fluid']
        committed = float(predicted[PREDICTED])
        delta = result['T_return_surface']-committed
        window_rows.append(dict(window=label, sample_id=sample, time=row['time'], bha=row['bha'],
                                bit_md_ft=float(row['bit_ft']), bit_tvd_ft=float(row['tvd_ft']),
                                hole_ft=float(row['hole_ft']), flow_primary_gpm=float(row['flow_primary_gpm']),
                                mass_flow_kg_s=kw['m_dot'], inlet_C=float(row['inlet_C']),
                                density_ppg=float(row['density_ppg']), pv_cP=common.number(row['pv_cP']),
                                yp_lbf_100ft2=common.number(row['yp']), mud_sample=row['mud_sample'],
                                rheology_sample=row['rheology_sample'], pv_reference_C=common.PV_REF_T,
                                tfa_in2=float(row['tfa_in2']), components_as_drill_pipe=';'.join(flags),
                                return_committed_C=committed, return_recalculated_C=result['T_return_surface'],
                                return_difference_C=delta, bit_recalculated_C=result['T_bottom_delivered'],
                                annulus_at_bit_C=float(result['Tu'][-1]), scored_windows=n_scored))
        if abs(delta) > REPRODUCTION_C:
            write(out/'windows.csv', window_rows)
            raise SystemExit(f'{sample}: return {result["T_return_surface"]:.4f} C against the committed '
                             f'{committed:.4f} C; the difference exceeds {REPRODUCTION_C} C')
        fluid = kw['fluid']
        z_tvd = result['geometry'].survey.tvd(result['z'])
        form_T = forecast.STATE['form'](z_tvd)
        T_ref = np.full_like(z_tvd, fluids.T_REF)
        b = {A20: budget(result, kw, T_ref, T_ref, fluid),
             'B': budget(result, kw, form_T, form_T, fluid),
             'C': budget(result, kw, result['Tu'], result['Td'], fluid)}
        b[C20] = budget(result, kw, result['Tu'], result['Td'], fixed_viscosity(fluid))
        b['A'] = budget(result, kw, T_ref, T_ref, fixed_viscosity(fluid, common.PV_REF_T))
        for name in ('A', 'B', 'C', A20, C20):
            case_rows.append(dict(case_row(common, label, sample, name, b[name]),
                                  column_mean_T_C=column_mean_T(b[name])))
        for name, high, low in (('C - A', 'C', 'A'), ('C - B', 'C', 'B'),
                                (f'Sensitivity: C - {A20}', 'C', A20),
                                (f'Sensitivity: {C20} - {A20}, density only', C20, A20),
                                (f'Sensitivity: C - {C20}, viscosity only', 'C', C20)):
            difference_rows.append(difference_row(common, label, sample, name, b[high], b[low]))
        if label == 'deepest':
            for shift in SHIFTS_C:
                for name, fluid_used in (('mud', fluid), ('viscosity at T_REF', fixed_viscosity(fluid))):
                    base = b['C'] if name == 'mud' else b[C20]
                    shifted = budget(result, kw, result['Tu']+shift, result['Td'], fluid_used)
                    sensitivity_rows.append(dict(sample_id=sample, shift_C=shift, viscosity=(
                        'follows temperature' if name == 'mud' else 'fixed at T_REF'),
                        **{k: v for k, v in difference_row(common, label, sample, '', shifted, base).items()
                           if k not in ('window', 'sample_id', 'difference')}))
            curves = {}
            for name in CASES:
                tvd, ecd = profile(result, b[name])
                curves[name] = (tvd/common.FT, ecd, b[name]['Tu'])
            write(out/'profile-deepest.csv', [dict(md_ft=z/common.FT, tvd_ft=t, **{
                f'{n}_T_C': curves[n][2][i] for n in CASES}, **{f'{n}_ECD_SG': curves[n][1][i] for n in CASES})
                for i, (z, t) in enumerate(zip(result['z'], curves['A'][0]))])
            figure(out/'ecd-profile.png', row, curves)
            # Hand check of case A: rho g TVD from the reported mud weight, and
            # the same column with water's compressibility from IAPWS-97.
            rho = float(row['density_ppg'])*common.PPG
            hand = rho*m1.G_GRAV*b['A']['bit_tvd_m']
            model = b['A']['hydrostatic_Pa']
            P_abs = fluids.P_ATM+pressure.column(z_tvd, T_ref, fluid)
            compressed, rho_w0 = iapws_column(rho, z_tvd, P_abs)
            check = dict(sample_id=sample, density_ppg=float(row['density_ppg']), rho_kg_m3=rho,
                         g_m_s2=m1.G_GRAV, bit_tvd_ft=b['A']['bit_tvd_m']/common.FT,
                         model_psi=model/common.PSI, rho_g_tvd_psi=hand/common.PSI,
                         rho_g_tvd_difference_percent=100*(model/hand-1),
                         iapws97_column_psi=compressed/common.PSI,
                         iapws97_difference_percent=100*(model/compressed-1),
                         water_rho_T_REF_kg_m3=rho_w0)
            write(out/'hand-check.csv', [check])
        print(f'{label}: {sample} reproduced to {delta:+.5f} C', flush=True)
    write(out/'windows.csv', window_rows)
    write(out/'cases.csv', case_rows)
    write(out/'differences.csv', difference_rows)
    write(out/'sensitivity.csv', sensitivity_rows)


if __name__ == '__main__':
    main()
