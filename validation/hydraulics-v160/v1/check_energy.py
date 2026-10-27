"""Save representative variable-property energy checks on a synthetic well."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from borethm import HydraulicProgramme, LocalLoss, WellGeometry, circulating_temperatures, hydraulics
from borethm import fluids, well_geometry as wg


def run(out):
    programme=HydraulicProgramme.reference_programme()
    geometry=programme.geometry(1500.,wg.DUAL_WALL,shoes=(50.,300.,750.))
    string=list(geometry.string)
    string[-1]=replace(string[-1],local_loss=LocalLoss(1.,.5,source='synthetic bit-body restriction'))
    geometry=WellGeometry(string,geometry.hole,geometry.survey)
    records=[]
    for name,fluid in [('water',None),('reference Bingham mud at 1200 kg/m3',fluids.Mud(1200.))]:
        r=circulating_temperatures(m_dot=20.,geometry=geometry,fluid=fluid,friction_heat=True,surface=programme.surface)
        assert r['success'] and r['energy_check']['passed'],name
        h=hydraulics(20.,geometry,result=r,fluid=fluid)
        records.append(dict(fluid=name,m_dot_kg_s=20.,depth_m=1500.,inlet_C=40.,face_W=28000.,
            bore_bottom_C=float(r['Td'][-1]),surface_return_C=float(r['Tu'][0]),spp_Pa=h['spp'],
            energy_check=r['energy_check'],hydraulic_flags=h['flags']))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(synthetic_well=True,hydraulics_model='v1.6.0',cases=records),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({r['fluid']:r['energy_check']['residual_W'] for r in records},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('validation/hydraulics-v160/v1/evidence/energy-checks.json'))
    run(parser.parse_args().output)
