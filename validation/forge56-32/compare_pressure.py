"""FORGE 56-32 standpipe-pressure comparison, under the registered protocol.

Subcommands:
  predict  model predictions for the windows with complete inputs; reads no target
  targets  standpipe and differential pressure for the listed windows, from GDR 1295
  score    secondary predictions (which need the reported differential as an
           input) and the comparison tables

The method is fixed by comparison_protocol.md, protocol-amendment.md and
input-completion.md in this folder.
"""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import statistics as st
import time
import zipfile

import numpy as np

from borethm import hydraulic_losses as hl, model1_coupled as m1, well_geometry as wg
from borethm.fluids import Mud
from borethm.studies import validate_forge16a as a, validate_forge16b as b

HERE = Path(__file__).resolve().parent
FT, INCH, PSI, GPM = 0.3048, 0.0254, 6894.757293168361, 3.785411784e-3/60
PPG = 119.82642731689663
YP_PA = 0.4788025898033584
COMPLETE_BHAS = ('9', '10')
BICO = dict(dp_psi=475.0, flow_low_gpm=300.0, flow_high_gpm=700.0, T_ref_C=(72-32)/1.8,
            source='BICO SSS100-B5 sheet, page 1: 475 psi no-load, 300-700 gpm, clean water at 72 F')
TFA_IN2 = {'9': 0.840, '10': 0.840}
TFA_JETS_IN2 = {'9': 3*np.pi/4*(14/32)**2+4*np.pi/4*(13/32)**2, '10': 3*np.pi/4*(13/32)**2+3*np.pi/4*(14/32)**2}
SURFACE_PRIMARY = 5
JOINT = dict(od_in=6.625, bore_in=3.25, length_in=29.0, pitch_ft=31.5)


