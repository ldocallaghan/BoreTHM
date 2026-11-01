"""Search primary report pages for pressure-input equipment evidence.

Only the explicitly named development-well documents are opened. Optional
page text for inspection is written to an external scratch directory.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from pypdf import PdfReader

PATTERNS = {
    'pump': r'\bpumps?\b|triplex|duplex|liner|\bstrokes?\b|displacement|efficien|pason|Kenai',
    'nozzle': r'nozzle|\bjets?\b|\bTFA\b|XR\+|centre.?port|center.?port',
    'string': r'kelly|TSDS|TSD40|TSDS40|HWDP|heavy.?weight|drill.?pipe|3\.?5FH|4FH',
    'density': r'mud.?weight|\bdensity\b|\bppg\b',
}


def write(path, rows):
    rows = [{k:'\n'.join(s.rstrip() for s in v.split('\n')) if isinstance(v,str) else v
             for k,v in r.items()} for r in rows]
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fields, lineterminator='\n'); w.writeheader(); w.writerows(rows)


def documents(raw58, raw16a, raw16b):
    for well, path, nested_names in (
        ('58-32', raw58, ('DailyDrillingReports_Well58-32.zip', '58-32_EOWR.zip')),
        ('16A', raw16a, ('2021-well-16a78-32-daily-reports.zip', '16A(78)-32_Daily_Reports.zip')),
        ('16B', raw16b, ('16B Daily Reports.zip',)),
    ):
        with zipfile.ZipFile(path) as top:
            for nested_name in nested_names:
                with zipfile.ZipFile(io.BytesIO(top.read(nested_name))) as nested:
                    for name in sorted(nested.namelist()):
                        if not name.lower().endswith('.pdf') or '__MACOSX' in name:
                            continue
                        if well == '58-32' and nested_name == '58-32_EOWR.zip' and not any(
                            s in name for s in ('DailyDrillingReport', 'BitSummary', 'EOWR_DOE', 'FinalMudLog')):
                            continue
                        yield well, path.name+'!'+nested_name+'!'+name, nested.read(name)
            if well == '58-32':
                for name in ('58-32_EOWR_DOE_22Feb_BinderComplete (1).pdf', 'Well_58-32_Final_Mud_Log.pdf'):
                    yield well, path.name+'!'+name, top.read(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw58', type=Path, required=True)
    p.add_argument('--raw16a', type=Path, required=True)
    p.add_argument('--raw16b', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--scratch', type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True); a.scratch.mkdir(parents=True, exist_ok=True)
    inventory, searches, hits = [], [], []
    cache = {}
    for i, (well, member, data) in enumerate(documents(a.raw58, a.raw16a, a.raw16b), 1):
        sha = hashlib.sha256(data).hexdigest()
        identity = dict(well=well, source_member=member, source_sha256=sha)
        try:
            if sha not in cache:
                reader = PdfReader(io.BytesIO(data))
                cache[sha] = [page.extract_text() or '' for page in reader.pages]
                (a.scratch/(sha+'.json')).write_text(json.dumps(cache[sha], indent=2)+'\n', encoding='utf-8')
            pages = cache[sha]
            total = 0
            for page_number, text in enumerate(pages, 1):
                lines = text.splitlines()
                found = {key:[j for j,line in enumerate(lines,1) if re.search(pattern,line,re.I)] for key,pattern in PATTERNS.items()}
                searches.append(dict(**identity,page=page_number,lines=len(lines),
                    **{key+'_line_hits':len(values) for key,values in found.items()},status='searched'))
                for key, indices in found.items():
                    for j in indices:
                        line = lines[j-1].rstrip()
                        # Reserved thermal observations are not part of this extract.
                        if well == '58-32' and re.search(r'temp|deg\s*[CF]|°',line,re.I):
                            continue
                        hits.append(dict(**identity,page=page_number,line_start=j,line_end=j,
                                         category=key,classification='measured',source_text=line))
                        total += 1
            inventory.append(dict(**identity,pages=len(pages),hit_rows=total,status='searched'))
        except Exception as error:
            inventory.append(dict(**identity,pages='',hit_rows=0,status=type(error).__name__+': '+str(error)))
        print(i,well,member,inventory[-1]['status'],flush=True)
        write(a.output/'source-documents.csv',inventory)
        write(a.output/'source-search-pages.csv',searches)
        write(a.output/'source-lines.csv',hits)
    manifest = dict(method='Declared all-page keyword searches; no model import or calculation',
        patterns=PATTERNS,documents=len(inventory),searched_pages=len(searches),matched_lines=len(hits),
        failures=[r for r in inventory if r['status']!='searched'],
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.glob('*.csv'))})
    (a.output/'source-search-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
