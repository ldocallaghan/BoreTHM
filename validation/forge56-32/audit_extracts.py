"""Check 56-32 input/provenance integrity without reading target series."""
import argparse
import ast
import csv
import gzip
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

HERE=Path(__file__).resolve().parent
GENERATED = (
    'bha_components.csv', 'bha_runs.csv', 'bit_records.csv', 'casing_records.csv',
    'mud_reports.csv', 'operating_notes.csv', 'operations.csv', 'pipe_tallies.csv',
    'survey.csv', 'survey-source.json', 'source_reports.json',
    'report_extraction_audit.json', 'rig_inputs_10s.csv.gz', 'target_availability.json',
    'rig-inputs.json', 'extract-summary.json', 'bha_crosswalk.csv', 'candidate_windows.csv',
    'window-preparation.json',
)


def read(root,name):
    with (gzip.open(root/name,'rt',encoding='utf-8',newline='') if name.endswith('.gz') else (root/name).open(encoding='utf-8',newline='')) as f:return list(csv.DictReader(f))


def audit(root):
    counts=json.loads((root/'target_availability.json').read_text())
    for r in counts:
        for c in r['targets']:assert c['finite']+c['missing']==r['raw_rows']
    assert sum(r['raw_rows'] for r in counts)==2506182
    spp=[c for r in counts for c in r['targets'] if c['channel']=='Standpipe Pressure (psi)']
    assert sum(c['finite'] for c in spp)==2476669
    assert sum(c['missing'] for c in spp)==29513
    target_tokens=('Standpipe','Differential','Temp OUT','MWD Temp','observed_pressure','measured_pressure')
    n=0;last=None
    with gzip.open(root/'rig_inputs_10s.csv.gz','rt',encoding='utf-8',newline='') as f:
        rr=csv.DictReader(f)
        assert not any(t.lower() in key.lower() for key in rr.fieldnames for t in target_tokens)
        for row in rr:
            t=datetime.fromisoformat(row['time']);assert last is None or t>last;last=t;n+=1
            assert int(row['source_rows'])==int(row['last_source_row'])-int(row['first_source_row'])+1
            for key in ('hole_depth_ft','bit_depth_ft','flow_gpm'):
                if row[key]:assert float(row[key+'_min'])-1e-9<=float(row[key])<=float(row[key+'_max'])+1e-9
    assert n==sum(r['input_bins_10s'] for r in counts)
    bhas=read(root,'bha_runs.csv');components=read(root,'bha_components.csv')
    assert len(bhas)==11 and len(components)==87
    assert len(read(root,'bit_records.csv'))==16 and len(read(root,'survey.csv'))==97
    assert len(read(root,'mud_reports.csv'))==28
    first=next(r for r in components if r['bha_sheet_id']=='1' and r['item']=='2')
    assert float(first['OD_in'])==9.625 and float(first['length_ft'])==33.63
    assert not first['ID_in']  # A missing motor bore is preserved, not invented.
    malformed=next(r for r in bhas if r['bha_sheet_id']=='3')
    assert not malformed['depth_out_ft'] and malformed['depth_out_source']=='2021/02/11'
    assert float(malformed['depth_out_derived_candidate_ft'])==3500
    assert not next(r for r in bhas if r['bha_sheet_id']=='5')['date_out']
    for row in read(root,'mud_reports.csv'):
        assert not row['rheology_measurement_temperature_C']
        if row['plastic_viscosity_cP']:
            assert row['pv_ref_T_primary_C']=='48.9' and row['pv_ref_T_sensitivity_C']=='26.7'
    cases=read(root,'candidate_windows.csv')
    assert len({r['window_id'] for r in cases})==len(cases)
    assert all(r['readiness']=='pending_V0_source_rulings' for r in cases)
    assert all(datetime.fromisoformat(r['time'])<datetime(2021,2,28) for r in cases)
    stats=Counter(r['role'] for r in cases)
    for script in ('build_extracts.py','prepare_pressure.py'):
        tree=ast.parse((HERE/script).read_text())
        names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):names.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):names.append(node.module or '')
        assert not any(x.startswith('borethm') for x in names)
    print(json.dumps(dict(input_bins=n,source_rows=sum(r['raw_rows'] for r in counts),
                         standpipe_finite=sum(c['finite'] for c in spp),standpipe_missing=sum(c['missing'] for c in spp),
                         candidate_windows=stats,source_conflicts_preserved=True,model_runs=0,target_series_read=False),indent=2))


def compare(root, other):
    for name in GENERATED:
        expected = hashlib.sha256((root / name).read_bytes()).hexdigest()
        actual = hashlib.sha256((other / name).read_bytes()).hexdigest()
        assert expected == actual, f'Rebuild differs: {name}'
    print(json.dumps({'rebuild_files_checked': len(GENERATED), 'all_SHA256_identical': True}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=HERE)
    parser.add_argument('--compare', type=Path, help='Compare all generated files with an independent rebuild')
    args = parser.parse_args()
    audit(args.data)
    if args.compare is not None:
        compare(args.data, args.compare)
