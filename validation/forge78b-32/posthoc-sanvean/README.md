# FORGE 78B-32 Sanvean sensors: post-hoc analysis

*Post-hoc, written on 21 November 2026 after the targets were read. It is not part of the declared test.*

The declared extractor ([extract_targets.py](../thermal/extract_targets.py), committed in `13aa9b7`) read no row of the three Sanvean output files, and the declared scorer excluded all 63 windows of each sensor because no clock alignment was found ([counts](../scores/counts.csv)). The files write their times as `2021/06/30 02:06:07.000`, and the declared formats include `%Y/%m/%d %H:%M:%S` without the fraction of a second (measured). Before unsealing only the column headings and row counts of these files had been read, so the format was not checked.

[posthoc_sanvean.py](posthoc_sanvean.py) adds the one format `%Y/%m/%d %H:%M:%S.%f` and runs the declared Sanvean extraction and scoring functions unchanged: the same clock alignment and acceptance thresholds, the same windows and predictions, and rules R1 to R3.

| File | Assembly | Rows | Offset, s | Pump agreement | Overlap bins | Median hole-depth difference, ft |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Forge 14.75 Run 1 | 3 | 76,320 | 10 | 0.996 | 7,599 | 0.0 |
| Forge 14.75 Run 2 | 4 | 50,762 | 10 | 0.998 | 5,077 | 0.0 |
| Forge 10.625 | 15 | 149,675 | 10 | 0.996 | 8,997 | 0.1 |

Each file passes the declared acceptance (agreement at least 0.95, median hole-depth difference at most 5 ft), and all 63 windows of each sensor are scored (calculated).

| Folder | Content |
| --- | --- |
| `targets/` | `sanvean.csv.gz`, the readings in the qualified bins (gzipped; `sanvean.csv.sha256` is the hash of the uncompressed file), and `sanvean-alignment.json`, with their SHA-256 |
| `scores/` | `sanvean-windows.csv`, `summary.csv`, `counts.csv` and `sanvean-measured-vs-predicted.png` |

Rebuild from the repository root:

```bash
python validation/forge78b-32/posthoc-sanvean/posthoc_sanvean.py PATH/1330.zip
```
