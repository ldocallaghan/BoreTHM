"""Reduce and score the registered FORGE 58-32 pressure comparison.

The extract command opens only source members named by source-bins.csv and
reduces pressure only on its registered native-row and half-open time bounds.
It writes an access record before opening the first member. The build command
uses that saved reduction, without reopening a raw source. No model is solved
here and no scenario is chosen from the observations.
"""
import argparse
from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import statistics as st
import subprocess
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
VARIANTS = ('original', 'working_entry10', 'secondary_entry8')
SCENARIOS = ('primary', 'heavy_pipe', 'wide_joint', 'larger_pipe')
PARTS = ('surface_psi', 'pipe_bore_psi', 'bha_bore_psi', 'bit_nozzles_psi',
         'annulus_psi', 'buoyancy_psi')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def dump(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf-8'))


def write(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    text = io.StringIO(newline='')
    writer = csv.DictWriter(text, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    path.write_bytes(text.getvalue().encode('utf-8'))


def finite(value, sentinel=-999.25):
    try:
        x = float(value)
        return x if math.isfinite(x) and x != sentinel else None
    except (ValueError, TypeError):
        return None


def reduce_bin(values, rule):
    values = [x for value in values if (x := finite(value, rule['missing_sentinel'])) is not None]
    return dict(native_count=len(values), complete=len(values) >= rule['min_native_observations_per_10s_bin'],
                mean_psi=st.fmean(values) if values else None)


def reduce_windows(samples, bins, rule):
    index = {(r['window_id'], r['bin_time']): r for r in bins}
    result = []
    for sample in samples:
        start = datetime.fromisoformat(sample['window_start'])
        group = [index.get((sample['window_id'], (start+timedelta(seconds=10*i)).isoformat(sep=' ')))
                 for i in range(rule['required_bins'])]
        complete = all(r is not None and r['complete'] for r in group)
        result.append(dict(window_id=sample['window_id'], event_id=sample['event_id'],
            bha_id=sample['bha_id'], complete=complete,
            complete_bins=sum(r is not None and r['complete'] for r in group),
            target_psi=st.fmean(r['mean_psi'] for r in group) if complete else None))
    return result


def clean_output(path):
    if path.exists() and any(path.iterdir()):
        raise ValueError('Choose an empty output directory')
    path.mkdir(parents=True, exist_ok=True)


def extract(raw, output, prior_access=None):
    """One source access, with only registered pressure values reduced."""
    clean_output(output)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    committed = subprocess.check_output(['git', 'show', f'{commit}:validation/forge58-32/pressure-test/score_comparison.py'], cwd=ROOT)
    if hashlib.sha256(committed).hexdigest() != sha(Path(__file__)):
        raise ValueError('Scoring script must match its committed version before access')
    subprocess.run(['git','diff','--quiet','HEAD'],cwd=ROOT,check=True)
    protocol = json.loads((HERE/'protocol.json').read_text())
    if protocol['window_pressure_targets_read']:
        raise ValueError('Targets have already been accessed; rebuild from the saved reduction')
    rule = protocol['target_reduction']
    if rule['channel'] != 'Pump Pressure' or not rule['start_inclusive_end_exclusive']:
        raise ValueError('Unexpected target registration')
    samples = read(HERE/'inputs/windows.csv')
    locators = read(HERE/'inputs/source-bins.csv')
    access = dict(access_time_utc=datetime.now(timezone.utc).isoformat(),
        scoring_code_commit=commit, scoring_code_sha256=sha(Path(__file__)),
        protocol_sha256=sha(HERE/'protocol.json'), locators_sha256=sha(HERE/'inputs/source-bins.csv'),
        members={}, status='started')
    if prior_access is not None:
        access['prior_access_attempts'] = json.loads(prior_access.read_text())
    dump(output/'access.json', access)
    groups = defaultdict(list)
    for row in locators:
        groups[row['source_member']].append(row)
    bins = []
    with zipfile.ZipFile(raw/'1006.zip') as top:
        # This is the registered nested archive; unrelated source members are not opened.
        with zipfile.ZipFile(io.BytesIO(top.read('Pason_Logs.zip'))) as nested:
            for source, locations in sorted(groups.items()):
                prefix = '1006.zip!Pason_Logs.zip!'
                if not source.startswith(prefix):
                    raise ValueError('Unregistered source container')
                data = nested.read(source[len(prefix):])
                access['members'][source] = hashlib.sha256(data).hexdigest()
                dump(output/'access.json', access)
                selected = {}
                for loc in locations:
                    for number in range(int(loc['first_source_row']), int(loc['last_source_row'])+1):
                        if number in selected:
                            raise ValueError('Overlapping native-row locators')
                        selected[number] = loc
                values = defaultdict(list)
                header_checked = False
                for number, row in enumerate(csv.reader(io.StringIO(data.decode('utf-8-sig'), newline='')), 1):
                    if number < min(selected):
                        names = [c.strip() for c in row]
                        if rule['channel'] in names:
                            if names.index(rule['channel']) != 8:
                                raise ValueError('Pressure column differs from registered rig layout')
                            header_checked = True
                        elif (len(names) == 36 and names[:2] == ['Date','Time']
                              and names[14:16] == ['Pump','Press']):
                            # Pason's split 36-cell heading precedes 18 data
                            # fields with 18 empty padding cells. The pressure
                            # data column is the registered column 8.
                            header_checked = True
                    if number not in selected:
                        continue
                    if not header_checked:
                        raise ValueError('Registered pressure header was not found before native rows')
                    loc = selected[number]
                    if len(row)>18 and not any(s.strip() for s in row[18:]):
                        row=row[:18]
                    if len(row) not in (9,18):
                        continue
                    try:
                        stamp = datetime.strptime(row[0].strip()+' '+row[1].strip(), '%m/%d/%Y %H:%M:%S')
                    except ValueError:
                        continue
                    start = datetime.fromisoformat(loc['bin_time'])
                    if not start <= stamp < start+timedelta(seconds=10):
                        raise ValueError('Native locator timestamp is outside its registered bin')
                    values[(loc['window_id'], loc['bin_time'])].append(row[8])
                for loc in locations:
                    bins.append(dict(window_id=loc['window_id'], bin_time=loc['bin_time'],
                        source_member=source, first_source_row=loc['first_source_row'],
                        last_source_row=loc['last_source_row'],
                        **reduce_bin(values[(loc['window_id'], loc['bin_time'])], rule)))
    bins.sort(key=lambda r: (r['window_id'], r['bin_time']))
    targets = reduce_windows(samples, bins, rule)
    write(output/'target-bins.csv', bins)
    write(output/'targets.csv', targets)
    access.update(status='complete', output_sha256={p.name:sha(p) for p in sorted(output.glob('*.csv'))})
    dump(output/'access.json', access)


def truth(value):
    return value is True or str(value).lower() == 'true'


def ready(sample):
    return sample['qualification'] == 'ready_with_declared_assumptions'


def percentage(residual, observed):
    return 100*residual/observed if observed != 0 else None


def metric(values):
    if not values:
        return dict(n=0, bias_psi=None, MAE_psi=None, RMSE_psi=None,
                    min_residual_psi=None, max_residual_psi=None)
    return dict(n=len(values), bias_psi=st.fmean(values), MAE_psi=st.fmean(abs(x) for x in values),
                RMSE_psi=math.sqrt(st.fmean(x*x for x in values)),
                min_residual_psi=min(values), max_residual_psi=max(values))


def score(samples, target_rows, predictions):
    """Pure registered reductions; usable with synthetic targets."""
    targets = {r['window_id']:r for r in target_rows}
    ids = [s['window_id'] for s in samples]
    events = list(dict.fromkeys(s['event_id'] for s in samples))
    index = {scenario:{(r['window_id'], r['variant']):r for r in rows}
             for scenario, rows in predictions.items()}
    if any(set(table) != {(w,v) for w in ids for v in VARIANTS} for table in index.values()):
        raise ValueError('Every scenario must retain every planned window and calculation')
    input_ids = {s['window_id'] for s in samples if ready(s)}
    complete = {w for w in ids if truth(targets[w]['complete'])}
    converged = {s:{w for w in ids if all(truth(table[w,v]['success']) for v in VARIANTS)}
                 for s,table in index.items()}
    paired = {s: input_ids & complete & conv for s,conv in converged.items()}
    common = set.intersection(*paired.values())
    windows, event_rows, coverage, summaries, contrasts, budget_rows = [], [], [], [], [], []
    for scenario, table in index.items():
        for sample in samples:
            w = sample['window_id']
            target = float(targets[w]['target_psi']) if w in complete else None
            for variant in VARIANTS:
                p = table[w,variant]
                success = truth(p['success'])
                prediction = float(p['spp_psi']) if success else None
                row = dict(scenario=scenario, window_id=w, event_id=sample['event_id'],
                    bha_id=sample['bha_id'], flow_gpm=sample['flow_gpm'], bit_depth_ft=sample['bit_depth_ft'],
                    input_ready=w in input_ids, target_complete=w in complete,
                    target_complete_bins=targets[w]['complete_bins'], target_psi=target,
                    variant=variant, success=success, solver_status=p.get('solver_status'),
                    solver_message=p.get('solver_message'), predicted_psi=prediction,
                    paired=w in paired[scenario], common_paired=w in common,
                    residual_psi=prediction-target if w in paired[scenario] else None,
                    residual_percent=percentage(prediction-target,target) if w in paired[scenario] else None)
                windows.append(row)
        for cohort, chosen in (('scenario',paired[scenario]), ('common',common)):
            stages = dict(planned=set(ids), input_ready=input_ids,
                          converged=input_ids & converged[scenario],
                          target_complete=input_ids & converged[scenario] & complete, paired=chosen)
            for stage, members in stages.items():
                coverage.append(dict(scenario=scenario, cohort=cohort, bha_id='2', stage=stage,
                    windows=len(members), events=len({s['event_id'] for s in samples if s['window_id'] in members})))
            for variant in VARIANTS:
                members = {w for w in input_ids if truth(table[w,variant]['success'])}
                coverage.append(dict(scenario=scenario, cohort=cohort, bha_id='2',
                    stage='converged_'+variant, windows=len(members),
                    events=len({s['event_id'] for s in samples if s['window_id'] in members})))
            local_events = []
            for event in events:
                planned = [s['window_id'] for s in samples if s['event_id']==event]
                selected = [w for w in planned if w in chosen]
                target = st.median(float(targets[w]['target_psi']) for w in selected) if selected else None
                for variant in VARIANTS:
                    predicted = st.median(float(table[w,variant]['spp_psi']) for w in selected) if selected else None
                    row = dict(scenario=scenario, cohort=cohort, event_id=event, bha_id='2', variant=variant,
                        planned_windows=len(planned), paired_windows=len(selected), paired_ids=';'.join(selected),
                        target_psi=target, predicted_psi=predicted,
                        residual_psi=predicted-target if selected else None,
                        residual_percent=percentage(predicted-target,target) if selected else None)
                    local_events.append(row)
                    if selected:
                        budget = dict(scenario=scenario, cohort=cohort, event_id=event, variant=variant,
                            paired_windows=len(selected), median_target_psi=target,
                            median_predicted_psi=predicted,
                            mean_predicted_psi=st.fmean(float(table[w,variant]['spp_psi']) for w in selected))
                        budget.update({part:st.fmean(float(table[w,variant][part]) for w in selected) for part in PARTS})
                        budget_rows.append(budget)
            event_rows.extend(local_events)
            for weighting in ('event','window'):
                stats = {}
                for variant in VARIANTS:
                    if weighting == 'event':
                        residuals = [r['residual_psi'] for r in local_events if r['variant']==variant and r['paired_windows']]
                    else:
                        residuals = [float(table[w,variant]['spp_psi'])-float(targets[w]['target_psi']) for w in ids if w in chosen]
                    stats[variant] = metric(residuals)
                    summaries.append(dict(scenario=scenario, cohort=cohort, weighting=weighting,
                                          variant=variant, **stats[variant]))
                for candidate, reference in (('working_entry10','original'),('secondary_entry8','original'),
                                             ('working_entry10','secondary_entry8')):
                    a,b = stats[candidate]['RMSE_psi'],stats[reference]['RMSE_psi']
                    contrasts.append(dict(scenario=scenario, cohort=cohort, weighting=weighting,
                        candidate=candidate, reference=reference, n=stats[candidate]['n'],
                        candidate_RMSE_psi=a, reference_RMSE_psi=b,
                        skill=1-a/b if a is not None and b not in (None,0.) else None))
    return dict(windows=windows, events=event_rows, coverage=coverage, summary=summaries,
                contrasts=contrasts, **{'event-budget':budget_rows})


def plots(output, windows):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colours = ('#666666', '#006bb3', '#c36b00')
    for scenario in SCENARIOS:
        fig, axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
        ax0,ax1,ax2,ax3 = axes.flat
        for variant, colour in zip(VARIANTS,colours):
            group = [r for r in windows if r['scenario']==scenario and r['variant']==variant and r['paired']]
            for i,r in enumerate(group):
                ax0.scatter(i,r['predicted_psi'],color=colour,s=13,label=variant if i==0 else None)
            ax1.scatter([float(r['flow_gpm']) for r in group],[r['residual_psi'] for r in group],s=15,color=colour)
            ax2.scatter([float(r['bit_depth_ft']) for r in group],[r['residual_psi'] for r in group],s=15,color=colour)
            ax3.scatter([float(r['bha_id']) for r in group],[r['residual_psi'] for r in group],s=15,color=colour)
        group = [r for r in windows if r['scenario']==scenario and r['variant']=='original' and r['paired']]
        ax0.plot(range(len(group)),[r['target_psi'] for r in group],color='black',linewidth=1,label='measured')
        ax0.set(xlabel='Paired window in registered order',ylabel='Standpipe pressure, psi')
        ax0.legend(fontsize=8)
        for ax,xlabel in ((ax1,'Flow, US gpm'),(ax2,'Bit measured depth, ft'),(ax3,'BHA')):
            ax.axhline(0,color='black',linewidth=.6)
            ax.set(xlabel=xlabel,ylabel='Predicted minus observed, psi')
        ax3.set_xticks([2])
        fig.suptitle('FORGE 58-32: '+scenario)
        fig.savefig(output/(scenario+'.png'),dpi=140,metadata={'Software':'Matplotlib'})
        plt.close(fig)


def build(target_dir, output):
    clean_output(output)
    access = json.loads((target_dir/'access.json').read_text())
    if access['status'] != 'complete' or access['scoring_code_sha256'] != sha(Path(__file__)):
        raise ValueError('Incomplete reduction or different scoring code')
    for name,expected in access['output_sha256'].items():
        if sha(target_dir/name) != expected:
            raise ValueError('Saved target reduction changed')
    samples = read(HERE/'inputs/windows.csv')
    targets = read(target_dir/'targets.csv')
    sources = {scenario:HERE/('model-only' if scenario=='primary' else 'predictions/'+scenario)
               for scenario in SCENARIOS}
    for path in sources.values():
        manifest = json.loads((path/'manifest.json').read_text())
        for name,expected in manifest['output_sha256'].items():
            if sha(path/name) != expected:
                raise ValueError('Model-only prediction changed: '+name)
    predictions = {scenario:read(path/'window-budget.csv') for scenario,path in sources.items()}
    tables = score(samples, targets, predictions)
    for name,rows in tables.items():
        write(output/(name+'.csv'),rows)
    for name in ('access.json','targets.csv','target-bins.csv'):
        (output/name).write_bytes((target_dir/name).read_bytes())
    plots(output,tables['windows'])
    paths = [Path(__file__), HERE/'predict_budget.py', HERE/'protocol.json', HERE/'protocol.md',
             HERE/'coverage-clarification.md', HERE/'inputs/windows.csv', HERE/'inputs/source-bins.csv',
             HERE/'inputs/manifest.json']
    paths.extend(p for path in sources.values() for p in sorted(path.glob('*.csv')))
    import matplotlib
    dump(output/'manifest.json', dict(scoring_code_commit=access['scoring_code_commit'],
        access_time_utc=access['access_time_utc'], source_member_sha256=access['members'],
        python=platform.python_version(), matplotlib=matplotlib.__version__,
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths},
        model_sha256=json.loads((HERE/'protocol.json').read_text())['source_model_sha256'],
        output_sha256={p.name:sha(p) for p in sorted(output.iterdir())},
        planned_windows=len(samples), planned_events=len({s['event_id'] for s in samples}),
        measures='Registered event and secondary window reductions; all contrasts on identical paired IDs'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    p = sub.add_parser('extract')
    p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prior-access-record',type=Path)
    p = sub.add_parser('build')
    p.add_argument('--targets',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.command == 'extract':
        extract(args.raw,args.output,args.prior_access_record)
    else:
        build(args.targets,args.output)


if __name__ == '__main__':
    main()
