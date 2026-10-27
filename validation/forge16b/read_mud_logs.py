"""Read depth-indexed mud temperatures and compare source channels only."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

import pandas as pd


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--pason-selected',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args();inventory=[];final=[]
    with zipfile.ZipFile(a.archive) as z:
        for name in z.namelist():
            if not name.lower().endswith('.las'):continue
            data=z.read(name);text=data.decode('cp1252')
            date=re.search(r'\bDATE\.\s*(\d+/\d+/\d+)',text)
            assert re.search(r'\bMTIA\.F\s',text) and re.search(r'\bMTOA\.F\s',text)
            count=0;rows=[];reading=False
            for line in text.splitlines():
                if line.startswith('~LOG_DATA'):reading=True;continue
                if not reading or not line.strip():continue
                values=line.split()
                if len(values)!=3:raise ValueError(name+': unexpected LAS data columns')
                depth,tin,tout=map(float,values)
                if tin==-999.25 or tout==-999.25:continue
                rows.append(dict(hole_depth_ft=depth,temp_in_F=tin,temp_out_F=tout));count+=1
            inventory.append(dict(member=name,header_date=date[1] if date else '',paired_depths=count,
                                  sha256=hashlib.sha256(data).hexdigest(),units='F'))
            if name=='Utah Forge 16B(78)-32 Mud Temperature.las':final=rows
    assert final
    pd.DataFrame(inventory).to_csv(a.output/'mud_log_versions.csv',index=False)
    log=pd.DataFrame(final);log.to_csv(a.output/'mud_temperatures_by_depth.csv',index=False)
    d=pd.read_csv(a.pason_selected)
    q=(d.flow_gpm>300)&d.flow_gpm.le(2000)&(d.bit_depth_ft-d.hole_depth_ft).abs().le(5)&d.rop_ft_h.gt(1)
    d=d[q].dropna(subset=['temp_in_F','temp_out_F','hole_depth_ft']).copy()
    d['hole_depth_ft']=d.hole_depth_ft.round()
    pairs=d.groupby('hole_depth_ft')[['temp_in_F','temp_out_F']].mean().reset_index().merge(log,on='hole_depth_ft',suffixes=('_pason','_LAS'))
    pairs.to_csv(a.output/'surface_channel_crosscheck.csv',index=False)
    valid=pairs[[c for c in pairs if c!='hole_depth_ft']].apply(lambda col:col.gt(32)&col.le(482)).all(axis=1)
    pairs[~valid].to_csv(a.output/'surface_crosscheck_rejected.csv',index=False)
    usable=pairs[valid]
    report=dict(raw_paired_depths=len(pairs),invalid_temperature_pairs=int((~valid).sum()),versions=len(inventory),LAS_units='Fahrenheit, explicit MTIA.F and MTOA.F headers',
                paired_depths=len(usable),comparison='Pason qualified drilling means at rounded hole depth versus final compiled LAS; source-to-source, not model errors')
    for field in ['temp_in_F','temp_out_F']:
        delta=usable[field+'_pason']-usable[field+'_LAS']
        report[field]=dict(mean_difference_F=float(delta.mean()),MAE_F=float(delta.abs().mean()),max_abs_F=float(delta.abs().max()))
    (a.output/'surface_channel_crosscheck.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
