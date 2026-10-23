"""Retained evaluations for report and export checks without physical solves."""
import json
from pathlib import Path
from types import SimpleNamespace

from borethm import site_evaluation as se

ROOT = Path(__file__).resolve().parents[1]


def _restore(value):
    if isinstance(value, dict):
        return {key: _restore(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore(item) for item in value]
    return float(value) if isinstance(value, str) and value in ('inf', '-inf') else value


def retained(key):
    return json.loads((ROOT / f'results/v1.3.4/checkpoint-1/{key}.json').read_text(encoding='utf-8'))


def report_input(key):
    """Adapt a saved export for the original report and export entry points.

    The export omits creep and wall-temperature values. Zero placeholders
    allow comparison of the unchanged report layout for those lines; no
    scientific claim is made about those placeholders. The reading does
    not inspect them. No model is run.
    """
    data = _restore(retained(key))
    site = se.find_site(key)
    p = data['programme']
    profile = site.stress_cases[0]
    z = data['z_m']
    fluid = p['fluid']
    if fluid is not None:
        fluid = SimpleNamespace(rho_surface=fluid['rho_surface'], sg=fluid['sg'],
                                yield_point=fluid['yield_point_Pa'], mu_ratio=fluid['pv_ratio_to_water'],
                                x=p.get('barite_mass_fraction', 0.))
    trip_rho = p.get('trip_simulated_rho_surface')
    trip = None if trip_rho is None else SimpleNamespace(
        rho_surface=trip_rho, x=p.get('trip_barite_mass_fraction', 0.))
    return dict(site=site, z=z, T_rock=data['T_rock_C'], circulation=data['evaluation'],
                Sv=profile.Sv(z), SHmax=profile.SHmax(z), Shmin=profile.Shmin(z), Pp=float(profile.Pp(z)),
                T_wall=0., creep_hot=0., creep_cold=0.,
                circ=dict(pipe=SimpleNamespace(name=p['pipe']), m_dot=p['flow'], mass_flow=p['mass_flow_kg_s'],
                          bhct=p['bit_C'], T_return=p['return_C'], backpressure=p['backpressure_Pa'],
                          ecd_SG=p['ecd_SG'], hyd=dict(spp=p['spp_Pa'], v_ann_min=p['v_ann_min']),
                          conflict=p['conflict']),
                fluid=fluid, trip_fluid=trip, apply_trip_fluid='trip_simulated_rho_surface' in p,
                fluid_passes=p['fluid_passes'], fluid_converged=p['fluid_converged'], rop_passes=p['rop_passes'],
                m1=dict(T_return_surface=p['return_C']), drill=dict(ROP=p['rop_m_h'] / 3600.),
                cycle={**data['cycle'], 'per_case': data['cycle']['cases']},
                cycle_sensitivity=data.get('sensitivities', {}), trip_profile=data.get('trip_profile'),
                windows=data['windows'], tools=data['tools'], components=data['components'], status=data['status'],
                input_warnings=data.get('input_warnings', []))
