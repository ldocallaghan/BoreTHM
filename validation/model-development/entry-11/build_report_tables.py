"""Extract daily parameter intervals and source-identified pump dimensions.

Source table rows are retained with page locators; nothing is fitted.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

import pdfplumber
from build_sources import write


def parameters(raw, output):
    rows, audit = [], []
    with zipfile.ZipFile(raw) as top, zipfile.ZipFile(io.BytesIO(top.read('DailyDrillingReports_Well58-32.zip'))) as z:
        for name in sorted(n for n in z.namelist() if 'DailyReportSummary' in n and n.endswith('.pdf')):
            data=z.read(name);sha=hashlib.sha256(data).hexdigest();member=raw.name+'!DailyDrillingReports_Well58-32.zip!'+name
            count=0;explicit_none=False
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for pn,page in enumerate(pdf.pages,1):
                    text=page.extract_text() or ''
                    explicit_none |= 'No Drilling Parameters Records for this report.' in text
                    date=re.search(r'Report For\s+(\d{2}-[A-Za-z]{3}-\d{2})',text)
                    report=re.search(r'Report No:\s*(\d+)',text)
                    for ti,table in enumerate(page.extract_tables(),1):
                        section=False
                        for ri,row in enumerate(table,1):
                            cells=[str(x).strip() for x in row if x is not None]
                            if any('Drilling Parameters' in c for c in cells):section=True;continue
                            if section and cells and re.fullmatch(r'[\d,]+-[\d,]+',cells[0]) and len(cells)>=9:
                                depth=[float(x.replace(',','')) for x in cells[0].split('-')]
                                try:flow=float(cells[5]);pressure=float(cells[8])
                                except ValueError:continue
                                rows.append(dict(classification='measured',report_no=report[1] if report else '',
                                    report_date=date[1] if date else '',depth_start_ft=depth[0],depth_end_ft=depth[1],
                                    reported_flow_gpm=flow,reported_pressure_psi=pressure,source_member=member,
                                    source_sha256=sha,page=pn,table=ti,row_start=ri,row_end=ri,
                                    source_cells=json.dumps(cells[:9]),time_basis='Report-date calendar day; no finer drilling-parameter time printed'))
                                count+=1;section=False
                            elif section and any('Survey' in c or 'Inventory' in c for c in cells):section=False
            audit.append(dict(source_member=member,sha256=sha,parameter_intervals=count,
                status='parsed' if count else ('source explicitly states no drilling-parameter records' if explicit_none else 'no parsed drilling-parameter interval')))
            print(name,count,flush=True)
    write(output/'drilling-parameter-intervals.csv',rows);write(output/'parameter-parse-audit.csv',audit)


def pump_rows(source_dir, scratch, output):
    import csv
    rows=[]
    with (source_dir/'source-documents.csv').open(encoding='utf-8') as f:documents=list(csv.DictReader(f))
    for doc in documents:
        if doc['well']!='16A' or doc['status']!='searched':continue
        pages=json.loads((scratch/(doc['source_sha256']+'.json')).read_text())
        for pn,text in enumerate(pages,1):
            lines=text.splitlines()
            for j,line in enumerate(lines):
                if not line.startswith('PUMP MAKE MODEL LINER STK'):continue
                for k in range(j+1,min(len(lines),j+5)):
                    fields=lines[k].split()
                    if len(fields)<5 or not fields[0].isdigit():continue
                    try:liner=float(fields[3]);stroke=float(fields[4])
                    except ValueError:continue
                    rows.append(dict(classification='measured',well='16A',source_member=doc['source_member'],
                        source_sha256=doc['source_sha256'],page=pn,line_start=k+1,line_end=k+1,
                        pump=fields[0],make=fields[1],model=fields[2],liner_in=liner,stroke_in=stroke,
                        source_text=lines[k]))
    write(output/'16A-pump-records.csv',rows)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw58',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True);p.add_argument('--scratch',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    parameters(a.raw58,a.output);pump_rows(a.sources,a.scratch,a.output)
    manifest=dict(code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        output_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.output.glob('*.csv'))})
    (a.output/'report-table-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
