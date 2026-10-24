"""Exact export comparison rejects numerical changes hidden by Python equality."""
import math
from pathlib import Path
import struct
import sys

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compare_exports import compare


def test_member_order_and_metadata_do_not_change_computed_values():
    result=compare({'values':[1,2.0],'versions':{'python':'a'}},
                   {'versions':{'python':'b'},'values':[1,2.0]})
    assert result['equal']
    assert result['excluded_fields']==[{'path':'/versions','reason':'code/environment provenance'}]
    assert not compare({'versions':1},{'versions':2},excluded=())['equal']


@pytest.mark.parametrize('before,after',[(0.0,-0.0),(1,1.0),(True,1),
    (1.0,math.nextafter(1.0,math.inf)),([1],[1,2]),({'a':1},{}),
    ('1',1),(None,0),(float('inf'),float('-inf'))])
def test_changed_values_types_shapes_or_bits_are_rejected(before,after):
    assert not compare({'result':before},{'result':after})['equal']


def test_decoded_nan_bits_and_escaped_leaf_paths():
    nan=float('nan')
    other=struct.unpack('>d',bytes.fromhex('7ff8000000000001'))[0]
    assert compare({'x':nan},{'x':nan})['equal']
    assert not compare({'x':nan},{'x':other})['equal']
    result=compare({'a/b~c':[0.0]},{'a/b~c':[-0.0]})
    assert result['differences'][0]['path']=='/a~1b~0c/0'


def test_scientific_fields_cannot_be_excluded():
    with pytest.raises(ValueError,match='unsupported exclusion'):
        compare({'result':1},{'result':2},excluded=['/result'])


def test_study_exclusions_are_explicit_and_missing_values_are_reported():
    before={'elapsed_seconds':1.0,'evidence':'old.json','source_sha256':'a','value':2.0}
    after={'elapsed_seconds':2.0,'evidence':'new.json','source_sha256':'b','value':2.0}
    assert not compare(before,after)['equal']
    result=compare(before,after,excluded=['/elapsed_seconds','/evidence','/source_sha256'])
    assert result['equal'] and len(result['excluded_fields'])==3
    assert compare({'versions':{}},{})['equal']
    assert not compare({'result':1},{})['equal']
