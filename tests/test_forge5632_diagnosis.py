"""Check the 56-32 shallow-assembly diagnosis scripts and their committed tables.

None of these tests opens GDR 1295. The LAS reader is checked on a small
synthetic file, and the committed tables are checked against the declared
scores they were built from.
"""
import csv
import importlib
import io
import math
from pathlib import Path
import zipfile

import pytest

native = importlib.import_module("validation.forge56-32.diagnosis.native_temperature")
summarise = importlib.import_module("validation.forge56-32.diagnosis.summarise")
surface = importlib.import_module("validation.forge56-32.diagnosis.surface_record")

HERE = Path(native.__file__).resolve().parent
LAS = """~Version Information
 VERS.   2.0 :
 WRAP.   NO  :
~Well Information
 STRT.F  100.0 :START DEPTH
 STOP.F  102.0 :STOP DEPTH
 NULL.   -999.25 :NULL VALUE
 DATE.   17-Aug-2021 :LOG DATE
~Curve Information
 DEPT.F     :Depth
 CBL .MV    :Amplitude
 MTEM.DEGF  :Mud Temperature
~A  DEPT CBL MTEM
 100.0  5.0  68.0
 101.0  6.0  -999.25
 102.0  7.0  212.0
"""


def read(name):
    with open(HERE/name, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_las_reader_drops_nulls_and_reports_the_unit():
    depth, temp, unit, header = native.parse_las(LAS, "MTEM")
    assert list(depth) == [100., 102.]
    assert list(temp) == [68., 212.]
    assert unit == "DEGF"
    assert header["DATE"].startswith("DATE")


def test_stored_member_is_read_from_its_byte_range(tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as z:
        z.writestr("log.las", LAS)
    path = tmp_path/"outer.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("first.txt", "padding")
        z.writestr("inner.zip", inner.getvalue())
    with open(path, "rb") as stream:
        top = zipfile.ZipFile(stream)
        text = zipfile.ZipFile(native.stored(stream, top, "inner.zip")).read("log.las").decode()
    assert text == LAS


def test_temperature_range_rule_matches_the_scoring_protocol():
    assert not surface.valid("return_C", 0.)
    assert surface.valid("return_C", 120.)
    assert not surface.valid("return_C", 120.01)
    assert not surface.valid("inlet_C", math.nan)
    assert surface.valid("flow_gpm", 0.)


def balance(measured, rock_model, conduction, hydraulic):
    return dict(sample_id="x", time="", bha="2", bit_ft="1", inlet_C="10", measured_return_C="50",
                measured_Q_W=measured, rock_model_W=rock_model, conduction_bound_W=conduction,
                hydraulic_W=hydraulic)


@pytest.mark.parametrize("measured, expected", [(1.25*3., "energy-consistent"),
                                                (1.25*3.+1e-6, "energy-inconsistent")])
def test_rule_uses_the_larger_rock_bound_and_the_margin(measured, expected):
    scores = {"x": {"v1.8.0": "20", "v1.8.0_minus_measured_C": "-30"}}
    rows = summarise.classify([balance(measured, 1., 2., 1.)], scores)
    assert rows[0]["rock_bound_W"] == 2.
    assert rows[0]["energy_class"] == expected


def test_window_means_reproduce_the_declared_return_and_inlet():
    """The return is the declared target. The inlet matches the forecast input
    wherever every qualified second is in range; the forecast averaged 10 s
    bins and kept out-of-range readings other than the null value."""
    scored = {r["sample_id"]: r for r in read(HERE.parent/"scores/windows.csv") if r["status"] == "scored"}
    windows = read("window_surface.csv")
    assert {w["sample_id"] for w in windows} == set(scored)
    differ = set()
    for w in windows:
        declared = scored[w["sample_id"]]
        assert float(w["return_C"]) == pytest.approx(float(declared["measured_C"]), abs=1e-9)
        if int(w["inlet_C_seconds"]) == int(declared["qualified_seconds"]):
            assert float(w["inlet_C"]) == pytest.approx(float(declared["inlet_C"]), abs=1e-3)
        elif abs(float(w["inlet_C"])-float(declared["inlet_C"])) > 1e-3:
            differ.add(w["sample_id"])
    assert differ == {"56b-0161", "56b-0172", "56b-0173"}


def test_classification_covers_every_scored_window_once():
    rows = read("classification.csv")
    assert len(rows) == len({r["sample_id"] for r in rows}) == 401
    assert {r["energy_class"] for r in rows} <= {"energy-consistent", "energy-inconsistent"}
