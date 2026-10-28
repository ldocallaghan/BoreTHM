"""Complete input-unavailable cases through the unchanged frozen scoreboard.

The retained batch has identical equations for unaffected assemblies. Only
the three explicitly authorised thermal-only instrument bores differ. Every
original sample and event is restored in its original order before scoring.
"""
import argparse
import importlib.util
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('d5_analysis',Path(__file__).with_name('analyse_score.py'))
analysis=importlib.util.module_from_spec(spec);spec.loader.exec_module(analysis)
score=analysis.score


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):parser.error('Choose an empty output directory')
    args.output.mkdir(parents=True,exist_ok=True)
    started=time.perf_counter()
    plan=score.read_json(score.PLAN);inputs=score.read_json(ROOT/'validation/scoreboard/transient-inputs.json')
    retained=[analysis.numeric(r) for r in score.read_csv(args.completed/'circulation.csv')]
    events=[analysis.numeric(r) for r in score.read_csv(args.completed/'run-in.csv')]
    missing={r['sample_id'] for r in retained if not r['success']}
    assert len(missing)==156
    assert {r['bha'] for r in retained if r['sample_id'] in missing}=={'23','38','39'}
    event_ids={e['event_id'] for e in events if e['archived_available'] and not e['success']}
    assert len(event_ids)==5
    score.write_csv(args.output/'initial-input-unavailable.csv',[r for r in retained if not r['success']])
    replacements=score.circulation({**plan,'samples':[s for s in plan['samples'] if s['id'] in missing]},'current',args.output)
    mapping={r['sample_id']:r for r in replacements}
    rows=[mapping.get(r['sample_id'],r) for r in retained]
    assert [r['sample_id'] for r in rows]==[s['id'] for s in plan['samples']]
    new_events=score.run_in({**inputs,'events':[e for e in inputs['events'] if e['event_id'] in event_ids]},'current',plan,args.output)
    mapping={r['event_id']:r for r in new_events}
    events=[mapping.get(e['event_id'],e) for e in events]
    assert [e['event_id'] for e in events]==[e['event_id'] for e in inputs['events']]
    score.write_csv(args.output/'circulation.csv',rows)
    score.write_csv(args.output/'run-in.csv',events)
    score.write_csv(args.output/'scoreboard.csv',score.scoreboard(rows,events))
    original=score.read_json(args.completed/'manifest.json')
    manifest={**original,'declaration_commit':'ae98695',
        'retained_batch_model_sources_sha256':original['model_sources_sha256'],
        'model_sources_sha256':{name:score.sha(ROOT/'src/borethm'/name) for name in original['model_sources_sha256']},
        'assembly_audit_sha256':score.sha(Path(__file__).with_name('components.json')),
        'completion_implementation_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'completion_script_sha256':score.sha(Path(__file__)),
        'retained_circulation_cases':len(retained)-len(missing),'completed_circulation_cases':len(replacements),
        'retained_run_in_cases':sum(e['archived_available'] for e in events)-len(new_events),
        'completed_run_in_cases':len(new_events),'completion_runtime_s':time.perf_counter()-started,
        'initial_runtime_s':886.3102178999688,
        'results_sha256':{p.name:score.sha(p) for p in args.output.glob('*.csv')}}
    score.write_json(args.output/'manifest.json',manifest)
    print(dict(completion_runtime_s=manifest['completion_runtime_s'],
        circulation_cases=len(rows),circulation_failures=sum(not r['success'] for r in rows),
        run_in_failures=sum(e['archived_available'] and not e['success'] for e in events)),flush=True)


if __name__=='__main__':main()
