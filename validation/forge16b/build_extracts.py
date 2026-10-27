"""Build observation-only FORGE 16B whole-well tables.

Requires pandas in the extraction environment; no BoreTHM model is imported.
The 412-column source is streamed to selected columns in an external scratch
directory. Outputs in this directory are not installed package data.
"""
import argparse
import csv
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path

import pandas as pd

HERE=Path(__file__).resolve().parent
COLUMNS={
 'Hole Depth (feet)':'hole_depth_ft','Bit Depth (feet)':'bit_depth_ft',
 'Total Pump Output (gal_per_min)':'flow_gpm','Standpipe Pressure (psi)':'spp_psi',
 'Differential Pressure (psi)':'reported_differential_psi','TEMP IN MANIFOLD (DEGREES)':'temp_in_F',
 'TEMP OUT FLOW (DEGREES)':'temp_out_F','EYE TEMP (F)':'eye_temp_F',
 'Rate Of Penetration (ft_per_hr)':'rop_ft_h','On Bottom ROP (ft_per_hr)':'on_bottom_rop_ft_h',
 'Weight on Bit (klbs)':'wob_klbs','Rotary RPM (RPM)':'rotary_rpm',
 'Bit Size (UNITS)':'bit_size_in','Motor RPM (RPM)':'motor_rpm','Mud Motor Used (unitless)':'motor_used'}


def select(raw,scratch):
    nested=scratch/'16B_Pason.zip';selected=scratch/'pason-selected-10s.csv'
    provenance=scratch/'pason-selected-provenance.json'
    with raw.open('rb') as f:archive_hash=hashlib.file_digest(f,'sha256').hexdigest()
    if selected.exists() and provenance.exists():
        saved=json.loads(provenance.read_text())
        with selected.open('rb') as f:selected_hash=hashlib.file_digest(f,'sha256').hexdigest()
        if saved==dict(archive_sha256=archive_hash,selected_sha256=selected_hash):return selected
    # A cache without matching provenance is rebuilt from the supplied archive.
    with zipfile.ZipFile(raw) as z:
        expected=z.getinfo('16B_Pason.zip')
        refresh=not nested.exists() or nested.stat().st_size!=expected.file_size
        if not refresh:
            import zlib
            crc=0
            with nested.open('rb') as f:
                for block in iter(lambda:f.read(1024*1024),b''):crc=zlib.crc32(block,crc)
            refresh=crc!=expected.CRC
    if refresh:
        with zipfile.ZipFile(raw) as z,z.open('16B_Pason.zip') as src,nested.open('wb') as dst:
            shutil.copyfileobj(src,dst)
    with zipfile.ZipFile(nested) as z,z.open('10 Second Data.csv') as src,selected.open('w',newline='') as dst:
        reader=csv.reader(io.TextIOWrapper(src,encoding='utf-8-sig',newline=''))
        header=next(reader);assert len(header)==412
        indices=[header.index(k) for k in COLUMNS]
        writer=csv.writer(dst);writer.writerow(['source_row','time',*COLUMNS.values()])
        for n,row in enumerate(reader,2):
            if len(row)!=412:raise ValueError(f'Malformed source row {n}')
            writer.writerow([n,row[0].replace('/','-')+' '+row[1],
                             *['' if row[i]=='-999.25' else row[i] for i in indices]])
    with selected.open('rb') as f:selected_hash=hashlib.file_digest(f,'sha256').hexdigest()
    provenance.write_text(json.dumps(dict(archive_sha256=archive_hash,selected_sha256=selected_hash),indent=2)+'\n')
    return selected


