"""Rebuild the uncommitted native extracts and verify their manifest hashes.

Requires the same pandas, NumPy and compression runtime as the source build.
Outputs must be outside the repository. This script calls no model function.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def full_association(steps, output):
    with gzip.open(steps,'rt',encoding='utf-8',newline='') as f:
        rows=list(csv.DictReader(f))
    rows=[dict(**r,source_change_match='No dated 58-32 pump/liner/configuration change identified',
        search_inventory='sources/source-search-pages.csv',
        qualification='Rounded ratio record includes segment starts and one-row rounding changes') for r in rows]
    with output.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw58','raw16a','raw16b','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();out=a.output.resolve()
    if out.is_relative_to(ROOT.resolve()):
        p.error('Derived bulk outputs must be outside the repository')
    results=out/'results';results.mkdir(parents=True,exist_ok=True)
    for well,raw in [('58-32',a.raw58),('16A',a.raw16a),('16B',a.raw16b)]:
        subprocess.run([sys.executable,str(HERE/'build_flow.py'),'--well',well,'--raw',str(raw),'--output',str(results)],check=True)
    subprocess.run([sys.executable,str(HERE/'build_checks.py'),'--raw58',str(a.raw58),'--output',str(results)],check=True)
    full_association(results/'58-32-ratio-steps.csv.gz',results/'B2-ratio-change-source-comparison.csv')
    expected=json.loads((HERE/'manifest.json').read_text())['rebuildable_files']
    verified={}
    for name,record in expected.items():
        path=out/name;digest=hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest==record['sha256'],name
        assert path.stat().st_size==record['bytes'],name
        verified[name]=dict(sha256=digest,bytes=path.stat().st_size)
    (out/'rebuild-verification.json').write_text(json.dumps(verified,indent=2)+'\n',encoding='utf-8')
    print('Verified',len(verified),'rebuildable files against the committed manifest.')


if __name__=='__main__':
    main()
