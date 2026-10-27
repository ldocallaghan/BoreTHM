# V0 protocol amendment review

Prepared after both V0 rulings, before V1 and before target inspection. Starting commit: `a1927b310694eacbd3edc7c4d93c093296e8ab08`.

## Review material

- [Governing amendment](../../forge56-32/protocol-amendment.md): short-window reasoning, interval measures, event weighting and input rulings.
- [56-32 motor mapping](../../forge56-32/motor_mapping.csv): all eleven motors, source identity and exclusions.
- [56-32 archive](../../forge56-32/README.md) and [58-32 archive](../../forge58-32/README.md).
- [58-32 protocol](../../forge58-32/comparison_protocol.md), [motor status](../../forge58-32/motor_mapping.csv) and source locators.
- [Accepted interface](../review-v0/interface.md) and [corrected defaults/sources](../review-v0/sources-and-defaults.md).

The short rule was chosen from operating considerations before counts were calculated. It uses 60 seconds of settling, then non-overlapping 60-second windows, with 10-ft clearance and a 2-ft stationary-bit cut. Events join continuous off-bottom occupancy across movement and pump/flow changes. Window stationarity cannot multiply event samples. Events with conflicting assigned BHAs are excluded. No threshold was chosen using pressure.

The mapping table was shown before this amendment was frozen. All 56-32 BHAs have motors. Its supplied GeoGuidance sheets do not include the recorded 7-in configuration; matching maker alone cannot justify a 6.75-in transfer. Discovery has no published no-load value. The eligible motor curves use the rated-flow endpoint interval, with reference-density assumptions stated in the protocol.

## 56-32 counts

| BHA | Old windows/events | New windows/events | Qualified windows/events | Motor status |
| --- | ---: | ---: | ---: | --- |
| 1 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 2 | 0/0 | 6/3 | 4/3 | eligible with flag |
| 3 | 0/0 | 0/0 | 0/0 | eligible with flag |
| 4 | 0/0 | 38/3 | 0/0 | excluded no matching sheet |
| 5 | 0/0 | 9/1 | 0/0 | excluded no matching sheet |
| 6 | 0/0 | 0/0 | 0/0 | excluded no matching sheet |
| 7 | 0/0 | 0/0 | 0/0 | excluded no matching sheet |
| 8 | 0/0 | 14/2 | 0/0 | excluded no published no load |
| 9 | 0/0 | 18/3 | 5/2 | eligible with flag |
| 10 | 1/1 | 28/4 | 9/4 | eligible with flag |
| 11 | 3/2 | 89/3 | 0/0 | excluded no published no load |
| Unresolved | 14/2 | 476/14 | 0/0 | unresolved |

New-rule exclusion accounting:
- excluded BHA unresolved: 476 windows.
- excluded outside motor rated flow: 21 windows.
- motor interval: 18 windows.
- excluded no matching sheet: 47 windows.
- excluded no published no load: 90 windows.
- excluded event BHA conflict: 26 windows.

Separate rated-flow failures (including overlaps with another exclusion): 35.
Qualified event count: 9.

## 58-32 counts

| BHA | Old windows/events | New windows/events | Qualified windows/events | Motor status |
| --- | ---: | ---: | ---: | --- |
| 1 | 0/0 | 0/0 | 0/0 | motorless reported BHA |
| 2 | 0/0 | 62/7 | 62/7 | motorless reported BHA |
| 3 | 0/0 | 13/3 | 0/0 | excluded unknown maker |
| 4 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 5 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 6 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 7 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 8 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 9 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 10 | 0/0 | 30/7 | 0/0 | excluded unknown maker |
| 11 | 0/0 | 0/0 | 0/0 | motorless reported BHA |
| 12 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 13 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 14 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 15 | 0/0 | 0/0 | 0/0 | excluded motor status unresolved |
| 16 | 0/0 | 0/0 | 0/0 | excluded motor status unresolved |
| 17 | 0/0 | 86/7 | 0/0 | excluded unknown maker |
| 18 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 19 | 0/0 | 0/0 | 0/0 | excluded motor status unresolved |
| 20 | 0/0 | 0/0 | 0/0 | excluded unknown maker |
| 21 | 0/0 | 0/0 | 0/0 | excluded motor status unresolved |
| 22 | 0/0 | 0/0 | 0/0 | excluded motor status unresolved |
| Unresolved | 59/12 | 1894/92 | 0/0 | unresolved |

New-rule exclusion accounting:
- excluded BHA unresolved: 1894 windows.
- motorless primary: 62 windows.
- excluded unknown maker: 129 windows.

Separate rated-flow failures (including overlaps with another exclusion): 0.
Qualified event count: 7.

The short rule identifies motorless rotary BHA 2 windows in 58-32. Reports also identify rotary BHAs 1 and 11, but the conservative interior-day assignment produces no qualified windows for them. Short/incomplete assembly descriptions do not establish motor absence. Missing geometry/catalogue inputs still need completion before either well is numerically scored. The counts above are sampling and motor qualifications, not completed model cases.

## Reproduction and checks

From the repository root, with Python 3.12.14 and pdfplumber 0.11.9:

```powershell
python validation/forge58-32/build_extracts.py --raw PATH_TO_DOWNLOADS
python validation/hydraulics-v160/prepare_pressure_windows.py --data validation/forge56-32 --well 56-32
python validation/hydraulics-v160/prepare_pressure_windows.py --data validation/forge58-32 --well 58-32
python validation/forge56-32/audit_extracts.py --data validation/forge56-32
.venv/Scripts/python.exe tools/check_links.py
git diff --check
```

Input/provenance checks cover finite/null accounting, unique window IDs, non-overlapping windows, rated-flow exclusions and single-BHA event eligibility. No extraction/preparation script imports BoreTHM. An independent 58-32 rebuild is compared by SHA-256, and the original 56-32 generated input files remain byte-identical. The file manifest records the amendment state. The two source archives remain outside the checkout; no 78B source is opened.

API mirror links are removed from current citations, including the earlier S2b report and its report-writing script. These are citation-only edits; archived numerical evidence is unchanged. S2b's recorded historical hashes refer to their original commit. The dual-wall/vacuum hydraulic bores now equal body bores, and the reference collar arithmetic is corrected.

V1 follows the protocol commit. Its execution record supplies that commit hash and the implementation diff. No held-out pressure comparison, golden regeneration, version change, tag, merge or release belongs to this amendment.
