# soultz: breakout formation delay 0 min

Target: 10700.000 m MD. Complete programme: **NO-GO**.

The target drilling-fluid requirement includes the connection checks. The coupled programme evaluates every built-in case. Target SG-equivalents and surface densities have separate columns.

| Case | UCS, MPa | drill_SG, SG-equivalent at target | drill_rho_surface, kg/m3 at 20 C | Target drilling verdict | Target full-cycle verdict |
|---|---:|---:|---:|---|---|
| SHmax lower bound (0.90 Sv), lab UCS 100 | 100 | 1.230037 | 1296.418 | CONDITIONAL | CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 115 | 115 | 1.209457 | 1275.764 | CONDITIONAL | CONDITIONAL |
| SHmax lower bound (0.90 Sv), lab UCS 130 | 130 | 1.188878 | 1255.089 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 100 | 100 | 1.271454 | 1337.918 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 115 | 115 | 1.250875 | 1317.308 | CONDITIONAL | CONDITIONAL |
| SHmax mid-range, lab UCS 130 | 130 | 1.230296 | 1296.678 | CONDITIONAL | CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 100 | 100 | 1.312872 | 1379.333 | NO-GO | NO-GO |
| SHmax upper bound (1.05 Sv), lab UCS 115 | 115 | 1.292293 | 1358.765 | CONDITIONAL | CONDITIONAL |
| SHmax upper bound (1.05 Sv), lab UCS 130 | 130 | 1.271714 | 1338.177 | CONDITIONAL | CONDITIONAL |

| Window | lo / 1000, surface SG at 20 C | Lower bound: state; case; depth | hi / 1000, surface SG at 20 C | Upper bound: state; case; depth | Open |
|---|---:|---|---:|---|---|
| drilling_fluid | 1.378925 | connection; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD | 1.312559 | drilling; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD | False |
| trip_fluid | 1.443624 | trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD | 1.364611 | trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD | False |

## Failing checks

- drilling_fluid: lower 1.378925 surface SG (connection; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD); upper 1.312559 surface SG (drilling; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD). The window is closed.
- trip_fluid: lower 1.443624 surface SG (trip; SHmax upper bound (1.05 Sv), lab UCS 100; 10700.00 m MD); upper 1.364611 surface SG (trip; SHmax lower bound (0.90 Sv), lab UCS 100; 4000.00 m MD). The window is closed.
- target stability, drilling, SHmax upper bound (1.05 Sv), lab UCS 100, 10700.00 m MD: drill_SG = 1.312872; upper limit 1.295986 SG-equivalent at target.
- target stability, trip, SHmax upper bound (1.05 Sv), lab UCS 100, 10700.00 m MD: max(trip_SG, trip_SG_start) = 1.361180; upper limit 1.346274 SG-equivalent at target.
- tool, running in, common programme, 10664.37 m MD: staged.peak = 214.484191; upper limit 200.000000 C.
  Best attempted run-in schedule: peak 201.206715 C; 184 stages, spacing 36.219384 m, 930.6 s per stage. Its peak depth is not returned. The depth above belongs to the practice peak. Schedule found: none.

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
    "form_h": 0.0,
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
  "elapsed_seconds": 57.688438799988944
}
```

Reproduce from the repository root:

```sh
python tools/breakout_timing.py --sites soultz
```
