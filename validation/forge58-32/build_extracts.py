"""Extract 58-32 inputs and pressure availability; never emit target values.

Only 1006.zip is opened. Requires pdfplumber. Report component, survey,
mud and bit cells are whitelisted; all pressure/thermal observations stay out.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path


def num(s):
    try:
        x = float(str(s).replace(',', '').strip())
        return x if math.isfinite(x) and x != -999.25 else None
    except (ValueError, TypeError):
        return None


def save(root, name, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with (root/name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def dump(root, name, value):
    (root/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def day(s):
    return datetime.strptime(s[:9], '%d-%b-%y').date().isoformat()


def reports(top, root):
    import pdfplumber
    components, runs, mud, bits, surveys, operations, casing, sources = [], [], [], [], [], [], [], []
    codes = {'BIT','MMTR','BS','STAB','SHOCK','DCM','DC','JAR','XO','HWDP','RR','OTHER','MWD','DP','SUB'}
    with zipfile.ZipFile(io.BytesIO(top.read('DailyDrillingReports_Well58-32.zip'))) as z:
        for name in sorted(z.namelist()):
            if not name.lower().endswith('.pdf') or '__MACOSX' in name or 'Graphical' in name:
                continue
            data = z.read(name)
            source = '1006.zip!DailyDrillingReports_Well58-32.zip!'+name
            sources.append(dict(member=source, sha256=hashlib.sha256(data).hexdigest()))
            with pdfplumber.open(io.BytesIO(data)) as doc:
                report_date = ''
                for pn, page in enumerate(doc.pages, 1):
                    text = page.extract_text() or ''
                    match = re.search(r'Report For\s+(\d{2}-[A-Za-z]{3}-\d{2})', text)
                    if match:
                        report_date = day(match[1])
                    match = re.search(r'BHA\s*-?\s*(?:No\.?|#)\s*(\d+)', text)
                    page_bha = match[1] if match else None
                    report_count_before = len(runs)
                    # Whitelisted header geometry. No full page text is saved.
                    md = re.search(r'Measured Depth\s*\(ft\):\s*([\d,.]+)', text)
                    last_casing = re.search(r'Last Casing:\s*([\d.]+)\s+at\s+([\d,]+)', text)
                    if last_casing:
                        casing.append(dict(report_date=report_date, OD_in=num(last_casing[1]), shoe_ft=num(last_casing[2]), source_member=source, page=pn))
                    for obj in page.find_tables():
                        table = obj.extract()
                        bha = page_bha
                        for row in table:
                            joined = ' '.join(c or '' for c in row)
                            match = re.search(r'BHA\s*(?:-\s*No\.|#)\s*(\d+)', joined)
                            if match:
                                bha = match[1]
                        selected = []
                        for ri, row in enumerate(table):
                            cells = [str(c).strip() for c in row if c is not None]
                            # Survey and BHA share the page horizontally. Select only
                            # the component's adjacent Qty/OD/Item/Length cells.
                            if bha:
                                for ci, cell in enumerate(cells):
                                    if cell in codes and ci >= 2 and ci+1 < len(cells):
                                        qty, od, length = (num(cells[ci-2]), num(cells[ci-1]), num(cells[ci+1]))
                                        if qty is not None and od is not None and length is not None:
                                            record = dict(report_date=report_date, bha_id=bha, quantity=qty, OD_in=od,
                                                          component=cell, reported_length_ft=length,
                                                          passage_ID_in='', source_member=source, page=pn, table_row=ri)
                                            components.append(record)
                                            selected.append(record)
                            # Selected mud fields occupy the first five real cells.
                            if cells and re.match(r'\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:?\d{2}', cells[0]) and len(cells) >= 5:
                                stamp = re.match(r'(\d{2}-[A-Za-z]{3}-\d{2})\s+(\d{2}):?(\d{2})', cells[0])
                                mud.append(dict(report_date=report_date, sample_date=day(stamp[1]), sample_time=stamp[2]+':'+stamp[3],
                                                mud_weight_ppg=num(cells[1]), funnel_viscosity_s=num(cells[2]),
                                                plastic_viscosity_cP=num(cells[3]), yield_point_lbf_100ft2=num(cells[4]),
                                                rheology_measurement_temperature_C='', pv_ref_T_primary_C=48.9,
                                                pv_ref_T_sensitivity_C=26.7, source_member=source, page=pn))
                            # Bit details: retain only cells left of the performance block.
                            boxes = obj.rows[ri].cells
                            left = [(str(c).strip(), box) for c,box in zip(row,boxes) if c is not None and box and box[0] < 240]
                            if ri > 0 and len(left) >= 5 and num(left[0][0]) is not None:
                                prev = ' '.join(c or '' for c in table[ri-1])
                                if 'No/Run' in prev.replace(' ', '') or ('Make' in prev and 'Jets' in prev):
                                    bits.append(dict(report_date=report_date, input_cells=[c for c,b in left], source_member=source, page=pn))
                            # Input-only daily operations. Suppress mixed target descriptions.
                            if len(cells) >= 6 and re.fullmatch(r'\d{2}:?\d{2}', cells[0]) and re.fullmatch(r'\d{2}:?\d{2}', cells[1]):
                                desc = cells[5]
                                if re.search(r'pressure|\bpsi\b|\bSPP\b|\bkPa\b|\bMPa\b|temp|\d\s*[CF]\b|MRT',desc,re.I):
                                    desc = '[mixed observation description suppressed]'
                                operations.append(dict(report_date=report_date, start_hhmm=cells[0].replace(':',''), end_hhmm=cells[1].replace(':',''),
                                                       elapsed=cells[2], end_MD_ft=num(cells[3]), code=cells[4], description=desc, source_member=source, page=pn))
                        if selected:
                            runs.append(dict(report_date=report_date, bha_id=bha, report_MD_ft=num(md[1]) if md else '',
                                             motor='documented' if any(r['component']=='MMTR' for r in selected) else 'no_motor_in_reported_BHA',
                                             components=';'.join(r['component'] for r in selected), source_member=source, page=pn))
                    if page_bha and len(runs)==report_count_before:
                        # Early DDRs state the complete assembly as a single input
                        # line, without a component dimension table.
                        line=next((l for l in text.splitlines() if re.search(r'BHA\s*-?\s*No\.?\s*'+page_bha+r'\b',l)), '')
                        if line and not re.search(r'pressure|psi|temp',line,re.I):
                            listed=re.findall(r'\b(?:'+ '|'.join(sorted(codes,key=len,reverse=True))+r')\b',line)
                            runs.append(dict(report_date=report_date,bha_id=page_bha,report_MD_ft=num(md[1]) if md else '',
                                motor='documented' if 'MMTR' in listed else 'no_motor_in_reported_BHA',
                                components=';'.join(listed),source_member=source,page=pn))
    # A separate directional-survey PDF contains input geometry only.
    with zipfile.ZipFile(io.BytesIO(top.read('Directional_Survey_well_58_32.zip'))) as z:
        name = next(n for n in z.namelist() if 'DirectionalSurveyRpt' in n)
        data = z.read(name)
        sources.append(dict(member='1006.zip!Directional_Survey_well_58_32.zip!'+name, sha256=hashlib.sha256(data).hexdigest()))
        with pdfplumber.open(io.BytesIO(data)) as doc:
            for pn, page in enumerate(doc.pages, 1):
                for line in (page.extract_text() or '').splitlines():
                    values = line.split()
                    if values and values[0] in ('MSS','MMS','MWD','**TieIn') and len(values)>=5 and all(num(v) is not None for v in values[1:5]):
                        surveys.append(dict(source_page=pn,survey_type=values[0],MD_ft=num(values[1]),inclination_deg=num(values[2]),azimuth_deg=num(values[3]),TVD_ft=num(values[4])))
    for name, rows in [('bha_components.csv',components),('bha_reports.csv',runs),('mud_reports.csv',mud),('bit_inputs.csv',bits),
                       ('survey.csv',surveys),('operations.csv',operations),('casing_records.csv',casing)]:
        save(root,name,rows)
    dump(root,'source_reports.json',sources)
    return dict(BHA_reports=len(runs), components=len(components), mud_samples=len(mud), survey_rows=len(surveys), bits=len(bits))


def rig(top, root):
    inputs = {2:'hole_depth_ft',3:'block_height_ft',4:'bit_depth_ft',5:'rop_ft_h',10:'rpm',11:'pump1_spm',12:'pump2_spm',14:'flow_gpm',16:'inlet_temperature_source_degrees'}
    outputs, counts = [], []
    with zipfile.ZipFile(io.BytesIO(top.read('Pason_Logs.zip'))) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.csv') or '__MACOSX' in name:
                continue
            bins = {}
            finite = missing = raw_rows = excluded = 0
            with io.TextIOWrapper(z.open(name),encoding='utf-8-sig',newline='') as f:
                for line_no,row in enumerate(csv.reader(f),1):
                    if len(row)>18 and not any(s.strip() for s in row[18:]):
                        row=row[:18]
                    if len(row)!=18:
                        excluded+=1
                        continue
                    try:
                        stamp=datetime.strptime(row[0].strip()+' '+row[1].strip(),'%m/%d/%Y %H:%M:%S')
                    except ValueError:
                        excluded+=1
                        continue
                    raw_rows+=1
                    ok=num(row[8]) is not None
                    finite+=int(ok)
                    missing+=int(not ok)
                    stamp=stamp.replace(second=stamp.second//10*10)
                    b=bins.setdefault(stamp,dict(first=line_no,last=line_no,rows=0,values={k:[] for k in inputs.values()}))
                    b['last']=line_no
                    b['rows']+=1
                    for index,key in inputs.items():
                        x=num(row[index])
                        if key=='flow_gpm' and x is not None and not 0<=x<=2000:
                            x=None
                        if x is not None:
                            b['values'][key].append(x)
            for stamp,b in sorted(bins.items()):
                out=dict(time=stamp.isoformat(sep=' '),source_member='1006.zip!Pason_Logs.zip!'+name,
                         first_source_row=b['first'],last_source_row=b['last'],source_rows=b['rows'])
                for key,values in b['values'].items():
                    out[key]=math.fsum(values)/len(values) if values else ''
                    out[key+'_count']=len(values)
                    if key in ('hole_depth_ft','bit_depth_ft','flow_gpm'):
                        out[key+'_min']=min(values) if values else ''
                        out[key+'_max']=max(values) if values else ''
                outputs.append(out)
            counts.append(dict(source_member=name,raw_rows=raw_rows,input_bins_10s=len(bins),standpipe_finite=finite,standpipe_missing=missing,non_data_rows=excluded))
    outputs.sort(key=lambda r:r['time'])
    assert len({r['time'] for r in outputs})==len(outputs), 'Resolve overlapping daily input bins before proceeding'
    save(root,'rig_inputs_10s.csv',outputs)
    dump(root,'target_availability.json',counts)
    return dict(raw_rows=sum(r['raw_rows'] for r in counts),bins_10s=len(outputs),standpipe_finite=sum(r['standpipe_finite'] for r in counts))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    parser.add_argument('--skip-rig',action='store_true')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.raw/'1006.zip') as top:
        summary={'report_inputs':reports(top,args.output)}
        if not args.skip_rig:
            summary['rig']=rig(top,args.output)
        else:
            counts=json.loads((args.output/'target_availability.json').read_text())
            summary['rig']=dict(raw_rows=sum(r['raw_rows'] for r in counts),bins_10s=sum(r['input_bins_10s'] for r in counts),
                                standpipe_finite=sum(r['standpipe_finite'] for r in counts))
    summary['target_values_emitted']=False
    dump(args.output,'extract-summary.json',summary)
    print(json.dumps(summary,indent=2))
