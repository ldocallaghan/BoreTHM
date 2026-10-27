"""Tabulate the frozen geometry inputs for Q4, without thermal solves."""
import csv
import json
from pathlib import Path
from borethm.studies import validate_forge16a as a
from borethm.studies import validate_forge16b_wholewell as b

HERE=Path(__file__).resolve().parent/'s2'
p=json.loads((HERE/'plan.json').read_text())
samples=[];strings=[]
for s in p['samples']:
    if s['well']=='16A':g=a.geometry(s['run'],s['bit_ft'],p['components_a'])
    else:g=b.geometry(s,p['components_b'],p['k_idp'])
    for i,segment in enumerate(g.string,1):
        pipe=segment.pipe
        strings.append(dict(sample=s['id'],well=s['well'],run=s['run'],segment_from_surface=i,
            length_ft=segment.length/b.FT,pipe_name=pipe.name,body_OD_in=2*pipe.r_out/b.INCH,
            body_ID_in=2*pipe.r_bore/b.INCH,
            layer_conductivity_W_mK=';'.join(str(x.k) for x in pipe.layers)))
    samples.append(dict(sample=s['id'],well=s['well'],run=s['run'],bit_ft_MD=s['bit_ft'],
        bit_ft_TVD=float(g.survey.tvd(g.md_bit)/b.FT),string_segments=len(g.string),
        ordinary_pipe_OD_in=5 if s['well']=='16A' else 5.5,ordinary_pipe_ID_in=4.276 if s['well']=='16A' else 4.670,
        open_hole_diameter_in=8.75 if s['well']=='16A' else 14.75 if s['eow_bha'] in [3,4] else 9.5,
        bottom_assembly_length_ft=g.string[-1].length/b.FT,bottom_assembly_OD_in=2*g.string[-1].pipe.r_out/b.INCH,
        bottom_assembly_ID_in=2*g.string[-1].pipe.r_bore/b.INCH,pipe_type=s.get('pipe_type','regular'),
        tfa_in2=s['tfa_m2']/b.INCH**2))
def save(name,rows):
    with (HERE/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
save('geometry-samples.csv',samples);save('string-segments.csv',strings)
print('Geometry samples',len(samples),'string segments',len(strings))
