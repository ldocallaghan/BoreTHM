# soultz: breakout formation delay 60 min

Target: 10700.000 m MD. Complete programme: **NO-GO**.

The target drilling-fluid requirement includes the connection checks. The coupled programme evaluates every built-in case. Target SG-equivalents and surface densities have separate columns.

| Case | UCS, MPa | drill_SG, SG-equivalent at target | drill_rho_surface, kg/m3 at 20 C | Target drilling verdict | Target full-cycle verdict |
|---|---:|---:|---:|---|---|
| SHmax lower bound (0.90 Sv), lab UCS 100 | 100 | 1.092514 | 1154.634 | CONDITIONAL | CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 115 | 115 | 1.069089 | 1130.973 | CONDITIONAL | CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 130 | 130 | 1.045665 | 1107.278 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 100 | 100 | 1.133931 | 1196.394 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 115 | 115 | 1.110507 | 1172.788 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 130 | 130 | 1.087083 | 1149.151 | CONDITIONAL | CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 100 | 100 | 1.175349 | 1238.058 | CONDITIONAL | NO-GO |
| SHmax upper bound (1.05 Sv), lab UCS 115 | 115 | 1.151925 | 1214.506 | CONDITIONAL | CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 130 | 130 | 1.128501 | 1190.924 | CONDITIONAL | CONDITIONAL |

| Window | lo / 1000, surface SG at 20 C | Lower bound: state; case; depth | hi / 1000, surface SG at 20 C | Upper bound: state; case; depth | Open |
|---|---:|---|---:|---|---|
| drilling_fluid | 1.238763 | connection; SHmax upper bound (1.05 Sv), lab UCS 100; 10550.00 m MD | 1.304633 | drilling; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD | True |
| trip_fluid | 1.440962 | trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD | 1.363156 | trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD | False |

## Failing checks

- trip_fluid: lower 1.440962 surface SG (trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD); upper 1.363156 surface SG (trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD). The window is closed.
- target stability, trip, SHmax upper bound (1.05 Sv), lab UCS 100, 10700.00 m MD: max(trip_SG, trip_SG_start) = 1.361809; upper limit 1.346274 SG-equivalent at target.
- tool, running in, common programme, 10664.37 m MD: staged.peak = 214.379989; upper limit 200.000000 C.
  Best attempted run-in schedule: peak 201.211945 C; 184 stages, spacing 36.219384 m, 930.6 s per stage. Its peak depth is not returned. The depth above belongs to the practice peak. Schedule found: none.

Coating qualification: INDETERMINATE; rating 204 C. This is separate from the failing checks above.

## Settings and provenance

```json
{
  "settings": {
    "flow_L_s": 40,
    "pipe": "TK-Drakon coated",
    "shoe_m": 4000.0,
    "pv_fraction": 1.0,
    "coating_rating_C": 204.0,
    "allowance_SG": 0.02,
    "form_h": 1.0,
    "bhp_Pa": null
  },
  "versions": {
    "commit": "6c0613610ae000d5ec173ac69c9a5b6779bb5de4",
    "dirty": false,
    "python": "3.14.4",
    "packages": {
      "numpy": "2.5.3",
      "scipy": "1.18.1",
      "iapws": "1.5.5",
      "matplotlib": "3.11.2"
    }
  },
  "source_sha256": "c6cca213c2ec48998592fee95f71d59eb8dab958940cf154897d6ac45e5b169b",
  "reporting_tool_sha256": "c577ad1569830af9683962bdbe86d8fb41ce5ec39bccd8d1a6c94c1aa61d9498",
  "elapsed_seconds": 80.77729030000046
}
```

Reproduce from the repository root:

```sh
python tools/breakout_timing.py --sites soultz
```
