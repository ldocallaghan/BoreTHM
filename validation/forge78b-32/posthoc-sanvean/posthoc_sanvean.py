"""Post-hoc Sanvean extraction and scoring for 78B-32, written after unsealing.

usage: python posthoc_sanvean.py ARCHIVE [OUTPUT]

The declared extractor read no Sanvean row, because the files write their
times as `2021/06/30 02:06:07.000` and the declared formats include
`%Y/%m/%d %H:%M:%S` without the fraction. This script adds that one format,
`%Y/%m/%d %H:%M:%S.%f`, and then runs the declared Sanvean extraction
(`extract_targets.sanvean`) and the declared Sanvean scoring
(`score_thermal.score_sanvean`, `summarise`, `count`) unchanged. Nothing else
differs from the declared code: the clock alignment, the acceptance
thresholds, R1 to R3, the windows and the predictions are those committed
before unsealing. Writes the targets with their SHA-256 (the readings
gzipped, with the hash of the uncompressed file in `sanvean.csv.sha256`),
the window scores, the summary, the counts and one figure to OUTPUT.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import zipfile

HERE = Path(__file__).resolve().parent
WELL = HERE.parent
sys.path.insert(0, str(WELL/"thermal"))
import extract_targets as ext  # noqa: E402
import score_thermal as sc  # noqa: E402

ADDED_FORMAT = "%Y/%m/%d %H:%M:%S.%f"


def figure(rows, path):
    import math
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    ink, mark, rule = "#2b2b2b", "#2a6fdb", "#9a9a9a"
    plt.rcParams.update({"font.size": 8, "axes.edgecolor": rule, "axes.labelcolor": ink, "xtick.color": ink,
                         "ytick.color": ink, "axes.grid": True, "grid.color": "#e3e3e3", "grid.linewidth": .6})
    scored = [r for r in rows if r["status"] == "scored"]
    if not scored:
        return False
    measured = np.array([r["measured_C"] for r in scored])
    lo, hi = float(measured.min())-2, float(measured.max())+2
    fig, axes = plt.subplots(2, len(sc.MODELS), figsize=(3*len(sc.MODELS), 6.2), sharex=True, sharey=True,
                             squeeze=False)
    for row, position in zip(axes, ("lower", "upper")):
        sub = [r for r in scored if r["position"] == position]
        for ax, model in zip(row, sc.MODELS):
            pairs = [(r["measured_C"], r[f"pred_{model}"]) for r in sub if math.isfinite(r[f"pred_{model}"])]
            if pairs:
                x, y = np.array(pairs).T
                ax.scatter(x, y, s=8, color=mark, alpha=.6, linewidths=0)
            ax.plot([lo, hi], [lo, hi], color=rule, linewidth=1)
            ax.set_title(f"{position} sensor, {model} (n = {len(pairs)})", color=ink)
            ax.set_xlabel("Measured Sanvean temperature, °C")
        row[0].set_ylabel("Predicted temperature, °C")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("archive", type=Path)
    ap.add_argument("output", type=Path, nargs="?", default=HERE)
    ap.add_argument("--skip-hash", action="store_true", help="development only")
    args = ap.parse_args()
    if not args.skip_hash and ext.sha(args.archive) != ext.ARCHIVE_SHA256:
        raise SystemExit("archive hash does not match")
    ext.TIME_FORMATS = (*ext.TIME_FORMATS, ADDED_FORMAT)
    targets = args.output/"targets"
    scores = args.output/"scores"
    targets.mkdir(parents=True, exist_ok=True)
    scores.mkdir(parents=True, exist_ok=True)

    windows_by_id, bins = ext.read_samples(WELL/"thermal"/"samples")
    with zipfile.ZipFile(args.archive) as zf:
        n_rows, report = ext.sanvean(zf, windows_by_id, bins, targets, WELL/"thermal"/"inputs")
    for name in ("sanvean.csv", "sanvean-alignment.json"):
        (targets/f"{name}.sha256").write_text(f"{ext.sha(targets/name)}  {name}\n", encoding="utf-8")

    pred = WELL/"predictions-v1.9.0"
    manifest = json.loads((pred/"manifest.json").read_text())
    for name, digest in manifest["predictions_sha256"].items():
        if sc.sha(pred/name) != digest:
            raise SystemExit(f"{name} differs from the prediction manifest")
    windows = sc.read(WELL/"thermal"/"samples"/"windows.csv")
    predictions = {r["sample_id"]: r for r in sc.read(pred/"predictions.csv")}
    rows, accepted = sc.score_sanvean(windows, predictions, sc.read(targets/"sanvean.csv"), report)
    summary, counts = [], []
    for position in ("lower", "upper"):
        sub = [r for r in rows if r["position"] == position]
        summary += sc.summarise(sub, f"B, Sanvean {position}, post-hoc", grouped=False)
        counts += sc.count(sub, f"B, Sanvean {position}, post-hoc")
    counts += [dict(part="B, Sanvean, post-hoc", count=f"clock alignment accepted, BHA {k}", windows=v)
               for k, v in accepted.items()]
    sc.write(scores/"sanvean-windows.csv", rows)
    sc.write(scores/"summary.csv", summary)
    sc.write(scores/"counts.csv", counts)
    figure(rows, scores/"sanvean-measured-vs-predicted.png")
    # The readings file is large; it is kept gzipped, with the hashes of its content and of the archive.
    plain = targets/"sanvean.csv"
    packed = targets/"sanvean.csv.gz"
    with open(plain, "rb") as src, open(packed, "wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as dest:
        shutil.copyfileobj(src, dest)
    (targets/"sanvean.csv.gz.sha256").write_text(f"{ext.sha(packed)}  sanvean.csv.gz\n", encoding="utf-8")
    plain.unlink()
    print(json.dumps(dict(sanvean_rows=n_rows, alignment={k.rsplit("/", 1)[-1]: v for k, v in report.items()},
                          counts=counts), indent=1, default=str))


if __name__ == "__main__":
    main()