def read(name):
    with open(HERE/name, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------- inputs ----------

def rig_inputs():
    with gzip.open(HERE/'rig_inputs_10s.csv.gz', 'rt', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    t = np.array([np.datetime64(r['time']) for r in rows])
    flow = np.array([number(r['flow_gpm']) if number(r['invalid_flow_count']) == 0 else None for r in rows], dtype=float)
    hole = np.array([number(r['hole_depth_ft']) for r in rows], dtype=float)
    inlet = np.array([number(r['inlet_temperature_source_degrees']) for r in rows], dtype=float)
    return t, flow, hole, inlet


class Clock:
    """Cumulative circulation: ten seconds for each bin whose valid mean flow exceeds 100 gal/min."""
    def __init__(self, t, flow, hole):
        self.seconds = (t-t[0]).astype('timedelta64[s]').astype(float)
        self.t0 = t[0]
        self.circ = np.cumsum(np.where(np.nan_to_num(flow) > 100., 10., 0.))
        deepest = np.fmax.accumulate(np.where(np.isfinite(hole), hole, 0.))
        self.depth = deepest*FT

    def exposure(self, when, md_bit):
        now = float(np.interp((np.datetime64(when)-self.t0).astype('timedelta64[s]').astype(float), self.seconds, self.circ))
        return m1.smooth_exposure(m1.exposure_from_history(self.circ, self.depth, now), md_bit)


def mud_for(when, hole_ft, samples):
    """Nearest recorded density, and nearest paired PV/YP, in the same hole section; ties to the earlier sample."""
    section = lambda depth: 0 if depth <= 382 else 1 if depth <= 3506 else 2
    pool = [s for s in samples if section(number(s['sample_depth_ft']) or 0) == section(hole_ft)]
    stamp = lambda s: np.datetime64(f"{s['sample_date']}T{s['sample_time']}")
    key = lambda s: (abs((stamp(s)-np.datetime64(when)).astype('timedelta64[s]').astype(float)), stamp(s))
    density = min((s for s in pool if number(s['mud_weight_ppg'])), key=key)
    paired = [s for s in pool if number(s['plastic_viscosity_cP']) is not None and number(s['yield_point_lbf_100ft2']) is not None]
    rheology = min(paired, key=key) if paired else None
    return dict(density_ppg=number(density['mud_weight_ppg']), mud_sample=f"{density['sample_date']} {density['sample_time']}",
                pv_cP=None if rheology is None else number(rheology['plastic_viscosity_cP']),
                yp=None if rheology is None else number(rheology['yield_point_lbf_100ft2']),
                rheology_sample=None if rheology is None else f"{rheology['sample_date']} {rheology['sample_time']}")


def survey():
    rows = read('survey.csv')
    md = np.array([number(r['Depth']) for r in rows])*FT
    tvd = np.array([number(r['Tru_Vdepth']) for r in rows])*FT
    return wg.Survey(md, tvd)


def hole(md_bit):
    """Casing present from 11 February: 20-in conductor to 129 ft, 13.375-in to 382 ft, 9.625-in to 3,494 ft."""
    r = lambda x: x*INCH/2
    steel = lambda p, q: wg.Layer(p, q, wg.K_STEEL)
    cement = lambda p, q: wg.Layer(p, q, wg.K_CEMENT)
    a_, b_ = r(8.921), r(9.625)
    c_, d_ = r(12.615), r(13.375)
    e_, f_ = r(19.000), r(20.0)
    intervals = [(0., 129.*FT, (steel(a_, b_), cement(b_, c_), steel(c_, d_), cement(d_, e_), steel(e_, f_))),
                 (129.*FT, 382.*FT, (steel(a_, b_), cement(b_, c_), steel(c_, d_), cement(d_, r(17.5)))),
                 (382.*FT, 3494.*FT, (steel(a_, b_), cement(b_, r(12.25))))]
    out = []
    for top, bottom, layers in intervals:
        if top < md_bit:
            out.append(wg.HoleInterval(top, min(bottom, md_bit+1e-6), a_, layers))
    if md_bit > 3494.*FT:
        out.append(wg.open_hole(3494.*FT, md_bit+1e-6, 8.75*INCH))
    return out


def pipe(name, od, inside, joint=None):
    p = wg.PipeType(name, (wg.Layer(inside*INCH/2, od*INCH/2, wg.K_STEEL),))
    if joint is not None:
        from dataclasses import replace
        p = replace(p, hydraulic_joint=joint)
    return p


def motor_loss(flow_ref_gpm):
    rho_ref = float(m1.fluid_props(np.array([BICO['T_ref_C']]), np.array([101325.]), None)[0][0])
    return hl.ReferenceToolLoss(BICO['dp_psi']*PSI, flow_ref_gpm*GPM, rho_ref, basis='total_internal',
                                source=BICO['source']+f'; reference flow {flow_ref_gpm:g} gpm',
                                flow_range=(BICO['flow_low_gpm']*GPM, BICO['flow_high_gpm']*GPM),
                                include_boundary_changes=False)


def motor_dp(flow_ref_gpm, density, flow):
    rho_ref = float(m1.fluid_props(np.array([BICO['T_ref_C']]), np.array([101325.]), None)[0][0])
    return BICO['dp_psi']*PSI*(density/rho_ref)*(flow/(flow_ref_gpm*GPM))**2


def geometry(bha, bit_ft, mode, flow_ref_gpm=None, joint_length_in=JOINT['length_in']):
    """Serial BHA from the sheet; bit as nozzle boundary; motor carries the declared whole-tool curve."""
    components = sorted((c for c in read('bha_components.csv') if c['bha_sheet_id'] == bha), key=lambda c: int(c['item']))
    current = mode == 'v1.6.0'
    joint = hl.HydraulicJoint(JOINT['od_in']*INCH, JOINT['bore_in']*INCH, joint_length_in*INCH, JOINT['pitch_ft']*FT,
                              source='NC50 (4 1/2 IF) catalogue scenario, as for 16A') if current and joint_length_in > 0 else None
    bottom = []
    if not current:
        # The original calculation cannot resolve closely spaced short components; it
        # used a length-weighted compact assembly, as for 16A and 16B. Items 2-5 (motor,
        # UBHO, stabiliser, monel collar) form it; collars, jars and heavy-weight pipe
        # stay separate.
        compact = [c for c in components if c['item'] in ('2', '3', '4', '5')]
        length = sum(number(c['length_ft']) for c in compact)
        inside = lambda c: 3.25 if 'motor' in c['description'].lower() else number(c['ID_in'])
        od = sum(number(c['OD_in'])*number(c['length_ft']) for c in compact)/length
        bore = sum(inside(c)*number(c['length_ft']) for c in compact)/length
        bottom.append(wg.StringSegment(length*FT, pipe('length-weighted compact assembly', od, bore)))
        components = [c for c in components if c not in compact]
    for c in components:
        name, od, inside, length = c['description'].replace('\n', ' '), number(c['OD_in']), number(c['ID_in']), number(c['length_ft'])
        if c['item'] == '1':
            continue                                  # bit: nozzle boundary, its length goes to the drill pipe
        if 'motor' in name.lower():
            thermal = 3.25                            # adjacent NMUBHO bore, thermal only
            tool = motor_loss(flow_ref_gpm) if current else None
            bottom.append(wg.StringSegment(length*FT, pipe(name+'; BICO no-load curve', od, thermal), tool_loss=tool))
            continue
        if 'HWDP' in name.upper() and current:
            hw = hl.HydraulicJoint(JOINT['od_in']*INCH, inside*INCH, joint_length_in*INCH if joint_length_in > 0 else 1e-6,
                                   JOINT['pitch_ft']*FT, source='NC50 catalogue envelope; recorded HWDP bore')
            bottom.append(wg.StringSegment(length*FT, pipe(name, od, inside, hw)))
            continue
        bottom.append(wg.StringSegment(length*FT, pipe(name, od, inside)))
    upper = bit_ft*FT-sum(s.length for s in bottom)
    if upper > 0:
        string = [wg.StringSegment(upper, pipe('5 in 19.5 lb/ft drill pipe', 5.0, 4.276, joint)), *reversed(bottom)]
    else:
        # Bit shallower than the assembly: only its lower part is in the hole.
        string, remaining = [], bit_ft*FT
        for segment in bottom:
            if remaining <= 1e-9:
                break
            from dataclasses import replace
            string.insert(0, segment if segment.length <= remaining else replace(segment, length=remaining))
            remaining -= segment.length
    return wg.WellGeometry(string, hole(bit_ft*FT), survey())


def solve(window, mode, pv_ref_T, flow_ref_gpm, clock, face_W=0.0):
    g = geometry(window['bha'], window['bit_ft'], mode, flow_ref_gpm)
    form = a.formation('216', g.survey)[0]
    fluid = Mud(window['density_ppg']*PPG, pv_ref=None if window['pv_cP'] is None else window['pv_cP']*1e-3,
                yield_point=(window['yp'] or 0.)*YP_PA, pv_ref_T=pv_ref_T)
    q = window['flow_gpm']*GPM
    rho = float(m1.fluid_props(np.array([window['T_in_C']]), np.array([m1.P_SURF]), fluid)[0][0])
    exposure = clock.exposure(window['time'], g.md_bit)
    breaks = m1.exposure_breaks(exposure, g.md_bit)
    surface = hl.SurfaceLoss.api_case(SURFACE_PRIMARY) if mode == 'v1.6.0' else None
    result = m1.solve_seeded(exposure, breaks, m_dot=q*rho, T_inj=window['T_in_C'], geotherm=form, geometry=g,
                             target_rock_T=float(form(g.survey.tvd(g.md_bit))), Q_face=face_W, k_rock=b.K_ROCK,
                             rhocp_rock=b.RHOCP_ROCK, friction_heat=True, tfa=window['tfa_in2']*INCH**2, film_mult=1.,
                             fluid=fluid, verbose=False, hydraulics_model=mode, surface=surface)
    hyd = m1.hydraulics(q*rho, g, result=result, fluid=fluid, tfa=window['tfa_in2']*INCH**2,
                        hydraulics_model=mode, surface=surface)
    row = dict(success=bool(result['success']), spp_psi=hyd['spp']/PSI, rho_in=rho, q=q, fluid=fluid, result=result, geometry=g)
    if mode == 'v1.6.0':
        for case in (1, 2, 3, 4):
            alt = m1.hydraulics(q*rho, g, result=result, fluid=fluid, tfa=window['tfa_in2']*INCH**2,
                                hydraulics_model=mode, surface=hl.SurfaceLoss.api_case(case))
            row[f'spp_surface{case}_psi'] = alt['spp']/PSI
        none = m1.hydraulics(q*rho, g, result=result, fluid=fluid, tfa=window['tfa_in2']*INCH**2,
                             hydraulics_model=mode, surface=hl.SurfaceLoss.coefficient(0., 'no surface loss'))
        row['spp_surface0_psi'] = none['spp']/PSI
        for length in (0.0, 58.0):
            g2 = geometry(window['bha'], window['bit_ft'], mode, flow_ref_gpm, length)
            alt = m1.hydraulics(q*rho, g2, result=result, fluid=fluid, tfa=window['tfa_in2']*INCH**2,
                                hydraulics_model=mode, surface=surface)
            row[f'spp_joint{int(length)}in_psi'] = alt['spp']/PSI
        jets = m1.hydraulics(q*rho, g, result=result, fluid=fluid, tfa=TFA_JETS_IN2[window['bha']]*INCH**2,
                             hydraulics_model=mode, surface=surface)
        row['spp_jets_tfa_psi'] = jets['spp']/PSI
    return row


def windows(role):
    t, flow, hole_, inlet = rig_inputs()
    samples = read('mud_reports.csv')
    out = []
    if role == 'primary':
        rows = [r for r in read('off_bottom_windows.csv') if r['selection'] == 'motor_interval']
        for r in rows:
            bha = str(int(float(r['bha_id'])))
            if bha not in COMPLETE_BHAS:
                continue
            start, end = np.datetime64(r['window_start']), np.datetime64(r['window_end'])
            mask = (t >= start) & (t < end)
            out.append(dict(window_id=r['window_id'], event_id=r['event_id'], role='primary', bha=bha, time=r['time'],
                            flow_gpm=number(r['flow_gpm']), bit_ft=number(r['bit_depth_ft']), hole_ft=number(r['hole_depth_ft']),
                            inlet_F=float(np.nanmean(inlet[mask])), start=r['window_start'], end=r['window_end']))
    else:
        for r in read('candidate_windows.csv'):
            if r['role'] != 'secondary_on_bottom' or not r['bha_sheet_id'] or str(int(float(r['bha_sheet_id']))) not in COMPLETE_BHAS:
                continue
            out.append(dict(window_id=r['window_id'], event_id=r['window_id'], role='secondary', bha=str(int(float(r['bha_sheet_id']))),
                            time=r['time'], flow_gpm=number(r['flow_gpm']), bit_ft=number(r['bit_depth_ft']),
                            hole_ft=number(r['hole_depth_ft']), inlet_F=number(r['inlet_F']),
                            start=r['window_start'], end=r['window_end']))
    complete = []
    for w in out:
        if w['inlet_F'] is None or not np.isfinite(w['inlet_F']):
            continue                                  # missing inlet temperature: incomplete input, counted separately
        w.update(mud_for(w['time'], w['hole_ft'], samples))
        w['T_in_C'] = (w['inlet_F']-32)/1.8
        w['tfa_in2'] = TFA_IN2[w['bha']]
        complete.append(w)
    return complete, Clock(t, flow, hole_)


VARIANTS = [('v1.5.0', 26.7, None, 'legacy_26.7'), ('v1.5.0', 48.9, None, 'legacy_48.9'),
            ('v1.6.0', 48.9, BICO['flow_high_gpm'], 'current_48.9_low'), ('v1.6.0', 48.9, BICO['flow_low_gpm'], 'current_48.9_high'),
            ('v1.6.0', 26.7, BICO['flow_high_gpm'], 'current_26.7_low'), ('v1.6.0', 26.7, BICO['flow_low_gpm'], 'current_26.7_high')]


def predict_rows(ws, clock, faces=None):
    rows = []
    for w in ws:
        row = {k: w[k] for k in ('window_id', 'event_id', 'role', 'bha', 'time', 'flow_gpm', 'bit_ft', 'hole_ft', 'T_in_C',
                                  'density_ppg', 'pv_cP', 'yp', 'mud_sample', 'rheology_sample', 'tfa_in2')}
        face = 0. if faces is None else faces[w['window_id']]
        row['face_W'] = face
        for mode, pv_ref, flow_ref, name in VARIANTS:
            try:
                r = solve(w, mode, pv_ref, flow_ref, clock, face)
                row[f'{name}_success'] = r['success']
                if mode == 'v1.5.0':
                    lo, hi = (motor_dp(f, w['density_ppg']*PPG, r['q'])/PSI for f in (BICO['flow_high_gpm'], BICO['flow_low_gpm']))
                    row[f'{name}_spp_psi'] = r['spp_psi']
                    row[f'{name}_low_psi'], row[f'{name}_high_psi'] = r['spp_psi']+lo, r['spp_psi']+hi
                else:
                    row[f'{name}_psi'] = r['spp_psi']
                    if pv_ref == 48.9:
                        for k, v in r.items():
                            if k.startswith('spp_') and k != 'spp_psi':
                                row[f'{name}_{k}'] = v
                row['flow_outside_rated'] = not (BICO['flow_low_gpm'] <= w['flow_gpm'] <= BICO['flow_high_gpm'])
            except Exception as error:
                row[f'{name}_success'] = False
                row[f'{name}_error'] = f'{type(error).__name__}: {error}'[:160]
        rows.append(row)
        print(row['window_id'], round(row.get('current_48.9_low_psi', float('nan')), 1),
              round(row.get('current_48.9_high_psi', float('nan')), 1), flush=True)
    return rows


def write(path, rows):
    fields = []
    for r in rows:
        fields += [k for k in r if k not in fields]
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def predict(output):
    started = time.perf_counter()
    ws, clock = windows('primary')
    rows = predict_rows(ws, clock)
    output.mkdir(parents=True, exist_ok=True)
    write(output/'primary-predictions.csv', rows)
    print(dict(windows=len(rows), runtime_s=round(time.perf_counter()-started, 1)))


def targets(archive, output):
    """Mean standpipe and differential pressure over each window's source rows, from the weekly Pason files."""
    wanted = {}
    for role in ('primary', 'secondary'):
        ws, _ = windows(role)
        for w in ws:
            wanted[w['window_id']] = (np.datetime64(w['start']), np.datetime64(w['end']))
    sums = {k: [0., 0., 0, 0] for k in wanted}
    starts = np.array([v[0] for v in wanted.values()]); ends = np.array([v[1] for v in wanted.values()])
    ids = list(wanted)
    outer = zipfile.ZipFile(archive)
    nested = (zipfile.ZipFile(io.BytesIO(outer.read('56-32_Pason_Archive.zip')))
              if '56-32_Pason_Archive.zip' in outer.namelist() else outer)
    for member in sorted(n for n in nested.namelist() if n.endswith('.csv') and '__MACOSX' not in n):
        with nested.open(member) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig', newline=''))
            header = next(reader)
            ispp, idiff = header.index('Standpipe Pressure (psi)'), header.index('Differential Pressure (psi)')
            idate, itime = header.index('YYYY/MM/DD'), header.index('HH:MM:SS')
            for row in reader:
                if not row:
                    continue
                when = np.datetime64(row[idate].replace('/', '-')+'T'+row[itime])
                hit = np.nonzero((starts <= when) & (when < ends))[0]
                if not len(hit):
                    continue
                spp, diff = number(row[ispp]), number(row[idiff])
                for i in hit:
                    s = sums[ids[i]]
                    if spp is not None and spp != -999.25:
                        s[0] += spp; s[2] += 1
                    if diff is not None and diff != -999.25:
                        s[1] += diff; s[3] += 1
    rows = [dict(window_id=k, spp_psi=s[0]/s[2] if s[2] else None, differential_psi=s[1]/s[3] if s[3] else None,
                 spp_count=s[2], differential_count=s[3]) for k, s in sums.items()]
    output.mkdir(parents=True, exist_ok=True)
    write(output/'targets.csv', rows)
    print(dict(windows=len(rows), missing=sum(r['spp_psi'] is None for r in rows)))


NAMES = [name for *_, name in VARIANTS]
INTERVALS = {'legacy_26.7': ('legacy_26.7_low_psi', 'legacy_26.7_high_psi'),
             'legacy_48.9': ('legacy_48.9_low_psi', 'legacy_48.9_high_psi'),
             'current_48.9': ('current_48.9_low_psi', 'current_48.9_high_psi'),
             'current_26.7': ('current_26.7_low_psi', 'current_26.7_high_psi')}


def compare(rows, measured_key):
    """Residuals, predicted minus measured, against both interval ends, and coverage."""
    out = []
    for r in rows:
        m = r.get(measured_key)
        row = {k: r[k] for k in ('window_id', 'event_id', 'bha', 'time', 'flow_gpm', 'bit_ft', 'flow_outside_rated') if k in r}
        row['measured_psi'] = m
        for name, (lo, hi) in INTERVALS.items():
            solved = (str(r.get(f'{name}_success')) == 'True' if name.startswith('legacy') else
                      str(r.get(f'{name}_low_success')) == 'True' and str(r.get(f'{name}_high_success')) == 'True')
            a_, b_ = (number(r.get(lo)), number(r.get(hi))) if solved else (None, None)
            row[f'{name}_converged'] = solved
            ok = m is not None and a_ is not None and b_ is not None
            row[f'{name}_low_psi'], row[f'{name}_high_psi'] = a_, b_
            row[f'{name}_inside'] = (a_ <= m <= b_) if ok else None
            for end, v in (('low', a_), ('high', b_)):
                row[f'{name}_{end}_residual_psi'] = v-m if ok else None
                row[f'{name}_{end}_residual_pct'] = 100*(v-m)/m if ok and m != 0 else None
        out.append(row)
    return out


def events(rows):
    groups = {}
    for r in rows:
        groups.setdefault(r['event_id'], []).append(r)
    out = []
    for event, members in groups.items():
        ok = [r for r in members if r['measured_psi'] is not None]
        row = dict(event_id=event, bha=members[0]['bha'], windows=len(members), target_windows=len(ok))
        if ok:
            m = st.median(r['measured_psi'] for r in ok)
            row['measured_psi'] = m
            for name in INTERVALS:
                lows = [r[f'{name}_low_psi'] for r in ok if r[f'{name}_low_psi'] is not None]
                highs = [r[f'{name}_high_psi'] for r in ok if r[f'{name}_high_psi'] is not None]
                if lows and highs:
                    lo, hi = st.median(lows), st.median(highs)
                    row.update({f'{name}_low_psi': lo, f'{name}_high_psi': hi, f'{name}_inside': lo <= m <= hi,
                                f'{name}_low_residual_psi': lo-m, f'{name}_high_residual_psi': hi-m,
                                f'{name}_low_residual_pct': 100*(lo-m)/m if m else None,
                                f'{name}_high_residual_pct': 100*(hi-m)/m if m else None})
        out.append(row)
    return out


def summary(rows, role):
    out = []
    for bha in sorted({r['bha'] for r in rows}):
        group = [r for r in rows if r['bha'] == bha]
        for name in INTERVALS:
            for end in ('low', 'high'):
                values = [r[f'{name}_{end}_residual_psi'] for r in group if r.get(f'{name}_{end}_residual_psi') is not None]
                out.append(dict(role=role, bha=bha, calculation=name, end=end, units=len(group), compared=len(values),
                                inside=sum(bool(r.get(f'{name}_inside')) for r in group),
                                median_residual_psi=st.median(values) if values else None,
                                min_residual_psi=min(values) if values else None,
                                max_residual_psi=max(values) if values else None))
    return out


def score(output):
    targets_ = {r['window_id']: r for r in read_csv(output/'targets.csv')}
    primary = read_csv(output/'primary-predictions.csv')
    for r in primary:
        t = targets_.get(r['window_id'], {})
        r['spp_measured_psi'] = number(t.get('spp_psi'))
    p_windows = compare(primary, 'spp_measured_psi')
    p_events = events(p_windows)
    ws, clock = windows('secondary')
    faces = {}
    for w in ws:
        t = targets_.get(w['window_id'], {})
        diff = number(t.get('differential_psi'))
        faces[w['window_id']] = max(diff or 0., 0.)*PSI*w['flow_gpm']*GPM
    s_pred = predict_rows(ws, clock, faces)
    write(output/'secondary-predictions.csv', s_pred)
    for r in s_pred:
        t = targets_.get(r['window_id'], {})
        spp, diff = number(t.get('spp_psi')), number(t.get('differential_psi'))
        r['target_psi'] = spp-diff if spp is not None and diff is not None else None
    s_windows = compare(s_pred, 'target_psi')
    write(output/'primary-windows.csv', p_windows)
    write(output/'primary-events.csv', p_events)
    write(output/'secondary-windows.csv', s_windows)
    p_events_as_rows = [dict(r, measured_psi=r.get('measured_psi')) for r in p_events]
    write(output/'summary.csv', summary(p_events_as_rows, 'primary events')+summary(s_windows, 'secondary windows'))
    print(dict(primary_windows=len(p_windows), primary_events=len(p_events), secondary_windows=len(s_windows)))


def read_csv(path):
    with open(path, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return [{k: (None if v == '' else v) for k, v in r.items()} for r in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('predict'); p.add_argument('--output', type=Path, default=HERE/'comparison')
    t = sub.add_parser('targets'); t.add_argument('--archive', type=Path, required=True); t.add_argument('--output', type=Path, default=HERE/'comparison')
    c = sub.add_parser('score'); c.add_argument('--output', type=Path, default=HERE/'comparison')
    args = parser.parse_args()
    if args.action == 'predict':
        predict(args.output)
    elif args.action == 'targets':
        targets(args.archive, args.output)
    elif args.action == 'score':
        score(args.output)


if __name__ == '__main__':
    main()
