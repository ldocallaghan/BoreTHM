"""Synthetic pressure reductions and identical three-calculation cohorts."""
import importlib.util
import csv
from datetime import datetime, timedelta
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

SOURCE = Path(__file__).resolve().parents[1]/'validation/forge58-32/pressure-test/score_comparison.py'
spec = importlib.util.spec_from_file_location('forge58_score',SOURCE)
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)
RULE = dict(required_bins=6, missing_sentinel=-999.25, min_native_observations_per_10s_bin=8)


def sample(w, event='event'):
    return dict(window_id=w,event_id=event,bha_id='2',window_start='2017-08-04 00:00:00',
        qualification='ready_with_declared_assumptions',flow_gpm=500.,bit_depth_ft=1000.)


def bins(w='a', counts=(10,)*6):
    return [dict(window_id=w,bin_time=f'2017-08-04 00:00:{i*10:02d}',
                 **sc.reduce_bin([i*10.]*count,RULE)) for i,count in enumerate(counts)]


def target(w, value=100., complete=True):
    return dict(window_id=w,complete=complete,complete_bins=6 if complete else 0,target_psi=value)


def predictions(samples):
    return {scenario:[dict(window_id=s['window_id'],variant=v,success=True,spp_psi=150.,
                          **{k:25. for k in sc.PARTS}) for s in samples for v in sc.VARIANTS]
            for scenario in sc.SCENARIOS}


def test_equal_bin_weights_and_half_open_six_bins():
    result = sc.reduce_windows([sample('a')],bins(counts=(8,9,10,8,10,9)),RULE)[0]
    assert result['complete']
    assert result['target_psi']==25.


@pytest.mark.parametrize('missing', [True,False])
def test_missing_bin_or_seven_observations_is_incomplete(missing):
    rows = bins()[:-1] if missing else bins(counts=(10,10,7,10,10,10))
    result = sc.reduce_windows([sample('a')],rows,RULE)[0]
    assert not result['complete']
    assert result['complete_bins']==5
    assert result['target_psi'] is None


def test_only_sentinel_and_nonfinite_missing_zero_and_negative_retained():
    row = sc.reduce_bin([0,-1,2,3,4,5,6,7,-999.25,'nan','inf',None,'bad'],RULE)
    assert row['native_count']==8
    assert row['complete']
    assert row['mean_psi']==3.25


def test_joint_convergence_target_and_input_coverage_and_empty_event():
    samples = [sample('a','one'),sample('b','one'),sample('c','empty'),sample('d','unready')]
    samples[-1]['qualification']='incomplete_inlet'
    p = predictions(samples)
    p['primary'][5]['success']=False  # secondary calculation on b
    result = sc.score(samples,[target('a'),target('b'),target('c',complete=False),target('d')],p)
    events = [r for r in result['events'] if r['scenario']=='primary' and r['cohort']=='scenario']
    assert all(r['paired_ids']=='a' for r in events if r['event_id']=='one')
    assert all(r['paired_windows']==0 and r['residual_psi'] is None for r in events if r['event_id']=='empty')
    counts = {r['stage']:r['windows'] for r in result['coverage'] if r['scenario']=='primary' and r['cohort']=='scenario'}
    assert counts['planned']==4
    assert counts['input_ready']==3
    assert counts['converged']==2
    assert counts['target_complete']==counts['paired']==1
    assert counts['converged_secondary_entry8']==2


def test_subtract_event_medians_and_equal_event_weight():
    samples = [sample('a','long'),sample('b','long'),sample('c','long'),sample('d','short')]
    p = predictions(samples)
    for scenario in p:
        for r in p[scenario]:
            r['spp_psi']={'a':100.,'b':300.,'c':200.,'d':500.}[r['window_id']]
    targets = [target('a',100.),target('b',200.),target('c',400.),target('d',300.)]
    result = sc.score(samples,targets,p)
    event = next(r for r in result['events'] if r['scenario']=='primary' and r['cohort']=='scenario' and r['event_id']=='long')
    assert event['residual_psi']==0.
    summary = {r['weighting']:r for r in result['summary'] if r['scenario']=='primary' and r['cohort']=='scenario' and r['variant']=='original'}
    assert summary['event']['bias_psi']==100.
    assert summary['window']['bias_psi']==25.
    assert summary['event']['RMSE_psi']==pytest.approx(2**.5*100)


def test_event_subtracts_medians_not_median_residual():
    samples = [sample(w) for w in 'abc']
    p = predictions(samples)
    for rows in p.values():
        for r in rows:
            r['spp_psi']={'a':10.,'b':20.,'c':100.}[r['window_id']]
    result = sc.score(samples,[target('a',0.),target('b',90.),target('c',95.)],p)
    assert result['events'][0]['residual_psi']==-70.
    assert sorted([10.,-70.,5.])[1]==5.


