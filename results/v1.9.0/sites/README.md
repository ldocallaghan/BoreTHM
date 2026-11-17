# Five built-in sites with the v1.9.0 defaults

These results support the [study summary](../../../docs/guides/summary.md). Each built-in site was evaluated on 17 November 2026 with the package defaults, the v1.8.0 physics, at commit `6425460e680555f858971461d5725c3df8af28d7` on `main`.

| File | Contents |
|---|---|
| `soultz.json`, `united-downs.json`, `larderello.json`, `pannonian.json`, `newberry.json` | The full result of each site, as `export_result` writes it |
| `table.json` | The rows that `tests/golden/v180_site_table.json` records, for the same five sites |
| `manifest.json` | The command, code, environment, timings, a comparison with the v1.8.0 golden table and the SHA-256 of every package, input and output file |
| `run_sites.py` | The script that wrote these files |

Every value in `table.json` agrees with `tests/golden/v180_site_table.json` within 1.6e-11 of its own units, so the v1.9.0 defaults reproduce the v1.8.0 results. The manifest records the largest difference for each site.

To repeat the run from the repository root, with the package installed:

```bash
python results/v1.9.0/sites/run_sites.py
```

The run uses four processes, each with one numerical thread, and took about seven minutes.
