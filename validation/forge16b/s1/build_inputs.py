"""Transcribe study inputs from EOW drawings and Appendix B; no model solve."""
import csv
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]/'geothermal-thermo-hydraulic-model'
OUT=ROOT/'validation/forge16b'
rows=[]
def group(bha,page,items,note=''):
    for i,(name,length,od,inside,kind) in enumerate(items,1):
        rows.append(dict(eow_bha=bha,item=i,component=name,length_ft=length,od_in=od,id_in=inside,
                         kind=kind,length_source=f'EOW p{page}',dimension_source=f'EOW p{page}',input_note=note))
def c(name,L,od,inside,kind='assembly'):return (name,L,od,inside,kind)
early=[c('PDC bit',1.55,9.688,3.375),c('Mud motor',38.47,9.5,4.625),
       c('String stabiliser',5.5,10,2.875),c('NMDC',30.56,9.563,4.25),
       c('NM pony DC',9,9.875,4.25),c('Hangoff sub',3.01,9.5,4.25),
       c('Hybrid sub',5.4,9.375,3.5),c('NM pony DC',12.32,9.25,4.25),
       c('Crossover',4.31,8,3),c('Nine drill collars',271.72,8.125,3,'collar'),
       c('Crossover',2.91,8,2.875),c('15 HWDP joints',456.67,7.188,3.875,'HWDP')]
group(3,38,early,'Reported body OD retained; 14.75 in hole/bit gauge is separate from component body OD')
length4=[1.56,37.96,7.8,30.56,9,3.01,5.4,12.32,4.31,363.21,2.91,913.42]
items4=[(name,L,od,inside,kind) for (name,_,od,inside,kind),L in zip(early,length4)]
items4[2]=c('14.75 in roller reamer',7.8,10,2.875)
group(4,185,items4,'Own Appendix B lengths; OD/ID borrowed from EOW 3 p38, including stabiliser body for roller reamer')
for r in rows:
    if r['eow_bha']==4:r['dimension_source']='EOW p38, BHA 3, borrowed'
tail=[c('Nine drill collars',278.27,6.813,2.875,'collar'),c('Crossover',3.15,6.937,3),c('30 HWDP joints',913.42,5.5,3.625,'HWDP')]
group(11,71,[c('PDC bit',1.13,6.375,2.75),c('HALO RSS',35.38,6.75,2),c('Spiral stabiliser',5.62,6.5,2.813),
 c('NM pony DC',9.22,6.438,3.25),c('NMDC',31.11,6.813,3.25),c('Roller reamer',5.64,6.375,3),
 c('Black box',6,6.75,2.25),c('RipStick',19.93,6.75,2),c('Mud motor',41.28,7.188,2),c('Filter sub',3.93,6.688,3.25),*tail],
 'Bit row body OD 6.375 in retained as reported; bit gauge 9.5 in')
group(12,75,[c('PDC bit',1.13,9.5,2.75),c('HALO RSS',35.31,6.75,2),c('Spiral stabiliser',5.66,6.5,2.813),
 c('NM pony DC',9.22,6.438,3.25),c('NMDC',31.11,6.813,3.25),c('Roller reamer',6.71,6.625,2.938),
 c('Black box',6,6.75,2.25),c('Float sub',2.45,6.375,2.875),c('Filter sub',3.93,6.688,3.25),*tail])
group(13,80,[c('PDC bit',1.13,9.5,2.75),c('HALO RSS',35.31,6.75,2),c('Spiral stabiliser',5.42,6.5,2.813),
 c('NMDC',31.11,6.813,3.25),c('Roller reamer',6.71,6.625,2.938),c('Black box',5.9,6.75,2.25),
 c('Float sub',2.45,6.375,2.875),c('Filter sub',3.93,6.688,3.25),*tail])
for bha,page,bit,rss,black in [(15,93,1.22,35.48,6),(16,97,1.18,35.33,5.97)]:
    group(bha,page,[c('PDC bit',bit,9.5,2.75),c('HALO RSS',rss,6.75,2),c('Spiral stabiliser',4.14,6.5,2.875),
     c('NM pony DC',12.24,6.438,3.5),c('NM pony DC',9.83,6.813,3.25),c('Roller reamer',5.39,6.625,3),
     c('NMDC',31.11,6.813,3.25),c('Black box',black,6.75,2.25),c('Filter sub',3.93,6.688,3.25),
     c('Float sub',2.45,6.375,2.875),*tail])
late=[c('PDC bit',1.05,9.5,2.75),c('Mud motor',41.92,7.188,2),c('Roller reamer',6.71,6.563,3),
 c('NM pony DC',9.22,6.438,3.25),c('NMDC',31.11,6.813,3.25),c('Pulser sub',5.6,6.5,3.5),
 c('NMDC',31.10,6.813,3.5),c('NM pony DC',12.24,6.438,3.5),c('NM pony DC',9.83,6.813,3.25),
 c('Black box',5.9,6.75,2.25),c('Filter sub',3.93,6.688,3.25),c('Float sub',2.45,6.375,2.875),
 c('Crossover',3.15,6.937,3),c('30 HWDP joints',918.47,5.5,3.625,'HWDP')]
group(38,160,late,'Own drawing dimensions/lengths; temperature position 84 ft plus 22 ft sensitivity as ruled; drawing says Eye=85 ft')
late27=[late[i] for i in [0,1,2,3,4,5,6,9,10,11,12,13]]
length27=[1.25,41.92,6.71,9.22,31.11,5.6,31.10,6,3.93,2.45,3.15,920.94]
group(27,191,[(name,L,od,inside,kind) for (name,_,od,inside,kind),L in zip(late27,length27)],
      'Own Appendix B lengths; matching component OD/ID borrowed from BHA 38 drawing p160')
for r in rows:
    if r['eow_bha']==27:r['dimension_source']='EOW p160, BHA 38, borrowed'
with (OUT/'component_inputs_s1.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (OUT/'mud_supplement_s1.csv').open('w',newline='',encoding='utf-8') as f:
    keys=['report_date','source','page','sample','density_ppg','funnel_viscosity_s','PV_cP','YP_lbf_100ft2','note']
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
    for date,page,sample in [('2023-05-13',237,'12-May-23 15:00 at Depth 4,978 ft Mud Pits, Type: Low Solids Non-Dispersed'),
                             ('2023-05-14',240,'13-May-23 11:00 at Depth 5,246 ft Mud Pits, Type: Low Solids Non-Dispersed')]:
        w.writerow(dict(report_date=date,source='End of Well Report-16B78-32-May_2024.pdf',page=page,sample=sample,
                        density_ppg=8.4,funnel_viscosity_s=27,PV_cP='',YP_lbf_100ft2='',
                        note='Mud table split across PDF pages; missing from S0 table; added before S1 predictions'))
print('Transcribed',len(rows),'component rows and two split-page mud rows')
