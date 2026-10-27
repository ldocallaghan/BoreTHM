"""Check S1 arithmetic, input provenance and unchanged baseline files."""
import ast
import csv
import hashlib
import json
import math
import statistics as st
from datetime import datetime,timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]/'geothermal-thermo-hydraulic-model'
DATA=ROOT/'validation/forge16b';OUT=HERE/'comparison'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
plan=json.loads((OUT/'plan.json').read_text())
rows=[json.loads(x) for x in (OUT/'results.jsonl').read_text().splitlines()]
assert len(rows)==872 and {r['case_id'] for r in rows}=={r['case_id'] for r in plan['cases']}
assert digest(OUT/'plan.json')==(OUT/'plan.sha256').read_text().strip()
assert digest(ROOT/'src/borethm/studies/validate_forge16b_wholewell.py')==plan['study_sha256']
for name,h in plan['source_hashes'].items():assert digest(DATA/name)==h,name
for name,h in {**plan['calculation_hashes'],**plan['package_input_hashes']}.items():assert digest(Path(name))==h,name
s0=HERE.parent/'s0'
old=json.loads((s0/'S0-audit.json').read_text())
for name,h in old['new_files_sha256'].items():assert digest(ROOT/name)==h,name
base=json.loads((s0/'model-and-existing-input-hashes.json').read_text())
for name,h in base.items():assert digest(ROOT/name)==h,name
samples={s['sample_id']:s for s in plan['samples']}
assert len(samples)==109
for s in samples.values():
    assert s['motor_heat_psi']==(max(0,s['reported_differential_psi']) if s['documented_motor'] else 0.)
    n=s['eow_bha']
    assert s['requested_positions_ft']==([22,69,84] if n==3 else [22,84] if n in (4,27,38) else [int(s['sensor_offset_ft'])])
lookup={r['case_id']:r for r in rows}
for x in read(OUT/'sample-comparisons.csv'):
    r=lookup[x['case_id']];s=samples[x['sample_id']]
    if r['success']:
        error=r[f"bore_{x['position_ft']}ft_C"]-s['measured_MWD_C']
        assert math.isclose(float(x['error_C']),error,abs_tol=1e-11)
        assert math.isclose(float(x['error_F']),error*1.8,abs_tol=1e-11)
for x in read(OUT/'run-metrics.csv'):
    rr=[r for r in rows if r['eow_bha']==int(x['eow_bha']) and r['fluid']==x['fluid'] and
        r['film_mult']==float(x['film_mult']) and r['exposure']==x['exposure']]
    good=[r for r in rr if r['success']]
    assert len(rr)==int(x['n']) and len(good)==int(x['converged'])
    if good:
        es=[r[f"bore_{x['position_ft']}ft_C"]-samples[r['sample_id']]['measured_MWD_C'] for r in good]
        assert math.isclose(st.mean(es),float(x['bias_C']),abs_tol=1e-11)
        assert math.isclose(st.mean(map(abs,es)),float(x['MAE_C']),abs_tol=1e-11)
        assert math.isclose(math.sqrt(st.mean(e*e for e in es)),float(x['RMSE_C']),abs_tol=1e-11)
obs={}
for filename in ['mud_samples.csv','mud_supplement_s1.csv']:
    for i,r in enumerate(read(DATA/filename),1):obs[f'{filename}:{i}']=r
def stamp(s):return datetime.strptime(s[:15],'%d-%b-%y %H:%M').replace(tzinfo=timezone.utc).timestamp()
def system(t):
    if t<datetime(2023,5,3,21,50,tzinfo=timezone.utc).timestamp():return 0
    if t<datetime(2023,5,12,15,30,tzinfo=timezone.utc).timestamp():return 1
    return 2
ledger=read(OUT/'mud-assignment-ledger.csv')
for r in ledger:
    source=obs[r['source_id']];field=r['field'];t=stamp(source['sample'])
    earlier=[]
    for key,row in obs.items():
        try:value=float(row.get(field,''))
        except ValueError:continue
        at=stamp(row['sample'])
        if at<t and system(at)==system(t):earlier.append((at,key,value))
    if r['method']=='nearest earlier within fluid system':
        donor=obs[r['donor_source_id']]
        assert stamp(donor['sample'])<t and system(stamp(donor['sample']))==system(t)
        assert stamp(donor['sample'])==max(x[0] for x in earlier)
        assert float(r['value'])==float(donor[field])
    elif r['method']=='BoreTHM reference rheology':
        assert not earlier
        assert math.isclose(float(r['value']),27 if field=='PV_cP' else 28,abs_tol=1e-6)
    else:assert float(r['value'])==float(source[field])
for m in plan['mud']:
    for field in ['density_ppg','PV_cP','YP_lbf_100ft2']:
        vals=[float(r['value']) for r in ledger if int(r['eow_bha'])==m['eow_bha'] and r['field']==field]
        assert math.isclose(st.mean(vals),m[field],abs_tol=1e-12)
components=read(DATA/'component_inputs_s1.csv')
expected={3:841.42,11:1354.08,12:1296.36,13:1286.80,15:1306.63,16:1306.41,38:1082.68}
for n,total in expected.items():
    assert math.isclose(sum(float(r['length_ft']) for r in components if int(r['eow_bha'])==n),total,abs_tol=.011),(n,total)
for r in components:assert 0<float(r['id_in'])<float(r['od_in']) and float(r['length_ft'])>0
for r in rows:
    if r['success']:
        s=samples[r['sample_id']]
        values=[r[f'bore_{p}ft_C'] for p in s['requested_positions_ft']]
        assert math.isclose(max(values)-min(values),r['requested_position_spread_C'],abs_tol=1e-12)
tree=ast.parse((ROOT/'src/borethm/studies/validate_forge16b_wholewell.py').read_text())
assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in ['fit_film','fit_idp','run_all'] for n in ast.walk(tree))
control=json.loads((HERE/'water-path-control/water-path-check.json').read_text())
assert control['passed'] and control['main_plan_unchanged']
legacy=[json.loads(line) for line in (HERE/'trial-reproduction-samples.jsonl').read_text().splitlines()]
control_count=0
for chain in ['saved_fitted','saved_unfitted']:
    path=HERE/'water-path-control'/chain
    cp=json.loads((path/'plan.json').read_text());cs={s['sample_id']:s for s in cp['samples']}
    for line in (path/'results.jsonl').read_text().splitlines():
        r=json.loads(line);s=cs[r['sample_id']]
        legacy_row=next(x for x in legacy if x['chain']==chain and x['run']=={17:'BHA10',18:'BHA11',19:'BHA12',20:'BHA13'}[r['eow_bha']] and x['time']==s['time_s'])
        assert r['success'] and math.isclose(r['bore_84ft_C'],(legacy_row['mwd_F']-32)/1.8,abs_tol=1e-10)
        control_count+=1
assert control_count==len(legacy)==150
report=dict(completed_cases=len(rows),failed_cases=sum(not r['success'] for r in rows),water_path_controls_verified=control_count,
            s0_files_unchanged=len(old['new_files_sha256']),baseline_files_unchanged=len(base),
            verified_run_metric_rows=len(read(OUT/'run-metrics.csv')),verified_mud_field_assignments=len(ledger),
            verified_component_totals=len(expected),no_fitting_entrypoint_calls=True)
(OUT/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
