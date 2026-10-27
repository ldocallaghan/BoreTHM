"""Build FORGE 56-32 input extracts and target availability counts.

Usage: python build_extracts.py --raw DOWNLOAD_FOLDER --output OUTPUT_FOLDER
Requires the standard library and pdfplumber for report tables. No BoreTHM
import, model calculation, target series or target-value summary is used.
The only raw download opened is 1295.zip. Large CSVs are streamed in place.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import zlib
from contextlib import contextmanager
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
INPUTS = {
    'hole_depth_ft': 'Hole Depth (feet)',
    'bit_depth_ft': 'Bit Depth (feet)',
    'flow_gpm': 'Total Pump Output (gal_per_min)',
    'rop_ft_h': 'On Bottom ROP (ft_per_hr)',
    'wob_klbf': 'Weight on Bit (klbs)',
    'rpm': 'Rotary RPM (RPM)',
    'block_height_ft': 'Block Height (feet)',
    'pump1_spm': 'Pump 1 strokes/min (SPM)',
    'pump2_spm': 'Pump 2 strokes/min (SPM)',
    'inlet_temperature_source_degrees': 'Temp IN (Degrees)',
}
TARGET_COUNTS = ('Standpipe Pressure (psi)', 'Differential Pressure (psi)',
                 'MWD Temp (Fahrenheit)', 'Temp OUT (Degrees)')


@contextmanager
def gzip_text(path):
    """Write UTF-8 CSV with a fixed gzip header for reproducible extracts."""
    with path.open('wb') as raw:
        with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as compressed:
            with io.TextIOWrapper(compressed,encoding='utf-8',newline='') as text:
                yield text


def record_rig_archive(root):
    path=root/'rig_inputs_10s.csv.gz'
    packed=path.read_bytes()
    unpacked=gzip.decompress(packed)
    dump(root,'rig-inputs.json',dict(file=path.name,sha256=hashlib.sha256(packed).hexdigest(),
        uncompressed_sha256=hashlib.sha256(unpacked).hexdigest(),
        compressed_bytes=len(packed),uncompressed_bytes=len(unpacked),
        compression='gzip; mtime=0; no embedded filename',zlib_version=zlib.ZLIB_RUNTIME_VERSION))


def number(value):
    try:
        x = float(str(value).replace(',', '').strip())
        return x if math.isfinite(x) and x != -999.25 else None
    except (TypeError, ValueError):
        return None


def dimension(value):
    """Decimal or explicit mixed fraction; unreadable text stays missing."""
    if value is None:
        return None
    value = str(value).strip().replace('"', '')
    if number(value) is not None:
        return number(value)
    m = re.fullmatch(r'(\d+)\s+(\d+/\d+)', value)
    if m:
        return int(m[1]) + float(Fraction(m[2]))
    if re.fullmatch(r'\d+/\d+', value):
        return float(Fraction(value))
    return None


def date(value):
    value=str(value).strip()
    match=re.match(r'(\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}|\d{2}-[A-Za-z]{3}-\d{2})',value)
    value=match[1] if match else value
    for fmt in ('%Y/%m/%d', '%m/%d/%Y', '%m/%d/%y', '%d-%b-%y'):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return ''


def write_csv(out, name, rows, fields=None):
    rows = list(rows)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row))
    with (out / name).open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows({k: v.strip() if isinstance(v, str) else v for k, v in row.items()} for row in rows)


def dump(out, name, value):
    (out / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8', newline='\n')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rig(top, out):
    counts = []; source_rows = []; fields = None; total_bins = 0
    with zipfile.ZipFile(io.BytesIO(top.read('56-32_Pason_Archive.zip'))) as z:
        with gzip_text(out / 'rig_inputs_10s.csv.gz') as dest:
            writer = None
            for name in sorted(n for n in z.namelist() if n.endswith('.csv') and '__MACOSX' not in n):
                raw_rows = 0; first = last = None; bucket = None; values = {}; bin_count = 0; invalid_flow = 0
                valid = {k: 0 for k in TARGET_COUNTS}

                def flush():
                    nonlocal writer, fields, total_bins, bin_count
                    if bucket is None:
                        return
                    row = dict(time=bucket.isoformat(sep=' '), member=name,
                               first_source_row=source_rows[0], last_source_row=source_rows[-1],
                               source_rows=len(source_rows))
                    for key in INPUTS:
                        vals = values[key]
                        row[key] = math.fsum(vals) / len(vals) if vals else ''
                        row[key + '_count'] = len(vals)
                        if key in ('flow_gpm', 'bit_depth_ft', 'hole_depth_ft'):
                            row[key + '_min'] = min(vals) if vals else ''
                            row[key + '_max'] = max(vals) if vals else ''
                    row['invalid_flow_count'] = invalid_flow
                    if writer is None:
                        fields = list(row)
                        writer = csv.DictWriter(dest, fields, lineterminator='\n'); writer.writeheader()
                    writer.writerow(row); total_bins += 1; bin_count += 1

                with io.TextIOWrapper(z.open(name), encoding='utf-8-sig', newline='') as f:
                    rr = csv.reader(f); header = next(rr)
                    positions = {key: header.index(col) for key, col in INPUTS.items()}
                    targets = {key: header.index(key) for key in TARGET_COUNTS}
                    di, ti = header.index('YYYY/MM/DD'), header.index('HH:MM:SS')
                    for source_row, row in enumerate(rr, 2):
                        if not row:
                            continue
                        if len(row) != len(header):
                            raise ValueError('Unexpected CSV width; target row suppressed')
                        t = datetime.strptime(row[di] + ' ' + row[ti], '%Y/%m/%d %H:%M:%S')
                        if last is not None and t < last:
                            raise ValueError('Non-monotonic input clock; review required')
                        raw_rows += 1; first = first or t; last = t
                        # Targets are parsed solely for finite/null counts. No value is saved.
                        for key, index in targets.items():
                            valid[key] += int(number(row[index]) is not None)
                        b = t.replace(second=t.second // 10 * 10)
                        if b != bucket:
                            flush(); bucket = b; values = {key: [] for key in INPUTS}; source_rows = []; invalid_flow = 0
                        source_rows.append(source_row)
                        for key, index in positions.items():
                            val = number(row[index])
                            if key == 'flow_gpm' and val is not None and not 0 <= val <= 2000:
                                invalid_flow += 1; val = None
                            if val is not None:
                                values[key].append(val)
                    flush()
                counts.append(dict(member=name, raw_rows=raw_rows, input_start=first.isoformat(sep=' '),
                                   input_end=last.isoformat(sep=' '), input_bins_10s=bin_count,
                                   targets=[dict(channel=k, finite=valid[k], missing=raw_rows-valid[k]) for k in TARGET_COUNTS]))
                print(name, 'input bins', bin_count, 'target counts only', flush=True)
    record_rig_archive(out)
    dump(out, 'target_availability.json', counts)
    return dict(raw_rows=sum(x['raw_rows'] for x in counts), bins_10s=total_bins)


def workbook_rows(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))] if 'xl/sharedStrings.xml' in z.namelist() else []
        root = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        for row in root.findall('.//m:sheetData/m:row', NS):
            cells = {}
            for cell in row.findall('m:c', NS):
                col = re.match('[A-Z]+', cell.get('r'))[0]
                v = cell.find('m:v', NS); text = v.text if v is not None else ''
                if cell.get('t') == 's' and text:
                    text = shared[int(text)]
                if cell.get('t') == 'inlineStr':
                    text = ''.join(cell.find('m:is', NS).itertext())
                cells[col] = text
            yield int(row.get('r')), cells


def report_inputs(top, out):
    import pdfplumber
    sources = []; bhas = []; components = []; bits = []; mud = []; casings = []; notes = []; audit = []; pipes = []; operations = []
    with zipfile.ZipFile(io.BytesIO(top.read('56-32 drill bit BHA data.zip'))) as tools:
        bit_name = 'Bit Record - FORGE 56-32.xlsx'; data = tools.read(bit_name)
        sources.append(dict(member='56-32 drill bit BHA data.zip!' + bit_name, sha256=digest(data)))
        for name in tools.namelist():
            if name.lower().endswith('.pdf'):
                sources.append(dict(member='56-32 drill bit BHA data.zip!'+name, sha256=digest(tools.read(name)), role='manufacturer_specification'))
        # All selected workbook columns are operational/geometric inputs.
        chosen = {'B': 'run_sequence', 'C': 'bit_size_in', 'D': 'bit_type', 'E': 'bit_serial', 'F': 'bit_maker',
                  'H': 'depth_in_ft', 'I': 'depth_out_ft', 'J': 'footage_ft',
                  'U': 'motor_size_in', 'V': 'motor_maker', 'W': 'steering_type',
                  'X': 'motor_bit_to_bend_in', 'Y': 'motor_lobes', 'Z': 'motor_stages',
                  'AA': 'motor_bend_degrees', 'AB': 'motor_rev_per_gal', 'AC': 'reported_flow_gpm',
                  'AD': 'TFA_in2', 'AE': 'mud_weight_ppg', 'AF': 'mud_type', 'AM': 'run_date_source'}
        for row_number, row in workbook_rows(data):
            if row_number == 1 or not row.get('B'):
                continue
            item = {key: row.get(col, '') for col, key in chosen.items()}
            item.update(source_member=bit_name, source_row=row_number)
            bits.append(item)
        with zipfile.ZipFile(io.BytesIO(tools.read('BHAs FORGE.zip'))) as z:
            for name in z.namelist():
                if name.lower().endswith('.pdf') and '/BHA #' not in name:
                    sources.append(dict(member='56-32 drill bit BHA data.zip!BHAs FORGE.zip!'+name, sha256=digest(z.read(name)), role='motor_sheet_not_pressure_data'))
            for name in sorted(n for n in z.namelist() if '/BHA #' in n and n.endswith('.pdf')):
                data = z.read(name); loc = '56-32 drill bit BHA data.zip!BHAs FORGE.zip!' + name
                sources.append(dict(member=loc, sha256=digest(data)))
                with pdfplumber.open(io.BytesIO(data)) as doc:
                    for pn, page in enumerate(doc.pages, 1):
                        for table in page.extract_tables():
                            if not table or not any('BHA #:' in (c or '') for row in table for c in row):
                                continue
                            header, dates, depths = table[0], table[1], table[2]
                            bha = dict(bha_sheet_id=header[6], hole_size_in=dimension(header[9]),
                                       motor_identifier_source=header[11], motor_OD_in=dimension(dates[11]),
                                       date_in_source=dates[6] or '', date_out_source=dates[9] or '',
                                       date_in=date(dates[6]), date_out=date(dates[9]),
                                       depth_in_ft=number(depths[6]), depth_out_ft=number(depths[9]),
                                       depth_out_source=depths[9] or '', footage_ft=number(depths[11]),
                                       source_member=loc, page=pn)
                            if not bha['date_in']:
                                match=re.search(r'Date In:\s*((?:\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}))',dates[5] or '')
                                if match:bha['date_in_source']=match[1];bha['date_in']=date(match[1])
                            bha['depth_out_status'] = 'reported' if bha['depth_out_ft'] is not None else 'unresolved_source_cell'
                            if bha['depth_out_ft'] is None and bha['depth_in_ft'] is not None and bha['footage_ft'] is not None:
                                bha['depth_out_derived_candidate_ft'] = bha['depth_in_ft'] + bha['footage_ft']
                            bhas.append(bha)
                            start = next(i for i, r in enumerate(table) if (r[0] or '') == 'Item')
                            for row in table[start + 1:]:
                                if not re.fullmatch(r'\d+', row[0] or '') or not row[1]:
                                    continue
                                component = dict(bha_sheet_id=header[6], item=row[0], description=row[1], vendor=row[3] or '', serial=row[4] or '',
                                                 stabilizer_OD_source=row[6] or '', OD_source=row[7] or '', ID_source=row[8] or '',
                                                 connection=row[9] or '', length_source=row[10] or '', cumulative_length_source=row[11] or '',
                                                 source_member=loc, page=pn)
                                for key, raw in [('OD_in', row[7]), ('ID_in', row[8]), ('length_ft', row[10]), ('stabilizer_OD_in', row[6])]:
                                    component[key] = dimension(raw)
                                component['input_flag'] = 'missing_or_unreadable_passage' if component['ID_in'] is None else ''
                                components.append(component)
    with zipfile.ZipFile(io.BytesIO(top.read('56-32 Daily Drilling Reports.zip'))) as z:
        for name in sorted(n for n in z.namelist() if n.endswith('.pdf') and '__MACOSX' not in n):
            data = z.read(name); loc = '56-32 Daily Drilling Reports.zip!' + name
            sources.append(dict(member=loc, sha256=digest(data)))
            with pdfplumber.open(io.BytesIO(data)) as doc:
                for pn, page in enumerate(doc.pages, 1):
                    text = page.extract_text() or ''
                    d = re.search(r'Report For\s*(\d{2}-[A-Za-z]{3}-\d{2})', text)
                    if not d:
                        continue
                    report_date = date(d[1]); tables = page.find_tables()
                    for table_obj in tables:
                        table = table_obj.extract()
                        for ri, row in enumerate(table):
                            joined = ' '.join(c or '' for c in row)
                            occupied=[c.strip() for c in row if c is not None]
                            if len(occupied)>=6 and re.fullmatch(r'\d{1,2}:\d{2}',occupied[0] or '') and re.fullmatch(r'\d{1,2}:\d{2}',occupied[1] or ''):
                                description=' '.join(occupied[5:])
                                safe=not re.search(r'psi|kPa|MPa|\bSPP\b|differential|press|temp|\bdeg[FC]\b',description,re.I)
                                ids=re.findall(r'\b(?:BHA|bit)\s*#?\s*(\d+)\b',description,re.I)
                                operations.append(dict(report_date=report_date,time_from=occupied[0],time_to=occupied[1],elapsed_hours=occupied[2],
                                                       end_MD_ft=occupied[3],code=occupied[4],description_input=description if safe else '',
                                                       description_status='input_excerpt' if safe else 'mixed_observation_text_suppressed',
                                                       trip_out=bool(re.search('pull|POOH|trip out',description,re.I)),trip_in=bool(re.search('ran in|run in|RIH|TIH',description,re.I)),
                                                       named_bit_or_BHA_ids=';'.join(ids),source_member=loc,page=pn))
                            if joined.strip() == 'Mud Information' and ri + 3 < len(table):
                                # Ruled cells retain fixed physical x intervals. Targets at Temp Out are never selected.
                                values_row = table[ri + 3]
                                boxes = table_obj.rows[ri + 3].cells
                                selected = {}
                                fields = {'mud_weight_ppg': (36,63), 'funnel_viscosity_s': (62,86), 'plastic_viscosity_cP': (85,104),
                                          'yield_point_lbf_100ft2': (103,124), 'gel_10s': (414,442), 'gel_10min': (441,469),
                                          'gel_30min': (468,496), 'report_inlet_F': (495,522)}
                                for key, (left, right) in fields.items():
                                    matches = [str(values_row[i] or '') for i, box in enumerate(boxes) if box and left <= (box[0]+box[2])/2 <= right]
                                    selected[key] = ' '.join(matches).strip()
                                sample = table[ri + 2][0] or ''
                                sm = re.search(r'(\d{2}-[A-Za-z]{3}-\d{2})\s+(\d{2}:\d{2})\s+at Depth\s+([\d,]+)', sample)
                                selected.update(report_date=report_date, sample_date=date(sm[1]) if sm else '', sample_time=sm[2] if sm else '',
                                                sample_depth_ft=number(sm[3]) if sm else '',
                                                rheology_measurement_temperature_C='', rheology_temperature_status='not_stated_in_selected_table',
                                                pv_ref_T_primary_C=48.9 if number(selected['plastic_viscosity_cP']) is not None else '',
                                                pv_ref_T_sensitivity_C=26.7 if number(selected['plastic_viscosity_cP']) is not None else '',
                                                pv_ref_T_basis='declared_assumption_not_verified_field_temperature', source_member=loc, page=pn)
                                mud.append(selected)
                            if joined.startswith('BHA -'):
                                m = re.search(r'BHA\s*-\s*No\.\s*(\d+)\s*-\s*(.*)', joined)
                                if m:
                                    notes.append(dict(report_date=report_date, kind='daily_BHA_description', identifier=m[1], description=m[2], source_member=loc, page=pn))
                            if joined.strip() == 'Casing/Tubular Information':
                                for cr in table[ri + 2:]:
                                    occupied = [c for c in cr if c is not None]
                                    if not occupied or not re.fullmatch(r'(FULL|LINER|OPEN|TIEBACK)', occupied[0] or '', re.I):
                                        break
                                    # This entire table is casing geometry/strength input, with no standpipe channel.
                                    names=['type','OD_in','top_MD_ft','top_TVD_ft','shoe_MD_ft','shoe_TVD_ft','hole_section','hole_diameter_in','weight_lb_ft','grade','LOT_ppg']
                                    casings.append(dict(report_date=report_date, **dict(zip(names,occupied)), source_member=loc, page=pn))
                            if 'Drill Pipe Inventory' in joined:
                                for pr in table[ri+2:ri+4]:
                                    occupied=[c for c in pr if c]
                                    if occupied and number(occupied[0]) is not None:
                                        pipes.append(dict(report_date=report_date,cells_json=json.dumps(occupied),source_member=loc,page=pn))
                    audit.append(dict(source_member=loc, page=pn, report_date=report_date, table_count=len(tables), target_cells_written=False))
    write_csv(out, 'bha_runs.csv', bhas)
    write_csv(out, 'bha_components.csv', components)
    write_csv(out, 'bit_records.csv', bits)
    write_csv(out, 'mud_reports.csv', mud)
    write_csv(out, 'casing_records.csv', casings)
    write_csv(out, 'operating_notes.csv', notes)
    write_csv(out, 'pipe_tallies.csv', pipes)
    write_csv(out, 'operations.csv', operations)
    dump(out, 'source_reports.json', sources)
    dump(out, 'report_extraction_audit.json', audit)
    return dict(bha_sheets=len(bhas), components=len(components), bits=len(bits), mud_samples=len(mud), casings=len(casings), daily_BHA_descriptions=len(notes))


def survey(top, out):
    member = '56-32 well_survey_final.csv'; archive = 'Well 56-32 trajectory survey data.zip'
    with zipfile.ZipFile(io.BytesIO(top.read(archive))) as z:
        data = z.read(member)
    rr = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
    header = rr[0]
    rows = [dict(source_row=i, **dict(zip(header, row))) for i, row in enumerate(rr[1:], 2) if row and any(row)]
    write_csv(out, 'survey.csv', rows)
    dump(out, 'survey-source.json', dict(member=archive+'!'+member, sha256=digest(data), columns=header, units='ft for depth; degrees for angles, source report convention'))
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE)
    parser.add_argument('--skip-rig', action='store_true', help='Reuse existing input history while rebuilding report inputs')
    args = parser.parse_args(); out = args.output; out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.raw/'1295.zip') as top:
        summary = dict(survey_stations=survey(top, out), report_inputs=report_inputs(top, out))
        if not args.skip_rig:
            summary['rig'] = rig(top, out)
        else:
            counts=json.loads((out/'target_availability.json').read_text())
            summary['rig']=dict(raw_rows=sum(r['raw_rows'] for r in counts),bins_10s=sum(r['input_bins_10s'] for r in counts))
    summary.update(model_imports=False, target_series_written=False, pressure_values_inspected=False)
    dump(out, 'extract-summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
