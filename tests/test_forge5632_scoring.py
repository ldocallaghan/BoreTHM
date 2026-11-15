"""Check the 56-32 return temperature scorer on synthetic targets.

The targets here are built from the committed predictions with known
offsets and noise. They exist only inside each test's temporary folder.
"""
import csv
import importlib
import math
import shutil

import numpy as np
import pytest

score_thermal = importlib.import_module("validation.forge56-32.score_thermal")

OFFSET = 3.
NOISE = .5


def windows():
    return score_thermal.drilling_windows()


def synthetic(seed=7):
    """Measured = v1.8.0 - OFFSET + noise, for every predicted window."""
    rng = np.random.default_rng(seed)
    rows = {}
    for w in windows():
        if not w["predicted"]:
            continue
        mean = w["v1.8.0"]-OFFSET+rng.normal(0., NOISE)
        seconds = 10*w["qualified_bins"]
        rows[w["sample_id"]] = dict(sample_id=w["sample_id"], qualified_bins=w["qualified_bins"],
                                    qualified_seconds=seconds, finite_seconds=seconds,
                                    mean_C=mean, min_C=mean-1., max_C=mean+1.,
                                    unit_conversion=score_thermal.UNIT_CONVERSION)
    return rows


def write_targets(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, score_thermal.TARGET_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows.values())
    return path


