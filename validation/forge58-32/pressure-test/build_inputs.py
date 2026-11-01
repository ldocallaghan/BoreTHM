"""Build the registered 58-32 pressure-test inputs without opening targets.

The existing target-free rig projection supplies the clock and inlet values.
Figure 14's manual transcription supplies the missing BHA dimensions. An
optional raw-archive check hashes only the end-of-well source PDF. This script
does not import BoreTHM, access raw Pason files or calculate a model output.
"""
import argparse
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import statistics as st
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
DATA = HERE.parent
ROOT = HERE.parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    with (DATA / name).open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def dump(path, value):
    path.write_bytes((json.dumps(value, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def write(path, rows):
    rows = list(rows)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    data = buffer.getvalue().encode('utf-8')
    if path.suffix == '.gz':
        with path.open('wb') as raw:
            with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as zipped:
                zipped.write(data)
    else:
        path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'inputs')
    parser.add_argument('--raw', type=Path, help='Optional directory containing 1006.zip for the source-PDF hash check')
    args = parser.parse_args()
    output = args.output
    if output.exists() and any(output.iterdir()):
        parser.error('Choose an empty output directory')
    protocol = json.loads((HERE / 'protocol.json').read_text(encoding='utf-8'))
    figure = json.loads((HERE / 'bha2-figure14.json').read_text(encoding='utf-8'))
    for name, expected in protocol['input_sha256'].items():
        if sha((DATA / name).read_bytes()) != expected:
            raise ValueError('Registered input has changed: ' + name)
    if args.raw:
        with zipfile.ZipFile(args.raw / '1006.zip') as top:
            with zipfile.ZipFile(io.BytesIO(top.read('58-32_EOWR.zip'))) as nested:
                source = nested.read('58-32_EOWR/58-32_EOWR_DOE.pdf')
        if sha(source) != figure['source_pdf_sha256']:
            raise ValueError('Figure source PDF has changed')
    candidates = read('off_bottom_windows.csv')
    selected = [r for r in candidates if r['selection'] == 'motorless_primary']
    if {r['bha_id'] for r in selected} != {'2'}:
        raise ValueError('The registered motorless cohort has changed')
    needed = {}
    for row in selected:
        start = datetime.fromisoformat(row['window_start'])
        for index in range(6):
            stamp = (start + timedelta(seconds=10 * index)).isoformat(sep=' ')
            if stamp in needed:
                raise ValueError('Overlapping registered windows')
            needed[stamp] = row['window_id']
    last = max(r['window_end'] for r in selected)
    packed = (DATA / 'rig_inputs_10s.csv.gz').read_bytes()
    raw = gzip.decompress(packed)
    metadata = json.loads((DATA / 'rig-inputs.json').read_text())
    if sha(raw) != metadata['uncompressed_sha256']:
        raise ValueError('Uncompressed input bytes differ')
    # Exact whitelist: a later target column cannot enter this projection.
    fixed = {'time', 'source_member', 'first_source_row', 'last_source_row', 'source_rows'}
    values = {'hole_depth_ft', 'block_height_ft', 'bit_depth_ft', 'rop_ft_h', 'rpm',
              'pump1_spm', 'pump2_spm', 'flow_gpm', 'inlet_temperature_source_degrees'}
    allowed = fixed | values | {v + '_count' for v in values}
    allowed |= {v + suffix for v in ('hole_depth_ft', 'bit_depth_ft', 'flow_gpm')
                for suffix in ('_min', '_max')}
    stream = csv.DictReader(io.StringIO(raw.decode('utf-8'), newline=''))
    if set(stream.fieldnames) != allowed:
        raise ValueError('Unexpected input projection columns')
    bins, clock = {}, []
    circulating, depth, previous = 0., 0., None
    history_gaps = 0
    for row in stream:
        stamp = row['time']
        if stamp >= last:
            break
        t = datetime.fromisoformat(stamp)
        if previous is not None and (t - previous).total_seconds() != 10:
            history_gaps += 1
        q, d = number(row['flow_gpm']), number(row['hole_depth_ft'])
        if d is not None and int(row['hole_depth_ft_count']) >= 8:
            depth = max(depth, d)
        if q is not None and q > 100 and int(row['flow_gpm_count']) >= 8:
            circulating += 10.
        clock.append(dict(time=stamp, cumulative_circulating_s=circulating,
                          monotone_hole_depth_ft=depth))
        if stamp in needed:
            bins[stamp] = {**row, 'cumulative_circulating_s': circulating,
                           'monotone_hole_depth_ft': depth}
        previous = t
    if set(bins) != set(needed):
        raise ValueError('A registered input bin is absent')
    mud = []
    system = protocol['fluid_system']
    for index, row in enumerate(read('mud_reports.csv'), 1):
        stamp = row['sample_date'] + ' ' + row['sample_time'] + ':00'
        if system['start'] <= stamp <= system['end']:
            mud.append({**row, 'sample_stamp': stamp, 'input_row': index})
    if not mud:
        raise ValueError('No mud measurement in the declared fluid section')
    rows, locators = [], []
    for row in selected:
        start = datetime.fromisoformat(row['window_start'])
        group = [bins[(start + timedelta(seconds=10*i)).isoformat(sep=' ')] for i in range(6)]
        when = datetime.fromisoformat(row['time'])
        complete = all(number(r['inlet_temperature_source_degrees']) is not None
                       and int(r['inlet_temperature_source_degrees_count']) >= 8 for r in group)
        closest = lambda pool: min(pool, key=lambda r: (abs((datetime.fromisoformat(r['sample_stamp']) - when).total_seconds()), r['sample_stamp']))
        density = closest([r for r in mud if number(r['mud_weight_ppg']) is not None])
        rheology = closest([r for r in mud if number(r['plastic_viscosity_cP']) is not None
                           and number(r['yield_point_lbf_100ft2']) is not None])
        inlet = math.fsum(number(r['inlet_temperature_source_degrees']) for r in group)/6 if complete else None
        if not figure['date_in'] <= row['time'] <= figure['date_out']:
            raise ValueError('A window lies outside the diagram BHA dates')
        out = {k: row[k] for k in ('window_id', 'event_id', 'bha_id', 'time', 'window_start',
               'window_end', 'flow_gpm', 'flow_min_gpm', 'flow_max_gpm', 'bit_depth_ft', 'hole_depth_ft')}
        out.update(input_bins=6, inlet_min_native_count=min(int(r['inlet_temperature_source_degrees_count']) for r in group),
            inlet_source_degrees=inlet, inlet_C=None if inlet is None else (inlet-32)/1.8,
            inlet_unit_basis='Fahrenheit, transferred DDR convention; raw Degrees label ambiguous',
            density_ppg=number(density['mud_weight_ppg']), density_source_row=density['input_row'],
            density_source_time=density['sample_stamp'], pv_cP=number(rheology['plastic_viscosity_cP']),
            yp_lbf_100ft2=number(rheology['yield_point_lbf_100ft2']), rheology_source_row=rheology['input_row'],
            rheology_source_time=rheology['sample_stamp'], pv_ref_T_C=26.7,
            rheology_time_offset_h=(datetime.fromisoformat(rheology['sample_stamp'])-when).total_seconds()/3600,
            fluid_system=system['id'], qualification='ready_with_declared_assumptions' if complete else 'missing_inlet',
            installed_pipe_geometry_confirmed=False, window_pressure_targets_read=False)
        rows.append(out)
        for r in group:
            locators.append(dict(window_id=row['window_id'], bin_time=r['time'], source_member=r['source_member'],
                first_source_row=r['first_source_row'], last_source_row=r['last_source_row'],
                source_rows=r['source_rows'], inlet_native_count=r['inlet_temperature_source_degrees_count']))
    daily = [r for r in read('bha_components.csv') if r['bha_id'] == '2' and r['report_date'] == '2017-08-05']
    if len(daily) != 11:
        raise ValueError('Expected eleven printed daily-summary BHA rows')
    components = []
    for item in figure['components']:
        i = item['item']
        exact = daily[i-1] if i <= 11 else None
        if exact and exact['component'] != item['component']:
            raise ValueError('Component order differs between sources')
        length = Decimal(exact['reported_length_ft'] if exact else str(item['figure_length_ft']))
        components.append(dict(item=i, component=item['component'], quantity=item['quantity'],
            total_length_ft=str(length), length_basis=item['length_basis'],
            length_source=exact['source_member'] + ':p1' if exact else figure['source_member'] + ':p29:fig14',
            reported_OD_in=number(exact['OD_in']) if exact else item['reported_OD_in'],
            reported_ID_in=item['reported_ID_in'], ID_source=figure['source_member'] + ':p29:fig14',
            reported_top_thread=item['reported_top_thread'],
            role='nozzle_boundary_only' if i == 1 else 'uniform_gauge_envelope_assumed' if item['component'] == 'STAB' else 'HWDP' if i == 17 else 'serial_passage',
            additional_tool_loss='unknown' if item['component'] in ('JAR', 'SHOCK') else 'none_added'))
    events = []
    for event in dict.fromkeys(r['event_id'] for r in rows):
        group = [r for r in rows if r['event_id'] == event]
        events.append(dict(event_id=event, bha_id='2', windows=len(group),
            ready_windows=sum(r['qualification'] == 'ready_with_declared_assumptions' for r in group),
            first_window=group[0]['window_start'], last_window=group[-1]['window_end'],
            bit_depth_min_ft=min(float(r['bit_depth_ft']) for r in group),
            bit_depth_max_ft=max(float(r['bit_depth_ft']) for r in group),
            flow_min_gpm=min(float(r['flow_gpm']) for r in group),
            flow_max_gpm=max(float(r['flow_gpm']) for r in group)))
    output.mkdir(parents=True, exist_ok=True)
    write(output/'windows.csv', rows)
    write(output/'source-bins.csv', locators)
    write(output/'events.csv', events)
    write(output/'components.csv', components)
    write(output/'circulation-clock.csv.gz', clock)
    total = sum(Decimal(c['total_length_ft']) for c in components)
    dump(output/'geometry.json', dict(reported_total_length_ft=figure['reported_assembly_length_ft'],
        figure_rounded_sum_ft=sum(c['figure_length_ft'] for c in figure['components']),
        merged_source_length_ft=float(total), modeled_nonbit_length_ft=float(total-Decimal(components[0]['total_length_ft'])),
        difference_from_reported_ft=float(Decimal(str(figure['reported_assembly_length_ft']))-total),
        rescaled=False, HWDP_joints=9, HWDP_total_length_ft=272., HWDP_pitch_ft=272/9))
    dump(output/'coverage.json', dict(planned_windows=len(rows), planned_events=len(events),
        ready_with_declared_assumptions=sum(r['qualification']=='ready_with_declared_assumptions' for r in rows),
        incomplete_inlet=sum(r['qualification']=='missing_inlet' for r in rows), source_bins=len(locators),
        source_components=len(components), pipe_geometry_measured=False, history_bins=len(clock),
        history_gaps=history_gaps, prior_report_pressure_exposure=True, window_pressure_targets_read=False))
    files = sorted(p for p in output.iterdir() if p.is_file())
    dump(output/'manifest.json', dict(python=platform.python_version(), zlib=zlib.ZLIB_RUNTIME_VERSION,
        input_sha256=protocol['input_sha256'], source_sha256={p.name:sha(p.read_bytes()) for p in
        (Path(__file__), HERE/'protocol.json', HERE/'protocol.md', HERE/'bha2-figure14.json', HERE/'references.json')},
        output_sha256={p.name:sha(p.read_bytes()) for p in files},
        compressed_clock_unpacked_sha256=sha(gzip.decompress((output/'circulation-clock.csv.gz').read_bytes())),
        window_pressure_targets_read=False, prior_report_pressure_exposure=True))
    print(json.dumps(json.loads((output/'coverage.json').read_text()), indent=2))


if __name__ == '__main__':
    main()
