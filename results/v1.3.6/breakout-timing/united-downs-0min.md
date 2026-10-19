# united-downs: breakout formation delay 0 min

Target: 12857.143 m MD. Complete programme: **NO-GO**.

The target drilling-fluid requirement includes the connection checks. The coupled programme evaluates every built-in case. Target SG-equivalents and surface densities have separate columns.

| Case | UCS, MPa | drill_SG, SG-equivalent at target | drill_rho_surface, kg/m3 at 20 C | Target drilling verdict | Target full-cycle verdict |
|---|---:|---:|---:|---|---|
| Reinecker et al. (2021), intact, 0 K | 203 | 1.169343 | 1234.369 | CONDITIONAL | CONDITIONAL |
| Reinecker et al. (2021), intact, 40 K | 172 | 1.204859 | 1269.879 | CONDITIONAL | CONDITIONAL |
| Reinecker et al. (2021), weak zones, 0 K | 147 | 1.233501 | 1298.465 | NO-GO | NO-GO |
| Reinecker et al. (2021), weak zones, 40 K | 118 | 1.266726 | 1331.571 | NO-GO | NO-GO |

| Window | lo / 1000, surface SG at 20 C | Lower bound: state; case; depth | hi / 1000, surface SG at 20 C | Upper bound: state; case; depth | Open |
|---|---:|---|---:|---|---|
| drilling_fluid | 1.331318 | connection; Reinecker et al. (2021), weak zones, 40 K; 12857.14 m MD | 1.285186 | drilling; Reinecker et al. (2021), intact, 0 K; 12857.14 m MD | False |
| trip_fluid | 1.401337 | trip; Reinecker et al. (2021), weak zones, 40 K; 12857.14 m MD | 1.365025 | trip; Reinecker et al. (2021), intact, 0 K; 12857.14 m MD | False |

## Failing checks

- drilling_fluid: lower 1.331318 surface SG (connection; Reinecker et al. (2021), weak zones, 40 K; 12857.14 m MD); upper 1.285186 surface SG (drilling; Reinecker et al. (2021), intact, 0 K; 12857.14 m MD). The window is closed.
- trip_fluid: lower 1.401337 surface SG (trip; Reinecker et al. (2021), weak zones, 40 K; 12857.14 m MD); upper 1.365025 surface SG (trip; Reinecker et al. (2021), intact, 0 K; 12857.14 m MD). The window is closed.
- target stability, drilling, Reinecker et al. (2021), weak zones, 0 K, 12857.14 m MD: drill_SG = 1.233501; upper limit 1.220205 SG-equivalent at target.
- target stability, drilling, Reinecker et al. (2021), weak zones, 40 K, 12857.14 m MD: drill_SG = 1.266726; upper limit 1.220205 SG-equivalent at target.
- target stability, trip, Reinecker et al. (2021), weak zones, 40 K, 12857.14 m MD: max(trip_SG, trip_SG_start) = 1.324449; upper limit 1.300370 SG-equivalent at target.
- tool, drilling, common programme, 12857.14 m MD: T = 205.702192; upper limit 200.000000 C.
- tool, connection, common programme, 12857.14 m MD: peak = 206.064902; upper limit 200.000000 C.
  The schedule search was skipped because the drilling tool temperature exceeds its limit.
- tool, running in, common programme, 12837.53 m MD: staged.peak = 224.475803; upper limit 200.000000 C.
  Best attempted run-in schedule: peak 224.475803 C; 61 stages, spacing 144.877536 m, 930.6 s per stage. Its peak depth is not returned. The depth above belongs to the practice peak. Schedule found: none.
  The schedule search was skipped because the drilling tool temperature exceeds its limit.

Coating qualification: INDETERMINATE; rating 204 C. This is separate from the failing checks above.

## Settings and provenance

```json
{
  "settings": {
    "flow_L_s": 50,
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
  "elapsed_seconds": 52.72136920003686
}
```

Reproduce from the repository root:

```sh
python tools/breakout_timing.py --sites united-downs
```