def read(path):
    with open(path, encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def summary_row(summary, predictor, set_name="all scored", kind="all", group="all"):
    return next(r for r in summary if r["predictor"] == predictor and r["set"] == set_name
                and r["group_kind"] == kind and r["group"] == group)


def test_forecast_has_the_declared_drilling_windows():
    every = windows()
    assert len(every) == 422
    assert sum(w["predicted"] for w in every) == 402


def test_known_offset_and_noise_are_recovered(tmp_path):
    rows = synthetic()
    summary, _ = score_thermal.score(write_targets(tmp_path/"targets.csv", rows), tmp_path/"scores")
    predicted = {w["sample_id"]: w for w in windows() if w["predicted"]}
    for name in score_thermal.PREDICTORS:
        errors = np.array([predicted[k][name]-rows[k]["mean_C"] for k in rows])
        row = summary_row(summary, name)
        assert row["n"] == 402
        assert row["bias_C"] == pytest.approx(errors.mean(), abs=1e-12)
        assert row["mae_C"] == pytest.approx(np.abs(errors).mean(), abs=1e-12)
        assert row["rmse_C"] == pytest.approx(np.sqrt((errors**2).mean()), abs=1e-12)
        assert row["within_2C"] == pytest.approx((np.abs(errors) <= 2).mean())
        assert row["within_5C"] == pytest.approx((np.abs(errors) <= 5).mean())
    primary = summary_row(summary, "v1.8.0")
    assert abs(primary["bias_C"]-OFFSET) < 4*NOISE/math.sqrt(402)
    assert primary["rmse_C"] == pytest.approx(math.sqrt(OFFSET**2+NOISE**2), rel=.05)
    assert 0. < primary["within_2C"] < .05
    assert primary["within_5C"] == 1.
    for name in ("v1.7.0", "analytical"):
        row = summary_row(summary, name)
        assert row["skill_of_v1.8.0"] == pytest.approx(1-primary["rmse_C"]/row["rmse_C"])
    assert primary["skill_of_v1.8.0"] == ""


def test_groups_partition_the_scored_windows(tmp_path):
    summary, _ = score_thermal.score(write_targets(tmp_path/"targets.csv", synthetic()), tmp_path/"scores")
    for kind in ("assembly", "depth", "flow", "inlet"):
        groups = [r for r in summary if r["group_kind"] == kind]
        assert sum(r["n"] for r in groups) == 402
        assert all(r["predictor"] == "v1.8.0" for r in groups)
    assert len([r for r in summary if r["group_kind"] == "assembly"]) == 10
    for kind in ("depth", "flow", "inlet"):
        assert len([r for r in summary if r["group_kind"] == kind]) == 4


def test_each_exclusion_rule_is_applied_and_listed(tmp_path):
    rows = synthetic()
    ids = sorted(rows)
    seconds = lambda k: rows[k]["qualified_seconds"]
    rows[ids[0]]["finite_seconds"] = math.floor(.8*seconds(ids[0]))-1
    rows[ids[1]]["finite_seconds"] = math.ceil(.8*seconds(ids[1]))
    rows[ids[2]]["min_C"] = -.1
    rows[ids[3]]["max_C"] = 120.1
    rows[ids[4]]["min_C"] = rows[ids[4]]["max_C"] = rows[ids[4]]["mean_C"]
    rows[ids[5]]["finite_seconds"] = 0
    rows[ids[5]]["mean_C"] = rows[ids[5]]["min_C"] = rows[ids[5]]["max_C"] = ""
    rows[ids[6]].update(min_C=0., max_C=120.)
    score_thermal.score(write_targets(tmp_path/"targets.csv", rows), tmp_path/"scores")
    out = {r["sample_id"]: r for r in read(tmp_path/"scores"/"windows.csv")}
    assert out[ids[0]]["status"] == "excluded" and out[ids[0]]["reasons"].startswith("R1")
    assert out[ids[1]]["status"] == "scored"
    assert out[ids[2]]["reasons"].startswith("R2") and out[ids[3]]["reasons"].startswith("R2")
    assert out[ids[4]]["reasons"].startswith("R3")
    assert out[ids[5]]["reasons"].startswith("R1") and out[ids[5]]["measured_C"] == ""
    assert out[ids[6]]["status"] == "scored"
    for k in ids[:6]:
        if k != ids[1]:
            assert out[k]["measured_C"] == "" and out[k]["v1.8.0_minus_measured_C"] == ""
    counts = {r["count"]: int(r["windows"]) for r in read(tmp_path/"scores"/"counts.csv")}
    assert counts["scored"] == 402-5
    assert counts["excluded"] == 5
    assert counts["excluded by R1 finite seconds below 80 % of qualified seconds"] == 2
    assert counts["excluded by R2 value outside 0 to 120 °C"] == 2
    assert counts["excluded by R3 one constant value across the window"] == 1
    summary = read(tmp_path/"scores"/"summary.csv")
    assert int(summary_row(summary, "v1.8.0")["n"]) == 402-5
    not_predicted = [r for r in out.values() if r["status"] == "not predicted"]
    assert len(not_predicted) == 20 and all(r["reasons"] for r in not_predicted)


def test_persistence_uses_the_preceding_scored_window_of_the_assembly(tmp_path):
    rows = synthetic()
    every = sorted((w for w in windows() if w["predicted"]), key=lambda w: w["time"])
    run = [w["sample_id"] for w in every if w["bha"] == "8"]
    rows[run[1]]["finite_seconds"] = 0
    rows[run[1]]["mean_C"] = rows[run[1]]["min_C"] = rows[run[1]]["max_C"] = ""
    summary, _ = score_thermal.score(write_targets(tmp_path/"targets.csv", rows), tmp_path/"scores")
    out = {r["sample_id"]: r for r in read(tmp_path/"scores"/"windows.csv")}
    assert out[run[0]]["persistence"] == ""
    assert out[run[1]]["persistence"] == ""
    assert float(out[run[2]]["persistence"]) == pytest.approx(rows[run[0]]["mean_C"])
    assert float(out[run[3]]["persistence"]) == pytest.approx(rows[run[2]]["mean_C"])
    first = {}
    for w in every:
        first.setdefault(w["bha"], w["sample_id"])
    assert all(out[k]["persistence"] == "" for k in first.values())
    with_persistence = [r for r in summary if r["set"] == "with persistence"]
    assert {r["predictor"] for r in with_persistence} == {"v1.8.0", "v1.7.0", "analytical", "persistence"}
    n = {r["n"] for r in with_persistence}
    assert n == {402-1-len(first)}
    row = next(r for r in with_persistence if r["predictor"] == "persistence")
    primary = next(r for r in with_persistence if r["predictor"] == "v1.8.0")
    assert row["skill_of_v1.8.0"] == pytest.approx(1-primary["rmse_C"]/row["rmse_C"])


@pytest.mark.parametrize("change", ["missing", "extra", "bins", "unit", "columns"])
def test_target_file_errors_stop_the_scoring(tmp_path, change):
    rows = synthetic()
    key = sorted(rows)[0]
    if change == "missing":
        del rows[key]
    elif change == "extra":
        rows["56b-0001"] = dict(rows[key], sample_id="56b-0001")
    elif change == "bins":
        rows[key]["qualified_bins"] += 1
    elif change == "unit":
        rows[key]["unit_conversion"] = "none"
    path = write_targets(tmp_path/"targets.csv", rows)
    if change == "columns":
        text = path.read_text(encoding="utf-8").replace("mean_C", "mean", 1)
        path.write_text(text, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError):
        score_thermal.score(path, tmp_path/"scores")


def test_changed_predictions_are_refused(tmp_path):
    copy = tmp_path/"predictions"
    shutil.copytree(score_thermal.PREDICTIONS, copy)
    text = (copy/"predictions.csv").read_text(encoding="utf-8")
    (copy/"predictions.csv").write_text(text.replace("13.682403641604257", "13.682403641604258"),
                                        encoding="utf-8", newline="")
    with pytest.raises(ValueError):
        score_thermal.drilling_windows(copy)


def test_figures_are_written(tmp_path):
    pytest.importorskip("matplotlib")
    score_thermal.score(write_targets(tmp_path/"targets.csv", synthetic()), tmp_path/"scores")
    for name in ("measured_vs_predicted", "residual_vs_depth", "residual_vs_time", "residual_vs_flow"):
        assert (tmp_path/"scores"/f"{name}.png").stat().st_size > 0
