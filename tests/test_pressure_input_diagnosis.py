"""Pump-state selections cannot depend on measured pressure."""
import importlib.util
from pathlib import Path
import math
from datetime import datetime, timedelta

SOURCE=Path(__file__).resolve().parents[1]/'validation/model-development/entry-11/diagnostic_rules.py'
spec=importlib.util.spec_from_file_location('entry11_rules',SOURCE)
rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)


def test_full_settling_and_retained_duration():
    assert list(rules.retained_off_indices(list(range(119)),[0]*119,[0]*119))==[]
    assert list(rules.retained_off_indices(list(range(120)),[0]*120,[0]*120))==[list(range(60,120))]


def test_source_time_conversion_has_explicit_seconds():
    origin=datetime(2017,8,5)
    times=[origin+timedelta(seconds=i) for i in range(120)]
    seconds=rules.epoch_seconds(times)
    assert seconds[1]-seconds[0]==1.
    assert list(rules.retained_off_indices(seconds,[0]*120,[0]*120))==[list(range(60,120))]


def test_gap_restarts_settling_and_missing_strokes_are_not_zero():
    seconds=list(range(100))+list(range(103,203))
    assert list(rules.retained_off_indices(seconds,[0]*200,[0]*200))==[]
    p1=[0]*120;p1[60]=math.nan
    assert list(rules.retained_off_indices(list(range(120)),p1,[0]*120))==[]


def test_single_native_slow_period_retained_and_gap_split():
    assert list(rules.spells([0,1,4,5],[True,False,True,True]))==[(0,1),(2,4)]
