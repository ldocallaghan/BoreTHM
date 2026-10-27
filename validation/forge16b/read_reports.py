"""Transcribe ruled mud-report cells with page locators using pdfplumber."""
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

FIELDS=['density_ppg','funnel_viscosity_s','PV_cP','YP_lbf_100ft2','filtrate','cake','pH',
        'solids_percent','oil_percent','water_percent','sand','LGS','chloride','calcium','CaCl',
        'gel_10s','gel_10min','gel_30min','temp_in_F','temp_out_F','loss']


def save(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pdf',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    digest=hashlib.file_digest(a.pdf.open('rb'),'sha256').hexdigest()
    mud=[];notes=[];inventory=[];unparsed=[]
    with pdfplumber.open(a.pdf) as doc:
        for pn in range(199,334):
            page=doc.pages[pn-1];text=page.extract_text() or ''
            date=re.search(r'Report For\s+06:00\s*AM\s+(\d{1,2}-\w{3}-\d{2})',text)
            if not date:page.close();continue
            stamp=datetime.strptime(date[1],'%d-%b-%y').date().isoformat()
            if not '2023-04-29'<=stamp<='2023-06-19':page.close();continue
            locator=dict(report_date=stamp,source=a.pdf.name,page=pn,sha256=digest)
            bha=re.search(r'BHA - No\.\s*(\d+)\s*-\s*([^\n]+)',text)
            inventory.append(dict(**locator,BHA=bha[1] if bha else '',description=bha[2] if bha else ''))
            lines=text.splitlines()
            for i,line in enumerate(lines):
                if re.search(r'cooler|chiller|insulated|motor assist|no motor',line,re.I):
                    notes.append(dict(**locator,excerpt=' '.join(lines[max(0,i-1):i+2])))
            for table in page.extract_tables():
                section=False;sample=''
                for row in table:
                    cells=[c for c in row if c is not None]
                    if not cells:continue
                    first=cells[0].strip()
                    if first=='Mud Information':section=True;continue
                    if first=='Mud Consumables':section=False
                    if not section:continue
                    if re.match(r'\d{1,2}-\w{3}-\d{2}',first):sample=first
                    if re.fullmatch(r'\d+(?:\.\d+)?',first):
                        if len(cells)==21:
                            mud.append(dict(**locator,sample=sample,**dict(zip(FIELDS,cells))))
                        else:
                            unparsed.append(dict(**locator,cells=cells,sample=sample))
                            if len(cells)>=4:
                                mud.append(dict(**locator,sample=sample,partial_parse=True,
                                                **dict(zip(FIELDS[:4],cells[:4]))))
            page.close()
            if pn%20==0:print('EOW page',pn,flush=True)
    save(a.output/'mud_samples.csv',mud);save(a.output/'report_pages.csv',inventory)
    save(a.output/'operating_notes.csv',notes)
    (a.output/'report_parse_audit.json').write_text(json.dumps(dict(mud_rows=len(mud),pages=len(inventory),
        note_rows=len(notes),unparsed_mud_rows=unparsed,pdfplumber_version=pdfplumber.__version__),indent=2)+'\n')
    print('Mud rows',len(mud),'unparsed',len(unparsed),flush=True)


if __name__=='__main__':main()
