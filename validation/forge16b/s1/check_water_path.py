"""Check the new water solve path with identical legacy samples and clock.

The whole-well plan and observations are unchanged. Two separate control plans
replay the already checked legacy inputs through the new study's run function.
No model attribute or function is replaced, and no parameter is fitted.
"""
import csv
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from borethm.studies import validate_forge16b as v
from borethm.studies import validate_forge16b_wholewell as w

HERE=Path(__file__).resolve().parent
BASE=json.loads((HERE/'comparison/plan.json').read_text())
ROOT=HERE/'water-path-control';DATA=ROOT/'legacy-clock'
DATA.mkdir(parents=True,exist_ok=True)
times,circ,depth=v.CLOCK
previous=0.;clock=[]
for t,c,d in zip(times,circ,depth):
    clock.append(dict(time=datetime.fromtimestamp(t,timezone.utc).isoformat(),circulating_count=(c-previous)/10,
                      raw_count=60,missing_flow_count=0,max_hole_depth_ft=d/v.FT));previous=c
w.csv_out(DATA/'circulation_history_10min.csv',clock)
replayed=[json.loads(line) for line in (HERE/'trial-reproduction-samples.jsonl').read_text().splitlines()]
gold=json.loads(v.GOLDEN.read_text());summary=[]
for chain,film,k in [('saved_fitted',gold['film_mult'],gold['k_idp']),('saved_unfitted',1.,gold['unfitted']['k_idp'])]:
    out=ROOT/chain;out.mkdir(exist_ok=True)
    if not (out/'plan.json').exists():
        samples=[];cases=[]
        for n,run in w.TRIAL_RUNS.items():
            for i,s in enumerate(v.on_bottom_samples(run)):
                sid=f'legacy-{n}-{i:03d}'
                samples.append(dict(sample_id=sid,eow_bha=n,bit_ft=s['bit_ft'],time_s=s['time'],
                    flow_gpm=s['flow_gpm'],T_in_C=float(v.F_to_C(s['T_in_F'])),motor_heat_psi=s['motor_dp_psi'],
                    tfa_m2=v.tfa(run),requested_positions_ft=[84]))
                cases.append(dict(case_id=sid,sample_id=sid,fluid='water',film_mult=film,exposure='cumulative'))
        plan={**BASE,'source_hashes':{'circulation_history_10min.csv':w.digest(DATA/'circulation_history_10min.csv')},
              'samples':samples,'cases':cases,'events':[],'k_idp':k,
              'control':'Legacy samples, geometry, water and clock through the new solve path; no field sample plan modified'}
        w.dump(out/'plan.json',plan);(out/'plan.sha256').write_text(w.digest(out/'plan.json')+'\n')
    w.run(DATA,out)
    plan=json.loads((out/'plan.json').read_text());ss={s['sample_id']:s for s in plan['samples']}
    result=[json.loads(line) for line in (out/'results.jsonl').read_text().splitlines()]
    for n,run in w.TRIAL_RUNS.items():
        rr=[r for r in result if r['eow_bha']==n]
        diffs=[]
        for r in rr:
            old=next(x for x in replayed if x['chain']==chain and x['run']==run and x['time']==ss[r['sample_id']]['time_s'])
            diffs.append(r['bore_84ft_C']-float(v.F_to_C(old['mwd_F'])))
        summary.append(dict(chain=chain,run=run,samples=len(rr),failures=sum(not r['success'] for r in rr),
                            max_abs_point_difference_C=max(map(abs,diffs)),
                            mean_difference_C=sum(diffs)/len(diffs),
                            matches_within_existing_seed_agreement_001C=max(map(abs,diffs))<=.01))
w.csv_out(ROOT/'water-path-check.csv',summary)
passed=all(not r['failures'] and r['matches_within_existing_seed_agreement_001C'] for r in summary)
w.dump(ROOT/'water-path-check.json',dict(passed=passed,checks=summary,
     main_plan_unchanged=w.digest(HERE/'comparison/plan.json')==(HERE/'comparison/plan.sha256').read_text().strip()))
print(json.dumps(dict(passed=passed,checks=summary),indent=2))
if not passed:raise SystemExit('Water path control failed')
