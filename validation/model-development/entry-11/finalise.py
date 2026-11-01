"""Assemble the diagnosis archive without changing any model input."""
import argparse
import csv
import gzip
import hashlib
import json
import shutil
from pathlib import Path

from build_sources import write
from rebuild_bulk import full_association

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bulk-output',type=Path,required=True)
    args=parser.parse_args();bulk=args.bulk_output.resolve()
    if bulk.is_relative_to(ROOT.resolve()):parser.error('Bulk output must be outside the repository')
    (bulk/'results').mkdir(parents=True,exist_ok=True)
    results=HERE/'results';sources=HERE/'sources'
    # The flow reducer creates an unused pressure stream for the other wells.
    # Those contain no header or observation and are not final source extracts.
    for well in ('16A','16B'):
        name=well+'-pressure-inputs.csv.gz';path=results/name
        manifest=results/(well+'-flow-manifest.json');m=json.loads(manifest.read_text())
        if path.exists():
            assert gzip.decompress(path.read_bytes())==b''
            digest=hashlib.sha256(path.read_bytes()).hexdigest();path.unlink()
            m['output_sha256'].pop(name)
            m['omitted_empty_stream']=dict(name=name,sha256=digest,reason='No pressure projection requested for this well')
            manifest.write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    # Calendar association is explicit; it does not establish a clock offset.
    changes=[]
    for r in read(sources/'source-lines.csv'):
        text=r['source_text']
        if r['well']=='16B' and ('pump liners from 6' in text or 'changing mud pump liners to 5-1/2' in text):
            changes.append(dict(classification='measured source record',well=r['well'],
                report_date='2023-05-04' if '20230504' in r['source_member'] else '2023-05-05',
                source_member=r['source_member'],source_sha256=r['source_sha256'],page=r['page'],
                line_start=r['line_start'],line_end=r['line_end'],source_text=text,
                qualification='Report calendar date; exact change completion time and Pason clock relation unresolved'))
    write(sources/'dated-pump-changes.csv',changes)
    full_association(results/'58-32-ratio-steps.csv.gz',results/'B2-ratio-change-source-comparison.csv')
    rows=[]
    for r in read(results/'58-32-ratios-by-day.csv'):
        rows.append(dict(day=r['day'],combination=r['combination'],native_rows=r['native_rows'],
            median_gal_stroke=r['median_gal_stroke'],min_gal_stroke=r['min_gal_stroke'],max_gal_stroke=r['max_gal_stroke'],
            source_member=r['source_member'],first_source_row=r['first_source_row'],last_source_row=r['last_source_row'],
            source_change_match='No dated 58-32 pump/liner/configuration change identified',
            qualification='Compact daily association; all rounded changes rebuildable externally',
            search_inventory='sources/source-search-pages.csv'))
    write(results/'B2-daily-change-source-comparison.csv',rows)
    names=('16A-ratio-changes.csv.gz','A2-native-comparisons.csv.gz','58-32-ratio-changes.csv.gz',
           '58-32-pressure-inputs.csv.gz','16B-ratio-changes.csv.gz','B2-ratio-change-source-comparison.csv')
    rebuildable={}
    command='python validation/model-development/entry-11/rebuild_bulk.py --raw58 1006.zip --raw16a 1283.zip --raw16b 1516.zip --output ../entry-11-bulk'
    for name in names:
        src=results/name;dest=bulk/'results'/name
        if src.exists():
            if dest.exists():assert src.read_bytes()==dest.read_bytes(),name
            else:shutil.copy2(src,dest)
            src.unlink()
        assert dest.is_file(),name
        rebuildable['results/'+name]=dict(sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
            bytes=dest.stat().st_size,rebuild_command=command,
            runtime='Python 3.12.14; pandas 3.0.1; NumPy 2.3.5; gzip mtime=0',
            disposition='Rebuildable derived file; not committed; raw source filenames must remain unchanged')
    enquiries=[
        ('Kenai Drilling, historical Rig 10 equipment custodian','Which pump model, stroke and liners were installed on Rig 10 on 3-6 August 2017? Supply dated equipment records.','Would establish whether the later 6.75-in by 10-in specification applies and independently verify displacement'),
        ('Pason data/configuration custodian and FORGE dataset custodian','What volume per stroke and efficiency were configured for 3-11 August 2017 and from 12 August? Was Flow In calculated or independently measured?' ,'Would explain the recorded flow/stroke regimes without selecting a pressure-fitting factor'),
        ('Kenai Drilling and FORGE drilling-report custodian','Pump-pressure transducer and report-gauge locations, calibration and zeroing records','Would establish whether the observations correspond to the standpipe boundary used by the model'),
        ('Bit supplier and FORGE bit-record custodian','Bit run 2 nozzle installation sheet and any open or centre port','Would independently confirm the recorded three 22/32-in jets and total opening area'),
        ('String supplier and FORGE drilling-record custodian','Installed ordinary-pipe and HWDP body/joint IDs and tally; conflicting HWDP thread labels','Would distinguish recorded nominal size from actual hydraulic passages'),
        ('FORGE mud-report custodian','Density-test provenance and whether daily flow and bit-hydraulic entries were calculated nominal values','Would check the physical meaning of the repeated 613-gpm entry'),
        ('16A rig-data provider and FORGE custodian','Per-pump drilling-period stroke channels; 29 October 11-in versus other 12-in stroke records','Would identify each pump configuration without substituting later stimulation data'),
        ('Frontier Drilling and Pason, 16B equipment/data custodians','Stroke length and per-pump displacement/efficiency settings through the 6-in to 5.5-in liner change','Would verify the source of the observed 16B flow-per-stroke change'),
    ]
    write(results/'enquiries.csv',[dict(classification='inferred source gap',custodian=o,question=q,what_it_settles=s) for o,q,s in enquiries])
    write(results/'diagnostic-solves.csv',[dict(classification='calculated coverage',status='not run',
        reason='No numerical correction independently established for the registered 2017 operating period; later rig-specification arithmetic is time-transferred only',
        slow_case='Report slow-pressure readings lack unique native time and bit-position identification',
        adoption='No corrected input adopted; no skill score')])
    statuses=[
        ('A1','complete','All daily and event scopes available; retained pump-off readings do not establish a dynamic correction'),
        ('A2','complete','Every parsed daily drilling-parameter interval retained; unavailable native coverage explicit'),
        ('A3','complete','Every qualifying native slow-circulation period retained, including brief transitions'),
        ('B1','complete','Native exact and rounded ratio records, day and pump-combination summaries'),
        ('B2','complete, source gap','No dated 58-32 pump/liner/configuration record found to identify the ratio changes'),
        ('B3','complete, source gap','All supplied relevant PDF pages searched; published later rig specification found, 2017 applicability unresolved'),
        ('B4','qualified arithmetic','All registered windows calculated at the published specification displacement and 100% efficiency; no 2017 applicability established and no efficiency supplied'),
        ('C','complete, source gap','Three 22/32-in jets and printed TFA confirmed; additional-port installation evidence unavailable'),
        ('D','complete, source gap','Nominal inventory and kelly confirmed; installed connection bores and full surface layout unresolved'),
        ('E','complete','Reported densities transcribed; density-equivalent bounds retained as bounds only'),
        ('F','qualified completion','16A total-only drilling export; per-pump check unavailable. 16B third-pump combinations included. No earlier study changed'),
    ]
    write(results/'check-status.csv',[dict(classification='calculated coverage',check=k,status=s,result=r) for k,s,r in statuses])
    # Canonical final text bytes avoid platform newline conversion changing
    # the committed checksums. Trimming PDF line-end spaces changes no cell.
    for path in sorted(sources.rglob('*.csv')):
        records=read(path)
        if records:write(path,records)
    for folder in (sources,results):
        for path in sorted(folder.rglob('*.json')):
            value=json.loads(path.read_text(encoding='utf-8'))
            for key in ('output_sha256','outputs'):
                if key in value:
                    for name in list(value[key]):
                        candidate=path.parent/name
                        if candidate.exists():value[key][name]=hashlib.sha256(candidate.read_bytes()).hexdigest()
                        elif 'results/'+name in rebuildable:
                            digest=value[key].pop(name)
                            assert digest==rebuildable['results/'+name]['sha256'],name
                            value.setdefault('rebuildable_output_sha256',{})[name]=digest
            path.write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))
    manifest=dict(declaration_commit='ea5f8b5ec6fafc3f1303f38136f19939e0f0546b',
        comparison_base='7bf08b1ef69aa713b07150db2c06687144a81fd3',
        method='Source diagnosis only; source-recorded, calculated and inferred findings labelled; no new scored test or adopted correction',
        rebuildable_files=rebuildable,
        code_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.glob('*.py'))},
        inherited_input_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
            'validation/forge58-32/pressure-test/inputs/windows.csv',
            'validation/forge58-32/pressure-test/inputs/source-bins.csv',
            'validation/forge58-32/pressure-test/bha2-figure14.json',
            'validation/forge58-32/pressure-test/results/events.csv',
            'validation/forge58-32/pressure-test/results/event-budget.csv',
            'validation/forge58-32/pressure-test/protocol.json',
            'validation/forge58-32/rig_inputs_10s.csv.gz',
            'validation/forge58-32/mud_reports.csv')},
        archive_sha256={p.relative_to(HERE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in (sources,results) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='manifest.json'})
    (HERE/'manifest.json').write_bytes((json.dumps(manifest,indent=2)+'\n').encode('utf-8'))


def read_gzip(path):
    with gzip.open(path,'rt',encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


if __name__=='__main__':main()
