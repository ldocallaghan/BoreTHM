"""Distribution checks reject accidental field-archive payloads."""
import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('check_wheel', Path(__file__).parents[1]/'tools/check_wheel.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def distributions(root, extra='', kind='wheel'):
    with zipfile.ZipFile(root/'borethm-1.5.0-py3-none-any.whl','w') as archive:
        archive.writestr('borethm/studies/validate_forge16a.py','')
        if extra and kind=='wheel':
            archive.writestr(extra,'temperature')
    with tarfile.open(root/'borethm-1.5.0.tar.gz','w:gz') as archive:
        if extra and kind=='sdist':
            member=tarfile.TarInfo('borethm-1.5.0/'+extra)
            member.size=1
            archive.addfile(member,io.BytesIO(b'x'))


@pytest.mark.parametrize('kind,path', [
    ('wheel','borethm/data/forge16a/sanvean_BHA42_10s.csv'),
    ('sdist','validation/forge16a/circulation-primary.csv'),
])
def test_reject_field_archive_payload(tmp_path,kind,path):
    distributions(tmp_path,path,kind)
    with pytest.raises(ValueError,match='must not ship'):
        check.distribution_inventory(tmp_path)


def test_study_modules_are_allowed_and_sizes_are_compared(tmp_path):
    before=tmp_path/'before';before.mkdir()
    after=tmp_path/'after';after.mkdir()
    distributions(before);distributions(after)
    result=check.compare_distributions(after,before)
    for kind in ('wheel','sdist'):
        assert result['current'][kind]['delta_bytes']==0
        assert result['current'][kind]['forge16a_archive_members']==[]
