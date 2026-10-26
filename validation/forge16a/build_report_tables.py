"""Transcribe ruled daily-report cells with a file/date/page locator."""
from pathlib import Path
import argparse,csv,hashlib,io,json,re,zipfile
import pdfplumber
HERE=Path(__file__).resolve().parent
def save(out,name,rows):
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (out/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def build(raw,out):
    seen=set();daily=[];components=[];bits=[];casings=[];events=[];audit=[]
    with zipfile.ZipFile(raw/'1283.zip') as z:
        for archive in ['16A(78)-32_Daily_Reports.zip','2021-well-16a78-32-daily-reports.zip']:
            with zipfile.ZipFile(io.BytesIO(z.read(archive))) as reports:
                for item in reports.infolist():
                    if not item.filename.lower().endswith('.pdf') or '__MACOSX' in item.filename:continue
                    data=reports.read(item);sha=hashlib.sha256(data).hexdigest()
                    if sha in seen:continue
                    seen.add(sha)
                    with pdfplumber.open(io.BytesIO(data)) as doc:
                        for pn,page in enumerate(doc.pages,1):
                            text=page.extract_text() or ''
                            date=re.search(r'RPT DATE:\s*(\d+/\d+/\d+)',text)
                            if not date:continue
                            date=date.group(1);locator=dict(report_date=date,archive=archive,member=item.filename,page=pn,sha256=sha)
                            # Retain contextual excerpts for losses/cooling/string evidence.
                            lines=text.splitlines()
                            for i,line in enumerate(lines):
                                if re.search(r'cooler|chill|lost|loss|drill.?pipe|sensor|top.?sub|bit.?box',line,re.I):
                                    events.append(dict(**locator,excerpt=' '.join(lines[max(0,i-1):min(len(lines),i+2)])))
                            desc=re.search(r'DESCRIPTION:\s*(.*?)(?:\n|LENGTH:)',text)
                            bha=re.search(r'\bBHA\s*#?\s*(\d+)',desc.group(1) if desc else '')
                            run=bha.group(1) if bha else ''
                            parsed=dict(**locator,BHA=run,description=desc.group(1).strip() if desc else '')
                            tables=page.extract_tables()
                            if not tables:continue
                            for table in tables:
                                section='';component_indices=None
                                for row in table:
                                    cells=[x for x in row if x is not None]
                                    if not cells:continue
                                    first=cells[0].strip()
                                    if len(cells)==1 and first in ['MUD','BHA','DRILL BITS','CASING','PUMPS','SURVEY DATA','CONSUMABLES','TIME BREAKDOWN']:
                                        section=first;continue
                                    if section=='MUD' and len(cells)==19 and re.fullmatch(r'\d{1,2}:\d\d',first):
                                        names=['mud_time','mud_weight_ppg','funnel_viscosity_s','water_loss_ml','pH','cake',
                                               'gel_10s','gel_10min','gel_30min','plastic_viscosity_cP','yield_point_lbf_100ft2',
                                               'chloride','K','Pf','Mf','Ca','oil','low_gravity_solids','HTHP']
                                        parsed.update(dict(zip(names,cells)))
                                    elif section=='DRILL BITS' and len(cells)==15 and re.fullmatch(r'\d+',first):
                                        names=['bit_number','size_in','manufacturer','type','serial','jets_32nds','TFA_in2','rerun','depth_in_ft','depth_out_ft','footage_ft','hours','WOB_klbf','rpm','ROP_ft_h']
                                        bits.append(dict(**locator,BHA=run,**dict(zip(names,cells))))
                                    elif section=='CASING' and len(cells)==6 and first in ['Conductor','Surface','Intermediate','Production']:
                                        casings.append(dict(**locator,**dict(zip(['type','OD_in','weight_lb_ft','grade','shoe_MD_ft','shoe_TVD_ft'],cells))))
                                    elif section=='BHA':
                                        if cells.count('COMPONENT')==2:
                                            component_indices=[i for i,x in enumerate(row) if x is not None]
                                        elif component_indices and len(cells)==10:
                                            vals=[row[i] for i in component_indices]
                                            for half in [vals[:5],vals[5:]]:
                                                if re.fullmatch(r'\d+',half[0] or ''):
                                                    component=dict(**locator,BHA=run,**dict(zip(['item','component','OD_in','ID_in','length_ft'],half)))
                                                    for field in ['OD_in','ID_in','length_ft']:
                                                        original=component[field]
                                                        if original and not re.fullmatch(r'\d+(?:\.\d+)?',original):
                                                            component[field+'_source_text']=original;component[field]=''
                                                    components.append(component)
                            daily.append(parsed)
                            audit.append(dict(**locator,BHA=run,table_count=len(tables),mud_parsed='mud_weight_ppg' in parsed))
                    print(date,run,flush=True)
    save(out,'daily_well_inputs.csv',daily);save(out,'bha_components.csv',components);save(out,'bit_records.csv',bits);save(out,'casing_records.csv',casings);save(out,'operating_notes.csv',events)
    (out/'report_extraction_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(dict(unique_PDFs=len(seen),dated_pages=len(daily),component_rows=len(components),bit_rows=len(bits),casing_rows=len(casings),note_rows=len(events)),indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--raw',required=True,type=Path);parser.add_argument('--output',type=Path,default=HERE);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);build(args.raw,args.output)
