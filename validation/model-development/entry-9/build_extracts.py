"""Extract pressure-diagnosis observations from FORGE 16A and 16B.

No package calculation is imported. Selection uses time, flow and depths.
Pressure and temperature values never select a window or assign an assembly.
The downloaded ZIPs are read without altering them. Scratch is external.
"""
import argparse
from bisect import bisect_right
import collections
import csv
from datetime import datetime
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import statistics
import time
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FIELDS = ['source_row', 'time', 'excursion', 'bit_depth_ft', 'hole_depth_ft',
          'flow_gpm', 'spp_psi', 'reported_differential_psi', 'spm1', 'spm2',
          'spm3', 'spm_total', 'temp_in_F', 'temp_out_F', 'motor_channel']
NUMERIC = FIELDS[3:]
WINDOW_FIELDS = ['window_id', 'assembly', 'excursion', 'start', 'end', 'observations',
                 'source_row_first', 'source_row_last', 'assignment', 'motor',
                 'bit_range_ft', 'flow_range_gpm']
WINDOW_FIELDS += [field for name in NUMERIC for field in [name, name+'_count']]
B_COLS = dict(bit_depth_ft='Bit Depth (feet)', hole_depth_ft='Hole Depth (feet)',
              flow_gpm='Total Pump Output (gal_per_min)',
              spp_psi='Standpipe Pressure (psi)',
              reported_differential_psi='Differential Pressure (psi)',
              spm1='Pump 1 strokes/min (SPM)', spm2='Pump 2 strokes/min (SPM)',
              spm3='Pump 3 strokes/min (SPM)',
              spm_total='Pump Total Strokes Rate (SPM)',
              temp_in_F='TEMP IN MANIFOLD (DEGREES)',
              temp_out_F='TEMP OUT FLOW (DEGREES)', motor_channel='Mud Motor Used (unitless)')


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) and value != -999.25 else None
    except (TypeError, ValueError):
        return None


def read(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def gz_writer(path):
    # Fixed gzip metadata permits byte-for-byte rebuilding.
    raw = path.open('wb')
    packed = gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0)
    return raw, io.TextIOWrapper(packed, encoding='utf-8', newline='')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def displacement_summary(well, days):
    result = []
    for day, values in sorted(days.items()):
        quartiles = statistics.quantiles(values, n=4, method='inclusive') if len(values)>1 else values*3
        result.append(dict(well=well, date=day, rows=len(values),
                           median_gal_per_stroke=statistics.median(values),
                           q25_gal_per_stroke=quartiles[0], q75_gal_per_stroke=quartiles[2],
                           triplex_6in_12in_95percent=3*math.pi/4*6**2*12/231*.95,
                           triplex_5p5in_12in_95percent=3*math.pi/4*5.5**2*12/231*.95))
    return result


def report_assignment(stamp, bit, hole, intervals):
    matches = [r for r in intervals if r['start'] <= stamp < r['end']
               and abs(hole-float(r['reported_hole_ft'])) <= 20]
    if len(matches) == 1:
        return matches[0]['assembly'], matches[0]['status']
    return '', 'unresolved shallow visit or excursion'


def report_starts(intervals):
    """Separate equipment changes identified in the operation reports."""
    return sorted({r['start'] for r in intervals
                   if r['status'] == 'reported incoming assembly'})


def annotate_b(path, assignments, scratch):
    mapping = {str(r['excursion']): r['assembly'] for r in assignments}
    intervals = read(HERE/'16b-assembly-intervals.csv')
    target = scratch/'pressure-16b-assigned.csv.gz'
    raw, text = gz_writer(target)
    try:
        writer = csv.DictWriter(text, fieldnames=['assembly','assignment',*FIELDS], lineterminator='\n')
        writer.writeheader()
        with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                bit, hole = float(row['bit_depth_ft']), float(row['hole_depth_ft'])
                assembly, status = report_assignment(row['time'], bit, hole, intervals)
                if not assembly and bit > 1000:
                    assembly = mapping.get(row['excursion'], '')
                    status = 'unique drilling-depth anchor' if assembly else status
                writer.writerow(dict(assembly=assembly, assignment=status, **row))
    finally:
        text.close();raw.close()
    target.replace(path)


