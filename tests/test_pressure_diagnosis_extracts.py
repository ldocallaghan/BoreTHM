"""Observation selection must be independent of pressure and temperature."""
import csv
from datetime import datetime, timedelta
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'validation/model-development/entry-9/build_extracts.py'
spec = importlib.util.spec_from_file_location('pressure_diagnosis_extracts', SOURCE)
extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract)


def sample_rows(pressure=500., temperature=90., depth=2000.):
    for i in range(24):
        row = {key: '' for key in extract.FIELDS}
        row.update(assembly='18', source_row=i+2, excursion='18',
                   time=(datetime(2020,11,24)+timedelta(seconds=10*i)).isoformat(sep=' '),
                   bit_depth_ft=depth, hole_depth_ft=6000., flow_gpm=600.,
                   spp_psi=pressure, temp_out_F=temperature)
        yield row


def run(tmp_path, rows, well='16A', assignments=()):
    tmp_path.mkdir(exist_ok=True)
    path=tmp_path/'input.csv.gz'
    raw, text=extract.gz_writer(path)
    try:
        writer=csv.DictWriter(text, fieldnames=['assembly',*extract.FIELDS], lineterminator='\n')
        writer.writeheader();writer.writerows(rows)
    finally:
        text.close();raw.close()
    extract.steady(path, well, assignments, tmp_path)
    return extract.read(tmp_path/f'{well.lower()}-steady-windows.csv')


def test_selection_does_not_use_pressure_or_temperature(tmp_path):
    original=run(tmp_path/'original',sample_rows())
    changed=run(tmp_path/'changed',sample_rows(pressure=-300.,temperature=900.))
    assert len(original)==len(changed)==1
    for field in ['window_id','assembly','start','end','bit_depth_ft','flow_gpm']:
        assert original[0][field]==changed[0][field]
    assert float(changed[0]['spp_psi'])==-300.


def test_missing_pressure_is_counted_without_changing_selection(tmp_path):
    rows=list(sample_rows())
    for row in rows:row['spp_psi']=''
    result=run(tmp_path,rows)
    assert len(result)==1
    assert result[0]['spp_psi']==''
    assert result[0]['spp_psi_count']=='0'


def test_shallow_assembly_is_never_inherited_from_adjacent_excursion(tmp_path):
    rows=list(sample_rows(depth=300.))
    result=run(tmp_path,rows,'16B',[dict(excursion='18',assembly='12')])
    assert len(result)==1
    assert result[0]['assembly']==''
    assert 'unresolved' in result[0]['assignment']
    assert result[0]['motor']=='unknown'


def test_moving_bit_and_flow_steps_are_excluded(tmp_path):
    rows=list(sample_rows())
    for i,row in enumerate(rows):row['bit_depth_ft']+=i*2
    assert run(tmp_path/'moving',rows)==[]
    rows=list(sample_rows())
    rows[-3]['flow_gpm']=800.
    assert run(tmp_path/'flow-step',rows)==[]


def test_empty_rebuild_replaces_an_earlier_window_table(tmp_path):
    assert len(run(tmp_path,sample_rows()))==1
    rows=list(sample_rows())
    for row in rows:row['flow_gpm']=0.
    assert run(tmp_path,rows)==[]


def test_gzip_has_reproducible_metadata(tmp_path):
    values=[]
    for name in ['first','second']:
        path=tmp_path/(name+'.gz')
        raw,text=extract.gz_writer(path)
        try:text.write('same observation\n')
        finally:text.close();raw.close()
        values.append(path.read_bytes())
        assert gzip.decompress(values[-1])==b'same observation\n'
    assert values[0]==values[1]


def test_rig_depth_absence_is_explicit_in_both_source_cadences():
    rows=extract.read(SOURCE.parent/'inputs/16a-channel-coverage.csv')
    depths=[r for r in rows if r['channel']=='Bit Depth']
    assert len(depths)==2
    assert all(int(r['data_rows'])>600000 and r['nonnull_rows']=='0' for r in depths)


def test_report_identifies_incoming_halo_without_pressure():
    intervals=extract.read(SOURCE.parent/'16b-assembly-intervals.csv')
    assembly,status=extract.report_assignment('2023-05-13 02:52:00',370.38,4980.46,intervals)
    assert assembly=='11'
    assert status=='reported incoming assembly'
    assert extract.report_assignment('2023-05-13 02:52:00',370.38,5300.,intervals)[0]==''


def test_mixed_equipment_operation_retains_its_uncertainty():
    intervals=extract.read(SOURCE.parent/'16b-assembly-intervals.csv')
    assembly,status=extract.report_assignment('2023-05-17 20:28:00',138.51,6609.87,intervals)
    assert assembly=='15'
    assert status=='report sequence inferred'


def test_report_boundary_separates_assemblies_without_a_shallow_visit(tmp_path, monkeypatch):
    intervals=extract.read(SOURCE.parent/'16b-assembly-intervals.csv')
    boundaries=extract.report_starts(intervals)
    assert '2023-05-26 09:00:00' in boundaries
    assert '2023-05-17 18:00:00' not in boundaries
    records=tmp_path/'validation/forge16b'
    records.mkdir(parents=True)
    (records/'run_definitions.csv').write_text(
        'eow_bha,depth_in_ft,depth_out_ft\n19,8585,9255\n20,9255,9800\n',
        encoding='utf-8')
    data=io.StringIO(newline='')
    writer=csv.writer(data,lineterminator='\n')
    writer.writerow(['Date','Time',*extract.B_COLS.values()])
    for stamp,depth in [('08:58:00',9000),('08:59:50',9262),
                        ('09:00:00',9300),('09:01:00',9400)]:
        row={key:0 for key in extract.B_COLS}
        row.update(bit_depth_ft=depth,hole_depth_ft=depth,flow_gpm=600)
        writer.writerow(['2023/05/26',stamp,*row.values()])
    scratch=tmp_path/'scratch';scratch.mkdir()
    nested=scratch/'16B_Pason.zip'
    with zipfile.ZipFile(nested,'w') as packed:
        packed.writestr('10 Second Data.csv',data.getvalue())
    (records/'source_manifest.json').write_text(json.dumps({'members':[
        {'name':'16B_Pason.zip','sha256':hashlib.sha256(nested.read_bytes()).hexdigest()}]}),
        encoding='utf-8')
    with zipfile.ZipFile(tmp_path/'1516.zip','w') as packed:
        packed.write(nested,'16B_Pason.zip')
    output=tmp_path/'output';output.mkdir()
    monkeypatch.setattr(extract,'ROOT',tmp_path)
    _,assignments,_=extract.select_b(tmp_path,scratch,output)
    assert [(r['assembly'],r['rows']) for r in assignments]==[('19',2),('20',2)]
