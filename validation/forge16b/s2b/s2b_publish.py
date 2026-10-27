"""Publish the compact S2b evidence archive outside the installed package."""
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]/'geothermal-thermo-hydraulic-model'
SOURCE=HERE/'s2b'
DEST=ROOT/'validation/forge16b/s2b'
DEST.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['plan.json','plan.sha256','pressure-samples.csv','model-pieces.csv',
       'bha-components.csv','bha-transitions.csv','scenario-budgets.csv',
       'pressure-run-summary.csv','scenario-run-summary.csv','nominal-sample-accounting.csv',
       'replays.csv','audit.json','S2b-review.md','pressure-accounting.png','commands.md']
for name in names:shutil.copyfile(SOURCE/name,DEST/name)
with (DEST/'tool-joints.csv.gz').open('wb') as dest:
    with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0) as out:
        out.write((SOURCE/'tool-joints.csv').read_bytes())
profiles={}
for path in sorted((SOURCE/'profiles').glob('*.npz')):
    with np.load(path) as profile:
        for name in profile.files:profiles[path.stem+'_'+name]=profile[name]
np.savez_compressed(DEST/'replayed-profiles.npz',**profiles)
for name in ['s2b_audit.py','s2b_report.py','s2b_publish.py']:
    shutil.copyfile(HERE/name,DEST/name)
shutil.copyfile(ROOT/'src/borethm/studies/forge16b_hydraulics.py',DEST/'execution-source.py')
plan=json.loads((SOURCE/'plan.json').read_text())
manifest=dict(baseline=plan['baseline'],versions=plan['versions'],
    original_script_sha256=plan['script_sha256'],plan_sha256=sha(SOURCE/'plan.json'),
    archive_note='New external S2b estimates; original S1/S2 evidence unchanged.',
    archived_output_sha256={p.name:sha(p) for p in sorted(DEST.iterdir()) if p.is_file() and p.name!='execution-manifest.json'})
(DEST/'execution-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print('Published',len(manifest['archived_output_sha256']),'files;',sum(p.stat().st_size for p in DEST.iterdir()),'bytes')