def select_b(raw, scratch, output):
    definitions = read(ROOT/'validation/forge16b/run_definitions.csv')
    intervals = [(r['eow_bha'], float(r['depth_in_ft']), float(r['depth_out_ft'])) for r in definitions]
    records = {}
    packed_path = output/'16b-observations.csv.gz'
    counters = collections.Counter()
    trip = 0
    at_surface = False
    seen_below = False
    previous_time = None
    previous_report_segment = None
    reported = read(HERE/'16b-assembly-intervals.csv')
    boundaries = report_starts(reported)
    not_before = {r['assembly']: r['start'] for r in reported
                  if r['status'] == 'reported incoming assembly'}
    deepest_drilling = 0.
    with zipfile.ZipFile(raw/'1516.zip') as outer:
        member = outer.getinfo('16B_Pason.zip')
        nested = scratch/'16B_Pason.zip'
        if not nested.exists():
            with outer.open(member) as src, nested.open('wb') as dst:
                import shutil
                shutil.copyfileobj(src, dst)
        if nested.stat().st_size != member.file_size:
            raise ValueError('16B nested archive size differs from downloaded member')
    # Verify the reusable nested archive against the published source manifest.
    expected = json.loads((ROOT/'validation/forge16b/source_manifest.json').read_text(encoding='utf-8'))
    saved = next(m['sha256'] for m in expected['members'] if m['name'] == '16B_Pason.zip')
    if digest(nested) != saved:
        raise ValueError('16B nested archive digest differs from archived source manifest')
    raw_file, destination = gz_writer(packed_path)
    try:
        writer = csv.DictWriter(destination, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        with zipfile.ZipFile(nested) as z:
            with io.TextIOWrapper(z.open('10 Second Data.csv'), encoding='utf-8-sig', newline='') as stream:
                reader = csv.reader(stream)
                header = next(reader)
                indices = {key: header.index(value) for key, value in B_COLS.items()}
                for index, cells in enumerate(reader, 2):
                    counters['source_rows'] += 1
                    if len(cells) != len(header):
                        raise ValueError(f'Unexpected 16B field count at row {index}')
                    stamp = cells[0].replace('/', '-')+' '+cells[1]
                    moment = datetime.fromisoformat(stamp)
                    if previous_time is not None and moment <= previous_time:
                        raise ValueError(f'Non-increasing 16B source clock at row {index}')
                    previous_time = moment
                    row = {key: number(cells[i]) for key, i in indices.items()}
                    bit, hole, flow = (row[k] for k in ['bit_depth_ft', 'hole_depth_ft', 'flow_gpm'])
                    if bit is None or hole is None or not 0 <= bit <= hole+10 or not 0 < hole <= 12000:
                        counters['invalid_depth_rows'] += 1
                        continue
                    report_segment = bisect_right(boundaries, stamp)
                    if previous_report_segment is not None and report_segment != previous_report_segment:
                        trip += 1
                        at_surface = False
                        seen_below = True
                    previous_report_segment = report_segment
                    if bit <= 1000:
                        at_surface = True
                    else:
                        if at_surface or not seen_below:
                            trip += 1
                            at_surface = False
                            seen_below = True
                    record = records.setdefault(trip, dict(first=stamp, last=stamp, candidates=set(),
                                                          minimum_bit_ft=bit, maximum_bit_ft=bit, rows=0))
                    record['last'] = stamp
                    record['rows'] += 1
                    record['minimum_bit_ft'] = min(record['minimum_bit_ft'], bit)
                    record['maximum_bit_ft'] = max(record['maximum_bit_ft'], bit)
                    if (flow is not None and 100 < flow <= 2000 and abs(bit-hole) <= 5
                            and hole > deepest_drilling):
                        deepest_drilling = hole
                        for bha, low, high in intervals:
                            if low+5 < hole < high-5 and stamp >= not_before.get(bha, ''):
                                record['candidates'].add(bha)
                    row.update(source_row=index, time=stamp, excursion=trip)
                    writer.writerow(row)
                    if index % 100000 == 0:
                        print('16B source rows:', index, flush=True)
    finally:
        destination.close()
        raw_file.close()
    assignments = []
    for key, record in records.items():
        choices = sorted(record.pop('candidates'), key=int)
        assignments.append(dict(excursion=key, assembly=choices[0] if len(choices) == 1 else '',
                                candidates=';'.join(choices), assignment='unique drilling-depth anchor'
                                if len(choices) == 1 else 'unresolved', **record))
    write(output/'16b-excursions.csv', assignments)
    return packed_path, assignments, dict(counters)


def select_a(raw, output):
    # The standard export's Bit Depth column is blank. Do not relabel its
    # hole-depth channel as bit depth. Sanvean supplies measured bit depth
    # only during its actual recording periods.
    source_name = '16A(78)-32_time_data_10s_intervals.csv'
    bins = {}
    counters = collections.Counter()
    ratios = collections.defaultdict(list)
    with zipfile.ZipFile(raw/'1283.zip') as z:
        with io.TextIOWrapper(z.open(source_name), encoding='utf-8-sig', newline='') as stream:
            for index, row in enumerate(csv.DictReader(stream), 2):
                if not row.get('Time'):
                    continue
                counters['source_rows'] += 1
                key = datetime.strptime(row['Time'], '%m/%d/%y %H:%M').isoformat(sep=' ')
                record = bins.setdefault(key, collections.defaultdict(list))
                record['rows'].append(index)
                flow, strokes = number(row.get('Flow In')), number(row.get('SPM Total'))
                if flow is not None and strokes is not None and 100<flow<=2000 and 0<strokes<=500:
                    ratios[key[:10]].append(flow/strokes)
                for key, column in [('spp_psi', 'Pump Pressure'), ('flow_gpm', 'Flow In'),
                                    ('spm_total', 'SPM Total'), ('temp_out_F', 'MUD TEMP'),
                                    ('reported_differential_psi', 'Differential Pressure')]:
                    value = number(row.get(column))
                    if value is not None:
                        record[key].append(value)
    raw_file, destination = gz_writer(output/'16a-observations.csv.gz')
    coverage = []
    try:
        writer = csv.DictWriter(destination, fieldnames=['assembly', 'rig_source_row_first',
                                 'rig_source_row_last', *FIELDS], lineterminator='\n')
        writer.writeheader()
        for source in sorted((ROOT/'validation/forge16a').glob('sanvean_BHA*_10s.csv')):
            assembly = source.stem.removeprefix('sanvean_BHA').removesuffix('_10s')
            depths = []
            matched = 0
            for index, row in enumerate(read(source), 2):
                stamp = row['time']
                rig = bins.get(stamp[:16]+':00')
                bit = number(row['bit_depth_ft'])
                hole = number(row['hole_depth_ft'])
                flow = number(row['flow_gpm'])
                if bit is None or hole is None or not 0 <= bit <= hole+10 or not 0 < hole <= 12000:
                    continue
                depths.append(bit)
                values = {key: '' for key in FIELDS}
                values.update(source_row=index, time=stamp, excursion=assembly,
                              bit_depth_ft=bit, hole_depth_ft=hole, flow_gpm=flow,
                              reported_differential_psi=number(row.get('motor_differential_psi')))
                first = last = ''
                if rig:
                    matched += 1
                    first, last = min(rig['rows']), max(rig['rows'])
                    for key in ['spp_psi', 'spm_total', 'temp_out_F']:
                        if rig[key]:
                            values[key] = statistics.fmean(rig[key])
                writer.writerow(dict(assembly=assembly, rig_source_row_first=first,
                                     rig_source_row_last=last, **values))
            coverage.append(dict(assembly=assembly, source=source.name, rows=len(depths),
                                 rig_matched_rows=matched, minimum_bit_ft=min(depths) if depths else '',
                                 maximum_bit_ft=max(depths) if depths else '',
                                 shallow_coverage='unavailable', inlet_channel='unavailable',
                                 return_channel='rig MUD TEMP; channel identity inferred in original archive'))
    finally:
        destination.close()
        raw_file.close()
    write(output/'16a-source-coverage.csv', coverage)
    write(output/'16a-pump-displacement.csv', displacement_summary('16A', ratios))
    return output/'16a-observations.csv.gz', dict(counters)


def b_displacement(path, output):
    ratios = collections.defaultdict(list)
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            flow = number(row['flow_gpm'])
            individual = [number(row[k]) for k in ['spm1','spm2','spm3']]
            if any(value is None for value in individual):
                continue
            strokes = sum(individual)
            if flow is not None and 100<flow<=2000 and 0<strokes<=500:
                ratios[row['time'][:10]].append(flow/strokes)
    write(output/'16b-pump-displacement.csv', displacement_summary('16B', ratios))


def audit_a_channels(raw, output):
    rows = []
    channels = ['Bit Depth', 'Measured while Drilling Tool Depth',
                'Depth Hole Total Vertical Depth', 'Pump Pressure', 'Mud Temperature']
    with zipfile.ZipFile(raw/'1283.zip') as archive:
        for cadence in ['10s', '1s']:
            member = f'16A(78)-32_time_data_{cadence}_intervals_standard.csv'
            count = collections.Counter()
            total = 0
            with io.TextIOWrapper(archive.open(member), encoding='utf-8-sig', newline='') as stream:
                reader = csv.reader(stream)
                header = next(reader)
                next(reader)  # Units line.
                indices = {name: header.index(name) for name in channels}
                for cells in reader:
                    total += 1
                    for name, index in indices.items():
                        if number(cells[index]) is not None:
                            count[name] += 1
                    if total % 1000000 == 0:
                        print('16A channel audit:', cadence, total, flush=True)
            for name in channels:
                rows.append(dict(archive='1283.zip', member=member, channel=name,
                                 data_rows=total, nonnull_rows=count[name],
                                 member_crc32=f'{archive.getinfo(member).CRC:08x}'))
    write(output/'16a-channel-coverage.csv', rows)


def steady(path, well, assignments, output):
    assignment = {str(r['excursion']): r['assembly'] for r in assignments}
    motors = {r['eow_bha']: r['motor'] for r in read(ROOT/'validation/forge16b/run_definitions.csv')}
    a_motors = {r['BHA'] for r in read(ROOT/'validation/forge16a/bha_components.csv')
                if 'motor' in r['component'].lower()}
    windows, excluded = [], collections.Counter()
    bucket, key = [], None
    settled_since, previous_q, previous_t = None, None, None

    def finish():
        if not bucket:
            return
        # A complete two-minute bin contains twelve 10-second observations.
        if len(bucket) != 12:
            excluded['incomplete two-minute bin'] += 1
            return
        ids = {r['excursion'] for r in bucket}
        if len(ids) != 1:
            excluded['excursion boundary'] += 1
            return
        assembly = assignment.get(next(iter(ids)), '') if well == '16B' else bucket[0]['assembly']
        numbers = {name: [number(r.get(name)) for r in bucket] for name in NUMERIC}
        for name in ['bit_depth_ft', 'hole_depth_ft', 'flow_gpm']:
            if any(v is None for v in numbers[name]):
                excluded['missing flow or depth'] += 1
                return
        q, b, h = (numbers[k] for k in ['flow_gpm', 'bit_depth_ft', 'hole_depth_ft'])
        if not all(100 < v <= 2000 for v in q):
            excluded['outside circulation flow range'] += 1
            return
        if not all(row['_settled'] for row in bucket):
            excluded['less than 30 seconds after flow start or step'] += 1
            return
        if max(q)-min(q) > .05*statistics.fmean(q):
            excluded['flow range above five percent'] += 1
            return
        if max(b)-min(b) > 5:
            excluded['bit moves more than five feet'] += 1
            return
        if not all(hole-bit >= 10 for hole, bit in zip(h, b)):
            excluded['less than ten feet off bottom'] += 1
            return
        status = 'documented recording period'
        if well == '16B':
            labels = {r.get('assembly', '') for r in bucket}
            if all('assignment' in r for r in bucket):
                assembly = next(iter(labels)) if len(labels) == 1 else ''
                if any(r['assignment']=='report sequence inferred' for r in bucket):
                    status = 'report sequence inferred'
                elif len({r['assignment'] for r in bucket}) == 1:
                    status = bucket[0]['assignment']
                else:
                    status = 'mixed input assignment; unresolved'
                    assembly = ''
            elif min(b) <= 1000:
                assembly = ''
                status = 'unresolved shallow visit or excursion'
            else:
                status = 'unique drilling-depth anchor' if assembly else 'unresolved shallow visit or excursion'
        result = dict(window_id=f'{well}-{len(windows)+1:05d}', assembly=assembly,
                      excursion=bucket[0]['excursion'], start=bucket[0]['time'], end=bucket[-1]['time'],
                      observations=len(bucket), source_row_first=bucket[0]['source_row'],
                      source_row_last=bucket[-1]['source_row'],
                      assignment=status,
                      motor=('yes' if assembly.removesuffix('r1').removesuffix('r2') in a_motors
                             else 'unknown') if well == '16A' else motors.get(assembly, 'unknown'),
                      bit_range_ft=max(b)-min(b), flow_range_gpm=max(q)-min(q))
        for name, values in numbers.items():
            present = [v for v in values if v is not None]
            result[name] = statistics.fmean(present) if present else ''
            result[name+'_count'] = len(present)
        windows.append(result)

    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream):
            stamp = datetime.fromisoformat(row['time'])
            q = number(row['flow_gpm'])
            # Reset on time gaps, pump starts, or a greater than 5%/20-gpm step.
            if (previous_t is None or (stamp-previous_t).total_seconds() > 15 or
                    q is None or previous_q is None or q <= 100 or previous_q <= 100 or
                    abs(q-previous_q) > max(20., .05*previous_q)):
                settled_since = stamp
            row['_settled'] = (stamp-settled_since).total_seconds() >= 30
            next_key = (row['excursion'], stamp.replace(minute=(stamp.minute//2)*2, second=0))
            if key != next_key:
                finish()
                bucket = []
                key = next_key
            bucket.append(row)
            previous_q, previous_t = q, stamp
        finish()
    write(output/f'{well.lower()}-steady-windows.csv', windows, WINDOW_FIELDS)
    groups = collections.defaultdict(list)
    for row in windows:
        groups[row['assembly']].append(row)
    summaries = []
    expected = ([r['run'] for r in read(ROOT/'validation/forge16a/run_inputs.csv')] if well == '16A'
                else [r['eow_bha'] for r in read(ROOT/'validation/forge16b/run_definitions.csv')])
    for assembly in [*expected, '']:
        rows = groups[assembly]
        summaries.append(dict(well=well, assembly=assembly, windows=len(rows),
                              excursions=len({r['excursion'] for r in rows}),
                              minimum_bit_ft=min((r['bit_depth_ft'] for r in rows), default=''),
                              maximum_bit_ft=max((r['bit_depth_ft'] for r in rows), default=''),
                              near_surface_windows=sum(r['bit_depth_ft'] <= 500 for r in rows),
                              report_sequence_inferred_windows=sum(r['assignment']=='report sequence inferred' for r in rows),
                              inlet_windows=sum(r['temp_in_F_count'] == 12 for r in rows),
                              return_windows=sum(r['temp_out_F_count'] == 12 for r in rows),
                              pressure_windows=sum(r['spp_psi_count'] == 12 for r in rows)))
    return summaries, dict(excluded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE/'inputs')
    args = parser.parse_args()
    args.scratch.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.scratch.resolve().is_relative_to(ROOT):
        parser.error('Scratch must be outside the repository')
    start = time.perf_counter()
    b, assignments, b_counts = select_b(args.raw, args.scratch, args.output)
    annotate_b(b, assignments, args.scratch)
    a, a_counts = select_a(args.raw, args.output)
    audit_a_channels(args.raw, args.output)
    b_displacement(b, args.output)
    a_summary, a_excluded = steady(a, '16A', [], args.output)
    b_summary, b_excluded = steady(b, '16B', assignments, args.output)
    write(args.output/'coverage.csv', a_summary+b_summary)
    metadata = dict(baseline='a0819322610b772a259a2c48a8050495e6e43fd6',
                    sources={'16A': a_counts, '16B': b_counts},
                    excluded_bins={'16A': a_excluded, '16B': b_excluded},
                    source_archives={name: digest(args.raw/name) for name in ['1283.zip', '1516.zip']},
                    build_sha256=digest(Path(__file__)),
                    input_files_sha256={p.relative_to(ROOT).as_posix(): digest(p) for p in [
                        HERE/'16b-assembly-intervals.csv',
                        ROOT/'validation/forge16b/run_definitions.csv',
                        ROOT/'validation/forge16b/source_manifest.json',
                        ROOT/'validation/forge16a/bha_components.csv',
                        ROOT/'validation/forge16a/run_inputs.csv',
                        *sorted((ROOT/'validation/forge16a').glob('sanvean_BHA*_10s.csv'))]},
                    files_sha256={p.name: digest(p) for p in sorted(args.output.iterdir()) if p.suffix != '.json'},
                    limitations=['16A bit depth comes from recorded Sanvean periods only; shallow trips unavailable',
                                 '16A inlet temperature unavailable; rig MUD TEMP carried as a return proxy',
                                 '16A rig pressure and pump strokes have minute timestamps; joined by minute',
                                 '16B excursions split at recorded visits to 1000 ft or shallower and reported incoming-assembly starts',
                                 '16B assignment requires exactly one new-drilling-depth anchor assembly and cannot precede its reported incoming-equipment start',
                                 '16B shallow windows require a cited report interval; mixed-operation inferences are labelled separately'])
    (args.output/'manifest.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(coverage=a_summary+b_summary, elapsed_seconds=time.perf_counter()-start), indent=2), flush=True)


if __name__ == '__main__':
    main()
