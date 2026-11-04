"""Archive compact installed-pipe results and hash external bulk outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):path.write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--scores',type=Path,required=True);p.add_argument('--bulk-output',type=Path,required=True)
    p.add_argument('--declaration',required=True);a=p.parse_args()
    source=a.scores.resolve();bulk=a.bulk_output.resolve()
    if source.is_relative_to(ROOT.resolve()) or bulk.is_relative_to(ROOT.resolve()):
        p.error('Complete scores and bulk storage must be outside the repository')
    bulk.mkdir(parents=True,exist_ok=True);out=HERE/'results';out.mkdir(exist_ok=True)
    records={};rebuildable={}
    command=('python validation/model-development/entry-12/score.py --declaration '+a.declaration+
        ' --output ../entry-12-bulk --scratch ../entry-12-scratch; '+
        'python validation/model-development/entry-12/compare.py --declaration '+a.declaration+' --results ../entry-12-bulk; '+
        'python validation/model-development/entry-12/trip_slopes.py --declaration '+a.declaration+' --output ../entry-12-bulk/secondary')
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        name=path.relative_to(source);dest=bulk/name;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert sha(dest)==sha(path),name
        else:shutil.copy2(path,dest)
        records[name.as_posix()]=dict(sha256=sha(path),bytes=path.stat().st_size)
        compact=(len(name.parts)==1 or (name.parts[0]=='secondary' and path.name!='windows.csv')
                 or (len(name.parts)==2 and path.name in ('scoreboard.csv','run-in.csv','manifest.json')))
        if compact:
            target=out/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target)
        else:rebuildable[name.as_posix()]=dict(**records[name.as_posix()],rebuild_command=command)
    # Per-candidate manifests distinguish compact and external results explicitly.
    for variant in json.loads((HERE/'options.json').read_text(encoding='utf-8'))['variants']:
        path=out/variant/'manifest.json';m=json.loads(path.read_text(encoding='utf-8'))
        m['full_manifest_sha256']=records[variant+'/manifest.json']['sha256']
        m['descriptive_settings_qualification']='Execution snapshot retains inherited eow19/predictions prose; geometry code retained EIS on insulated pipe. Current options correct only those descriptive fields; all numerical settings and selections are unchanged.'
        m['rebuildable_result_sha256']={name:digest for name,digest in m['results_sha256'].items() if not (path.parent/name).exists()}
        m['results_sha256']={name:digest for name,digest in m['results_sha256'].items() if (path.parent/name).exists()}
        write(path,m)
    path=out/'secondary/manifest.json';m=json.loads(path.read_text(encoding='utf-8'))
    m['full_manifest_sha256']=records['secondary/manifest.json']['sha256']
    m['rebuildable_result_sha256']={name:digest for name,digest in m['results_sha256'].items() if not (path.parent/name).exists()}
    m['results_sha256']={name:digest for name,digest in m['results_sha256'].items() if (path.parent/name).exists()}
    write(path,m)
    path=out/'manifest.json';m=json.loads(path.read_text(encoding='utf-8'))
    m['full_manifest_sha256']=records['manifest.json']['sha256']
    m['source_manifests']={v:sha(out/v/'manifest.json') for v in m['variants']}
    write(path,m)
    write(HERE/'bulk-manifest.json',dict(declaration_commit=a.declaration,method='Compact final results retained; full reproducible comparison outputs external',
          all_external_files=records,rebuildable_files=rebuildable,
          archive_command='python validation/model-development/entry-12/archive_results.py --scores ../entry-12-bulk --bulk-output ../entry-12-final-bulk --declaration '+a.declaration))
    print('Retained compact results; recorded',len(rebuildable),'external bulk outputs.')


if __name__=='__main__':main()
