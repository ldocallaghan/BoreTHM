"""Summarise source coverage and check extract accounting; no thermal model."""
from pathlib import Path
import argparse,bisect,csv,hashlib,json,statistics
from datetime import datetime,timedelta

HERE=Path(__file__).resolve().parent
def read(path):
    return list(csv.DictReader(path.open(encoding='utf-8'))) if path.exists() else []
def save(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def numeric(r,key):
    try:return float(r[key])
    except (KeyError,TypeError,ValueError):return None
def bounds(rows,key):
    v=[numeric(r,key) for r in rows];v=[x for x in v if x is not None]
    return (min(v),max(v)) if v else ('','')
def audit(root):
    inventory=read(root/'run_inventory.csv');mud=read(root/'mud_log_by_depth.csv')
    daily=read(root/'daily_well_inputs.csv');bits=read(root/'bit_records.csv');components=read(root/'bha_components.csv')
    first_bits={}
    for record in bits:first_bits.setdefault(record['sha256'],record)
    rig={r['time']:r for r in read(root/'rig_history_1min.csv')}
    runs=[];clock=[];checks=[]
    for item in inventory:
        run=item['run'];base=run.split('r')[0]
        rows=read(root/f'sanvean_BHA{run}_10s.csv')
        assert sum(int(x['raw_count']) for x in rows)==int(item['raw_rows'])
        assert sum(int(x['invalid_flow_count']) for x in rows)==int(item['invalid_flow_rows'])
        assert all(int(x['drilling_count'])<=int(x['raw_count']) for x in rows)
        drilling=[x for x in rows if int(x['drilling_count'])>0]
        lo,hi=bounds(drilling,'hole_depth_ft')
        interval=[x for x in mud if lo!='' and lo<=float(x['md_ft'])<=hi and float(x['temp_in_F'])>32 and float(x['temp_out_F'])>32]
        reports=[x for x in daily if x['BHA']==base]
        bit=[]
        for x in bits:
            same_run=x['BHA']==base
            # The 10 December report's final BHA table is a packer assembly;
            # its operations explicitly describe the preceding rerun of BHA 35.
            historical_rerun=(run=='35r2' and x['report_date']=='12/10/2020' and x['bit_number']=='32')
            if not (same_run or historical_rerun) or lo=='':continue
            if not x['depth_out_ft'] and x is not first_bits[x['sha256']]:continue
            try:
                a=float(x['depth_in_ft'].replace(',',''));b=float(x['depth_out_ft'].replace(',','')) if x['depth_out_ft'] else float('inf')
            except ValueError:continue
            if min(b,hi)-max(a,lo)>1:bit.append(x)
        row=dict(run=run,start=item['start'],end=item['end'],
                 bit_box_available=int(item['bit_box_count'])>0,top_sub_available=int(item['top_sub_count'])>0,
                 lower_mandrel_available=int(item['lower_mandrel_count'])>0,drilling_MD_min_ft=lo,drilling_MD_max_ft=hi,
                 drilling_h=item['drilling_h'],pumps_off_h=item['pumps_off_h'],pumps_off_downward_motion_h=item['running_in_pumps_off_h'],
                 drilling_flow_min_gpm=bounds(drilling,'flow_gpm')[0],drilling_flow_max_gpm=bounds(drilling,'flow_gpm')[1],
                 mudlog_in_min_F=bounds(interval,'temp_in_F')[0],mudlog_in_max_F=bounds(interval,'temp_in_F')[1],
                 mudlog_out_min_F=bounds(interval,'temp_out_F')[0],mudlog_out_max_F=bounds(interval,'temp_out_F')[1],
                 report_dates='; '.join(sorted(set(x['report_date'] for x in reports))),
                 mud_weight_min_ppg=bounds(reports,'mud_weight_ppg')[0],mud_weight_max_ppg=bounds(reports,'mud_weight_ppg')[1],
                 PV_min_cP=bounds(reports,'plastic_viscosity_cP')[0],PV_max_cP=bounds(reports,'plastic_viscosity_cP')[1],
                 YP_min_lbf_100ft2=bounds(reports,'yield_point_lbf_100ft2')[0],YP_max_lbf_100ft2=bounds(reports,'yield_point_lbf_100ft2')[1],
                 nozzle_records='; '.join(sorted(set(x['jets_32nds']+' ('+x['TFA_in2']+' in2)' for x in bit if x['jets_32nds']))),
                 bit_box_offset_ft='',top_sub_offset_ft='',sensor_quantity='unresolved: fluid versus body not stated',
                 known_hydraulic_disruption='washout documented around both BHA 35 deployments' if base=='35' else '')
        # The report identifies a PUK sub above the motor, but does not map its
        # sensing element to the exported labels. Preserve that distinction.
        dates=sorted(set(x['report_date'] for x in reports),key=lambda x:datetime.strptime(x,'%m/%d/%Y'))
        selected=[x for x in components if x['BHA']==base and dates and x['report_date']==dates[0]]
        unique={x['item']:x for x in selected}
        if all(str(i) in unique and numeric(unique[str(i)],'length_ft') is not None for i in [1,2,3]):
            if 'sensor' in unique['3']['component'].lower() or 'puk' in unique['3']['component'].lower():
                start=sum(float(unique[str(i)]['length_ft']) for i in [1,2]);row['reported_PUK_sub_bottom_ft_above_bit']=start
                row['reported_PUK_sub_top_ft_above_bit']=start+float(unique['3']['length_ft'])
        runs.append(row)
        samples=drilling[::max(1,len(drilling)//200)]
        candidates=[]
        for offset in range(-12,13):
            depth=[];flow=[]
            for x in samples:
                t=datetime.fromisoformat(x['time']).replace(second=0)+timedelta(hours=offset)
                s=rig.get(t.isoformat(sep=' '))
                if s and s['hole_depth_ft'] and s['flow_gpm']:
                    depth.append(abs(float(x['hole_depth_ft'])-float(s['hole_depth_ft'])))
                    flow.append(abs(float(x['flow_gpm'])-float(s['flow_gpm'])))
            if depth:candidates.append(dict(run=run,offset_hours_rig_minus_Sanvean=offset,matched=len(depth),
                                            median_absolute_depth_ft=statistics.median(depth),median_absolute_flow_gpm=statistics.median(flow)))
        clock.extend(sorted(candidates,key=lambda x:x['median_absolute_depth_ft'])[:3])
        checks.append(dict(run=run,bins=len(rows),raw_count_reconciled=True,invalid_flow_count_reconciled=True))
    save(root/'run_inputs.csv',runs);save(root/'clock_alignment.csv',clock)
    result=dict(passed=True,runs=len(runs),bit_box_runs=[r['run'] for r in runs if r['bit_box_available']],
                bit_box_and_top_sub_runs=[r['run'] for r in runs if r['bit_box_available'] and r['top_sub_available']],
                raw_rows=sum(int(r['raw_rows']) for r in inventory),invalid_flow_rows=sum(int(r['invalid_flow_rows']) for r in inventory),
                flow_above_100000_rows=sum(int(r['flow_above_100000_rows']) for r in inventory),
                best_clock_offsets=[min([x for x in clock if x['run']==r['run']],key=lambda x:x['median_absolute_depth_ft']) for r in runs],
                checks=checks,thermal_predictions_computed=False)
    assert len(result['bit_box_runs'])==9 and len(result['bit_box_and_top_sub_runs'])==8
    (root/'source_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,default=HERE);a=p.parse_args();print(json.dumps(audit(a.data),indent=2))