def test_zero_observation_and_zero_reference_rmse():
    samples=[sample('a')]
    p=predictions(samples)
    for rows in p.values():
        for r in rows:
            r['spp_psi']=0. if r['variant']=='original' else 10.
    result=sc.score(samples,[target('a',0.)],p)
    assert all(r['residual_percent'] is None for r in result['events'])
    assert all(r['skill'] is None and r['reference_RMSE_psi']==0.
               for r in result['contrasts'] if r['reference']=='original')


def test_scenario_cohorts_and_intersection():
    samples=[sample('a'),sample('b','second')]
    p=predictions(samples)
    p['wide_joint'][3]['success']=False
    result=sc.score(samples,[target('a'),target('b')],p)
    own=[r for r in result['summary'] if r['scenario']=='primary' and r['cohort']=='scenario']
    common=[r for r in result['summary'] if r['cohort']=='common']
    assert all(r['n']==2 for r in own)
    assert all(r['n']==1 for r in common)


def test_skill_and_all_contrasts_use_same_ids():
    samples=[sample('a')]
    p=predictions(samples)
    for rows in p.values():
        for r in rows:
            r['spp_psi']={'original':200.,'working_entry10':120.,'secondary_entry8':150.}[r['variant']]
    result=sc.score(samples,[target('a')],p)
    values={(r['candidate'],r['reference']):r['skill'] for r in result['contrasts']}
    assert values['working_entry10','original']==pytest.approx(.8)
    assert values['secondary_entry8','original']==pytest.approx(.5)
    assert values['working_entry10','secondary_entry8']==pytest.approx(.6)


def test_no_paired_windows_has_no_metrics():
    samples=[sample('a')]
    result=sc.score(samples,[target('a',complete=False)],predictions(samples))
    assert all(r['n']==0 and r['RMSE_psi'] is None for r in result['summary'])
    assert all(r['skill'] is None for r in result['contrasts'])


@pytest.mark.parametrize('split_header',[False,True])
def test_extract_uses_only_registered_rows_and_records_access(tmp_path,monkeypatch,split_header):
    data=tmp_path/'study'
    inputs=data/'inputs'
    inputs.mkdir(parents=True)
    sc.dump(data/'protocol.json',dict(window_pressure_targets_read=False,
        target_reduction=dict(RULE,channel='Pump Pressure',start_inclusive_end_exclusive=True)))
    sc.write(inputs/'windows.csv',[sample('a')])
    member='1006.zip!Pason_Logs.zip!Pason_Logs/synthetic.csv'
    sc.write(inputs/'source-bins.csv',[dict(window_id='a',bin_time=f'2017-08-04 00:00:{i*10:02d}',
        source_member=member,first_source_row=2+i*10,last_source_row=11+i*10) for i in range(6)])
    text=io.StringIO(newline='')
    writer=csv.writer(text,lineterminator='\n')
    if split_header:
        heading=['Date','Time']+['input']*34
        heading[14:16]=['Pump','Press']
    else:
        heading=['Date','Time',*['input']*6,'Pump Pressure']
    writer.writerow(heading)
    for i in range(61):
        stamp=datetime(2017,8,4)+timedelta(seconds=i)
        row=[stamp.strftime('%m/%d/%Y'),stamp.strftime('%H:%M:%S'),
             *['unused']*6,100. if i<60 else 'unregistered pressure']
        writer.writerow(row+['unused']*9+['']*18 if split_header else row)
    raw=text.getvalue().encode()
    nested=io.BytesIO()
    with zipfile.ZipFile(nested,'w') as archive:
        archive.writestr('Pason_Logs/synthetic.csv',raw)
        archive.writestr('unregistered.csv','must not be opened')
    with zipfile.ZipFile(tmp_path/'1006.zip','w') as archive:
        archive.writestr('Pason_Logs.zip',nested.getvalue())
    monkeypatch.setattr(sc,'HERE',data)
    monkeypatch.setattr(sc,'ROOT',tmp_path)
    monkeypatch.setattr(sc.subprocess,'check_output',lambda args,**kw:
        'synthetic-commit\n' if args[1]=='rev-parse' else SOURCE.read_bytes())
    monkeypatch.setattr(sc.subprocess,'run',lambda *args,**kw:None)
    sc.extract(tmp_path,tmp_path/'reduction')
    access=json.loads((tmp_path/'reduction/access.json').read_text())
    assert access['status']=='complete'
    assert access['members']=={member:hashlib.sha256(raw).hexdigest()}
    assert sc.read(tmp_path/'reduction/targets.csv')[0]['target_psi']=='100.0'
    assert len(sc.read(tmp_path/'reduction/target-bins.csv'))==6
