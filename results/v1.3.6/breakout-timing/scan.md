# Breakout formation delay scan

The window bounds are surface SG at 20 C. drill_SG is the deciding case's SG-equivalent requirement at the target and includes its connection checks.

| Site | Delay, min | lo / 1000, surface SG | hi / 1000, surface SG | Drilling window open | drill_SG, SG-equivalent at target | Deciding case | Complete programme |
|---|---:|---:|---:|---|---:|---|---|
| soultz | 0 | 1.378925 | 1.312559 | False | 1.312872 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 5 | 1.378925 | 1.312559 | False | 1.312872 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 10 | 1.361320 | 1.313039 | False | 1.295916 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 15 | 1.326528 | 1.313998 | False | 1.261815 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 20 | 1.303416 | 1.314622 | True | 1.239169 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 30 | 1.275969 | 1.314257 | True | 1.211735 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 45 | 1.252765 | 1.304382 | True | 1.189041 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 60 | 1.238763 | 1.304633 | True | 1.175349 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 90 | 1.221937 | 1.304937 | True | 1.158881 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| soultz | 120 | 1.211755 | 1.305123 | True | 1.148904 | SHmax upper bound (1.05 Sv), lab UCS 100 | NO-GO |
| united-downs | 0 | 1.331318 | 1.285186 | False | 1.266726 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 5 | 1.331318 | 1.285186 | False | 1.266726 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 10 | 1.311613 | 1.285694 | False | 1.246006 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 15 | 1.277113 | 1.286534 | True | 1.212521 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 20 | 1.256425 | 1.287063 | True | 1.192516 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 30 | 1.232512 | 1.287685 | True | 1.169358 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 45 | 1.213353 | 1.288193 | True | 1.150741 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 60 | 1.201990 | 1.288498 | True | 1.139667 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 90 | 1.188436 | 1.288862 | True | 1.126464 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |
| united-downs | 120 | 1.180277 | 1.289086 | True | 1.118508 | Reinecker et al. (2021), weak zones, 40 K | NO-GO |

## Critical delay brackets

These brackets describe the first passing sampled drilling-fluid window. The fixed grid has no interpolation or refinement. They do not establish a measured breakout formation time.

- soultz: closed at 15 min; open at 20 min. First passing sampled delay: 20 min.
  Scan wall time: 517.4 s; 8 fresh runs (515.3 s of solves), 2 reused runs. Each JSON trial retains its own original calculation time and provenance.
- united-downs: closed at 10 min; open at 15 min. First passing sampled delay: 15 min.
  Scan wall time: 654.2 s; 8 fresh runs (652.4 s of solves), 2 reused runs. Each JSON trial retains its own original calculation time and provenance.

Reproduce from the repository root:

```sh
python tools/breakout_timing.py
python tools/breakout_timing.py --scan --reuse
```
