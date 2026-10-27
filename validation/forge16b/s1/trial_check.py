"""Reproduce the two saved 16B trial chains at fixed saved parameters; no fit."""
import csv
import importlib.metadata
import json
import platform
import time
from pathlib import Path
from borethm.studies import validate_forge16b as v

OUT=Path(__file__).resolve().parent
gold=json.loads(v.GOLDEN.read_text())
dest=OUT/'trial-reproduction-samples.jsonl'
done={}
if dest.exists():
    for line in dest.read_text().splitlines():
        row=json.loads(line);done[(row['chain'],row['run'],row['time'])]=row
for chain,film,k in [('saved_fitted',gold['film_mult'],gold['k_idp']),
                     ('saved_unfitted',1.,gold['unfitted']['k_idp'])]:
    for run in ('BHA10','BHA11','BHA12','BHA13'):
        for sample in v.on_bottom_samples(run):
            key=(chain,run,sample['time'])
            if key in done:continue
            start=time.perf_counter()
            row=dict(chain=chain,run=run,film_mult=film,k_idp=k,**v.model_at(run,sample,film,k))
            row['duration_s']=time.perf_counter()-start
            with dest.open('a',encoding='utf-8') as f:f.write(json.dumps(row)+'\n')
            done[key]=row
            print(chain,run,len(done),row['ok'],round(row['duration_s'],2),flush=True)
checks=[]
for chain,target in [('saved_fitted',gold['run_means']),('saved_unfitted',gold['unfitted']['run_means'])]:
    for run in target:
        rows=[r for r in done.values() if r['chain']==chain and r['run']==run]
        mean=v.mean_mwd(rows)
        delta=mean-target[run]
        checks.append(dict(chain=chain,run=run,samples=len(rows),failures=sum(not r['ok'] for r in rows),
                           computed_mean_F=mean,saved_mean_F=target[run],difference_F=delta,
                           pass_existing_1F_tolerance=abs(delta)<=1.0))
with (OUT/'trial-reproduction.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(checks[0]));writer.writeheader();writer.writerows(checks)
passed=all(c['pass_existing_1F_tolerance'] and not c['failures'] for c in checks)
(OUT/'trial-reproduction.json').write_text(json.dumps(dict(passed=passed,python=platform.python_version(),
    versions={x:importlib.metadata.version(x) for x in ['borethm','numpy','scipy','iapws','matplotlib']},
    fitted_parameters_reused=True,no_fitting=True,checks=checks),indent=2)+'\n')
print(json.dumps(dict(passed=passed,checks=checks),indent=2),flush=True)
if not passed:raise SystemExit('Trial water reproduction failed; stop before whole-well calculation')