def tables(selected,out):
    d=pd.read_csv(selected).rename(columns={'motor_dp_psi':'reported_differential_psi'})
    d['time']=pd.to_datetime(d.time)
    assert d.time.is_monotonic_increasing and not d.time.duplicated().any()
    # These thresholds use source observations only, before any model errors.
    physical=d.eye_temp_F.gt(32)&d.eye_temp_F.le(482)
    eye=d.eye_temp_F.where(physical)
    med=pd.Series(eye.to_numpy(),index=d.time).rolling('31min',center=True,min_periods=30).median().to_numpy()
    candidate=(eye-med).abs().gt(40)
    group=(candidate.ne(candidate.shift())|d.time.diff().dt.total_seconds().gt(20)).cumsum()
    isolated=pd.Series(False,index=d.index)
    ledger=[]
    for _,part in d[candidate].groupby(group[candidate]):
        first,last=part.time.iloc[0],part.time.iloc[-1]
        if (last-first).total_seconds()+10>600:continue
        before=d[(d.time>=first-pd.Timedelta(minutes=10))&(d.time<first)&physical&~candidate]
        after=d[(d.time>last)&(d.time<=last+pd.Timedelta(minutes=10))&physical&~candidate]
        if len(before)<6 or len(after)<6:continue
        left,right=before.eye_temp_F.median(),after.eye_temp_F.median()
        if abs(left-right)>15:continue
        flag=(part.eye_temp_F-left).abs().gt(40)&(part.eye_temp_F-right).abs().gt(40)
        isolated.loc[part.index]=flag
        if flag.any():ledger.append(dict(start=str(first),end=str(last),source_rows=int(flag.sum()),
                                         left_reference_F=left,right_reference_F=right))
    clean=physical&~isolated
    d['eye_clean_F']=d.eye_temp_F.where(clean)
    d['physical_reject']=d.eye_temp_F.notna()&~physical
    d['isolated_jump_reject']=isolated
    base=(d.flow_gpm>300)&d.flow_gpm.le(2000)&(d.bit_depth_ft-d.hole_depth_ft).abs().le(5)
    drilling=base&d.rop_ft_h.gt(1)
    d['qualified']=drilling
    d['qualified_eye_F']=d.eye_clean_F.where(drilling)
    definitions=pd.read_csv(out/'run_definitions.csv',keep_default_na=False)
    inventory=[];samples=[];excluded=[]
    for _,r in definitions.iterrows():
        # Five-foot exclusion on either side avoids ambiguous run-boundary rows.
        fullscope=d.hole_depth_ft.gt(float(r.depth_in_ft))&d.hole_depth_ft.le(float(r.depth_out_ft))
        scope=fullscope&d.hole_depth_ft.gt(float(r.depth_in_ft)+5)&d.hole_depth_ft.lt(float(r.depth_out_ft)-5)
        op=d[scope&drilling];valid=d[scope&drilling&clean]
        row=r.to_dict();row.update(raw_eye_rows=int((fullscope&base&d.eye_temp_F.notna()).sum()),
            first_raw_eye=str(d.loc[fullscope&base&d.eye_temp_F.notna(),'time'].min()),
            last_raw_eye=str(d.loc[fullscope&base&d.eye_temp_F.notna(),'time'].max()),
            drilling_rows=len(op),valid_eye_rows=len(valid),physical_rejected=int((scope&base&d.physical_reject).sum()),
            isolated_rejected=int((scope&base&isolated).sum()),distinct_levels=valid.eye_clean_F.nunique(),
            first=str(valid.time.min()) if len(valid) else '',last=str(valid.time.max()) if len(valid) else '')
        for field in ['bit_depth_ft','flow_gpm','temp_in_F','temp_out_F','spp_psi','reported_differential_psi','rop_ft_h','eye_clean_F']:
            row[field+'_min']=valid[field].min();row[field+'_max']=valid[field].max();row[field+'_mean']=valid[field].mean()
        count=0
        for centre,part in op.groupby(op.time.dt.round('30min')):
            # dt.round uses alternating exact half-way ties. Define the actual
            # half-open centred window explicitly for deterministic membership.
            part=op[(op.time>=centre-pd.Timedelta(minutes=15))&(op.time<centre+pd.Timedelta(minutes=15))]
            sensed=part[part.eye_clean_F.notna()]
            reason=[]
            if len(sensed)<90:reason.append('less than 15 minutes of qualified EYE coverage')
            if sensed.eye_clean_F.nunique()<2:reason.append('fewer than two distinct EYE levels')
            if part.hole_depth_ft.max()-part.hole_depth_ft.min()<.5:reason.append('less than 0.5 ft new-depth range')
            if int(r.eow_bha)==26:reason.append('no documented MWD in this assembly')
            if sensed[['temp_in_F','temp_out_F','spp_psi','reported_differential_psi']].isna().any().any():reason.append('missing paired surface input')
            if reason:
                excluded.append(dict(eow_bha=int(r.eow_bha),centre=str(centre),reason='; '.join(reason)));continue
            s=dict(sample_id=f'16b-{int(r.eow_bha):02}-{centre:%Y%m%d%H%M}',eow_bha=int(r.eow_bha),
                   time=str(centre),source_row_first=int(sensed.source_row.min()),source_row_last=int(sensed.source_row.max()),
                   qualified_rows=len(sensed),distinct_eye_levels=int(sensed.eye_clean_F.nunique()),
                   sensor_offset_ft=r.sensor_offset_ft,offset_basis=r.offset_basis,pipe_type=r.pipe_type,fit_role=r.fit_role)
            for field in ['bit_depth_ft','hole_depth_ft','flow_gpm','temp_in_F','temp_out_F','spp_psi','reported_differential_psi','rop_ft_h','eye_clean_F']:
                s[field]=sensed[field].mean()
            s['measured_MWD_C']=(s['eye_clean_F']-32)/1.8
            samples.append(s);count+=1
        row['candidate_samples']=count;inventory.append(row)
    pd.DataFrame(inventory).to_csv(out/'period_inventory.csv',index=False)
    pd.DataFrame(samples).to_csv(out/'candidate_samples.csv',index=False)
    pd.DataFrame(excluded).to_csv(out/'excluded_windows.csv',index=False)
    pd.DataFrame(ledger).to_csv(out/'isolated_jump_spells.csv',index=False)
    rejected=d[d.physical_reject|isolated][['source_row','time','eye_temp_F','physical_reject','isolated_jump_reject']]
    rejected.to_csv(out/'rejected_eye_rows.csv',index=False)
    # Long off spells are observed input history, not a transient model.
    known_off=d.flow_gpm.between(0,100)
    off_group=(known_off.ne(known_off.shift())|d.time.diff().dt.total_seconds().gt(20)).cumsum()
    off_rows=[]
    for _,part in d[known_off].groupby(off_group[known_off]):
        duration=(part.time.iloc[-1]-part.time.iloc[0]).total_seconds()+10
        if duration<60:continue
        off_rows.append(dict(start=str(part.time.iloc[0]),end=str(part.time.iloc[-1]+pd.Timedelta(seconds=10)),
                             duration_s=duration,minimum_bit_ft=part.bit_depth_ft.min(),
                             maximum_hole_ft=part.hole_depth_ft.max(),
                             long_reset=duration>7200,trip_to_surface=bool(part.bit_depth_ft.min()<1000)))
    pd.DataFrame(off_rows).to_csv(out/'observed_off_spells.csv',index=False)
    d['date']=d.time.dt.strftime('%Y-%m-%d')
    raw=d[base&d.eye_temp_F.notna()].groupby('date').agg(n=('eye_temp_F','size'),mean_F=('eye_temp_F','mean'))
    raw.to_csv(out/'daily_eye_means_unfiltered.csv')
    expected={'2023-05-21':(179.9,180),'2023-05-23':(149.6,149),'2023-05-25':(165.2,164),'2023-05-27':(220.5,220)}
    checks=[]
    for date,(check,report) in expected.items():
        observed=float(raw.loc[date,'mean_F']);assert abs(observed-check)<.06
        filtered=d[base&clean&(d.date==date)].eye_clean_F.mean()
        checks.append(dict(date=date,raw_daily_mean_F=observed,filtered_daily_mean_F=filtered,
                           Eavor_run_mean_F=report,raw_minus_report_F=observed-report,n=int(raw.loc[date,'n'])))
    pd.DataFrame(checks).to_csv(out/'trial_mean_check.csv',index=False)
    # A compact record for later circulation-clock reconstruction, with original
    # row counts retained and no filling of the downhole-temperature channel.
    d['circulating']=d.flow_gpm.between(100,2000,inclusive='right')
    d['missing_flow']=d.flow_gpm.isna()
    history=d.groupby(d.time.dt.floor('10min')).agg(raw_count=('source_row','size'),max_hole_depth_ft=('hole_depth_ft','max'),
                                                    circulating_count=('circulating','sum'),missing_flow_count=('missing_flow','sum'))
    history.to_csv(out/'circulation_history_10min.csv')
    minute=d.groupby(d.time.dt.floor('min'))
    data=minute[list(COLUMNS.values())+['eye_clean_F']].mean()
    data['raw_count']=minute.size();data['qualified_count']=minute.qualified.sum()
    data['qualified_eye_count']=minute.qualified_eye_F.count();data['qualified_eye_mean_F']=minute.qualified_eye_F.mean()
    data=data[(data.qualified_count>0)|data.eye_temp_F.notna()]
    data.to_csv(out/'pason_selected_1min.csv')
    summary=dict(raw_rows=len(d),first=str(d.time.min()),last=str(d.time.max()),
                 EYE_nonnull=int(d.eye_temp_F.notna().sum()),physical_rejected=int(d.physical_reject.sum()),
                 isolated_jump_rejected=int(isolated.sum()),qualified_drilling_rows=int(drilling.sum()),
                 qualified_clean_eye_rows=int((drilling&clean).sum()),candidate_samples=len(samples),
                 excluded_windows=len(excluded),minute_rows=len(data),pandas_version=pd.__version__,
                 protocol='Protocol is subject to S0 review; no model error has been computed.')
    (out/'extract_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,required=True,help='Downloaded GDR 1516 ZIP')
    p.add_argument('--scratch',type=Path,required=True,help='External scratch directory')
    p.add_argument('--output',type=Path,default=HERE)
    a=p.parse_args();a.scratch.mkdir(parents=True,exist_ok=True);a.output.mkdir(parents=True,exist_ok=True)
    selected=select(a.raw,a.scratch)
    tables(selected,a.output)


if __name__=='__main__':main()
