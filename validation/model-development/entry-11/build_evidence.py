"""Rebuild source transcriptions and explicitly qualified arithmetic.

The PDF text caches are produced by build_sources.py. The downloaded rig
specification remains external; only factual extracts and its hash are saved.
"""
import argparse
import csv
from datetime import datetime
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path

from pypdf import PdfReader
from build_sources import write

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RIG_URL='https://kenaidrilling.com/wp-content/uploads/2024/09/Rig10-Specs.pdf'


def read(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pages',type=Path,required=True)
    p.add_argument('--rig-spec',type=Path,required=True)
    p.add_argument('--raw16a',type=Path,required=True);a=p.parse_args()
    docs=read(HERE/'sources/source-documents.csv');facts=[]
    def fact(suffix,page,start,end,name,value,unit='',qualification=''):
        doc=next(d for d in docs if d['source_member'].endswith(suffix))
        pages=json.loads((a.pages/(doc['source_sha256']+'.json')).read_text())
        text='\n'.join(pages[page-1].splitlines()[start-1:end])
        facts.append(dict(classification='measured source record',name=name,value=value,unit=unit,
            source_member=doc['source_member'],source_sha256=doc['source_sha256'],page=page,
            line_start=start,line_end=end,source_text=text,qualification=qualification))
    daily='58-32_EOWR/DailyDrillingReport.pdf'
    fact(daily,13,27,27,'report10_slow_pump1','51 spm: 95 psi; 52 spm: 104 psi',qualification='Time and exact bit position not printed for these readings')
    fact(daily,2,68,69,'report6_inventory','240 joints: 4-in TSDS, G-105, TSDS40; 15 joints: 4-in HWDP, 3.5FH',qualification='Weight cells blank; inventory is not the installed component count')
    fact(daily,5,28,29,'report7_inventory','240 joints: 4-in TSDS, S-135, TSDS40; 15 joints: 4-in HWDP, 4FH',qualification='Thread label conflicts with adjacent reports')
    fact(daily,7,103,105,'report8_inventory','240 joints: 4-in TSDS, 14.0 lb/ft, S-135, TSDS40; 15 joints: 4-in HWDP, 28.0 lb/ft, TSDS40')
    fact(daily,10,75,77,'report9_inventory','240 joints: 4-in TSDS, 14.0 lb/ft, S-135, TSDS40; 15 joints: 4-in HWDP, 28.0 lb/ft, TSDS40')
    fact(daily,6,70,70,'report8_kelly','4.25-in square replaced by 5.25-in hex at 360 ft; 17:30-19:00',qualification='External size and shape; bore and complete surface layout unreported')
    fact(daily,13,14,15,'report10_bit_hydraulics','254 psi bit drop; 177 ft/s jet velocity; three 22/32-in jets',qualification='Printed drilling-summary values, not an independent nozzle test')
    fact('58-32_EOWR/BitSummary.pdf',1,6,12,'bit2_nozzles','Smith XR+, 12.25 in; 22/32, 22/32, 22/32; printed TFA 1.114 in2',qualification='No additional open or centre port is documented; absence of a note is not inspection evidence')
    for row in read(ROOT/'validation/forge58-32/mud_reports.csv'):
        if not '2017-08-03'<=row['sample_date']<='2017-08-06':continue
        doc=next(d for d in docs if d['source_member']==row['source_member'])
        lines=json.loads((a.pages/(doc['source_sha256']+'.json')).read_text())[int(row['page'])-1].splitlines()
        stamp=datetime.fromisoformat(row['sample_date']).strftime('%d-%b-%y')
        indices=[i for i,s in enumerate(lines,1) if stamp in s and row['sample_time'] in s]
        assert len(indices)==1,(row,indices)
        fact(row['source_member'].split('!',2)[-1],int(row['page']),indices[0],indices[0],
             'mud_density_'+row['sample_date'],float(row['mud_weight_ppg']),'lb/US gal')
    figure=json.loads((ROOT/'validation/forge58-32/pressure-test/bha2-figure14.json').read_text())
    hwdp=next(r for r in figure['components'] if r['component']=='HWDP')
    doc=next(d for d in docs if d['source_member'].endswith('58-32_EOWR/58-32_EOWR_DOE.pdf'))
    facts.append(dict(classification='measured source record',name='HWDP_bore',value=hwdp['reported_ID_in'],unit='in',
        source_member=doc['source_member'],source_sha256=doc['source_sha256'],page=29,
        line_start='',line_end='',source_text='Figure 14, item 17: HWDP, 9 joints, total length 272 ft, ID 2.5 in',
        qualification='Figure item locator; retained P3 transcription, not a bore inferred from the inventory thread'))
    spec=PdfReader(a.rig_spec);sha=hashlib.sha256(a.rig_spec.read_bytes()).hexdigest()
    text=spec.pages[0].extract_text();assert 'RS-F-1000' in text and 'Triplex' in text
    spec_meta=dict(url=RIG_URL,sha256=sha,page=1,creation_date=str(spec.metadata.get('/CreationDate')),
        modification_date=str(spec.metadata.get('/ModDate')),author=str(spec.metadata.get('/Author')),
        qualification='2021 PDF metadata; no evidence that this pump/liner configuration was installed in August 2017')
    (HERE/'sources/rig10-public-source.json').write_text(json.dumps(spec_meta,indent=2)+'\n',encoding='utf-8')
    pump_lines=[i for i,line in enumerate(text.splitlines(),1) if 'RS-F-1000' in line]
    assert len(pump_lines)==2
    facts.append(dict(classification='measured source record',name='published_Rig10_pumps',value='Two RS-F-1000 triplex pumps, 6.75-in liner and 10-in stroke, 1000 HP each',
        unit='',source_member=RIG_URL,source_sha256=sha,page=1,line_start=min(pump_lines),line_end=max(pump_lines),source_text='Mud Pump #1 and Mud Pump #2 specification rows',qualification=spec_meta['qualification']))
    write(HERE/'sources/verified-facts.csv',facts)
    arithmetic=[dict(classification='calculated',quantity='three_22_32_nozzle_area',value=3*math.pi/4*(22/32)**2,unit='in2',basis='Bit run 2 recorded nozzle sizes; rounded printed TFA is 1.114 in2')]
    displacement=3*math.pi/4*6.75**2*10/231
    arithmetic.append(dict(classification='calculated',quantity='published_Rig10_displacement_100pct',value=displacement,unit='US gal/stroke',basis='Published later rig specification; not established for the registered 2017 period'))
    for liner,stroke in ((6.75,12),(7,11)):
        arithmetic.append(dict(classification='calculated',quantity=f'illustrative_D{liner}_L{stroke}',value=3*math.pi/4*liner**2*stroke/231,unit='US gal/stroke',basis='Illustrative arithmetic only; no installed pump identification'))
    ratios=read(HERE/'results/58-32-ratios-by-day.csv')
    factor=float(next(r['median_gal_stroke'] for r in ratios if r['day']=='2017-08-04' and r['combination']=='1+2'))
    arithmetic.append(dict(classification='calculated',quantity='configured_equivalent_D2L',value=factor*231*4/(3*math.pi),unit='in3',basis='Pason ratio; not a sourced liner or stroke'))
    write(HERE/'results/source-arithmetic.csv',arithmetic)
    # The registered window input projection supplies actual source-stroke means.
    locators=read(ROOT/'validation/forge58-32/pressure-test/inputs/source-bins.csv')
    import gzip
    needed={r['bin_time'] for r in locators}
    with gzip.open(ROOT/'validation/forge58-32/rig_inputs_10s.csv.gz','rt',encoding='utf-8') as f:
        bins={r['time']:r for r in csv.DictReader(f) if r['time'] in needed}
    windows=read(ROOT/'validation/forge58-32/pressure-test/inputs/windows.csv');out=[]
    import statistics as st
    for window in windows:
        used=[bins[r['bin_time']] for r in locators if r['window_id']==window['window_id']]
        spm=st.fmean(float(r['pump1_spm'])+float(r['pump2_spm']) for r in used)
        out.append(dict(classification='calculated, time-transferred specification arithmetic',window_id=window['window_id'],
            event_id=window['event_id'],recorded_flow_gpm=window['flow_gpm'],summed_pump_spm=spm,
            published_displacement_gal_stroke=displacement,published_100pct_flow_gpm=spm*displacement,
            source_url=RIG_URL,source_sha256=sha,source_page=1,
            native_row_ranges=json.dumps([dict(member=r['source_member'],first_row=r['first_source_row'],last_row=r['last_source_row']) for r in used]),
            qualification='No 2017 applicability or efficiency established; not a corrected flow input; no hydraulic solve'))
    write(HERE/'results/B4-published-specification-flows.csv',out)
    with zipfile.ZipFile(a.raw16a) as top:
        nested_name='16A(78)-32_Pason_Data.zip';member='28044193.las'
        with zipfile.ZipFile(io.BytesIO(top.read(nested_name))) as nested:
            data=nested.read(member)
            lines=[]
            with io.TextIOWrapper(io.BytesIO(data),encoding='utf-8-sig') as stream:
                for line in stream:
                    if line.startswith('~A'):break
                    lines.append(line.rstrip())
            metadata=[]
            for i,line in enumerate(lines,1):
                if line.startswith(('#LAS','WELL.','RIG .')):
                    metadata.append(dict(classification='measured source record',source_member=a.raw16a.name+'!'+nested_name+'!'+member,
                        source_sha256=hashlib.sha256(data).hexdigest(),line_start=i,line_end=i,source_text=line,
                        qualification='Later stimulation job; not the 2020 drilling-period per-pump record'))
            write(HERE/'sources/16A-pason-job-identity.csv',metadata)


if __name__=='__main__':main()
