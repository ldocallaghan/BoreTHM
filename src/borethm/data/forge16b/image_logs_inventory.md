# FORGE 16B image logs: inventory and feasibility (GDR 1531)

Source: May, D. and Jones, D. (Schlumberger), 2023. Utah FORGE: Well
16B(78)-32 Logs from Schlumberger Technologies. Geothermal Data Repository,
submission 1531. https://doi.org/10.15121/2001059. CC-BY 4.0. Seven zip files,
24.7 GB in all.

Nothing was downloaded in full. The file listing (`gdr1531_listing.csv`, 168
files) was read from the zips' central directories, and the LAS headers below
from the first part of each member, by HTTP range requests
(`python src/borethm/data/forge16b/build_extracts.py --image-logs`, and `las_header()` in
the same script). Times since drilling come from the Pason record of GDR 1516
(`drilling_history_10min.csv`, the deepest hole against time) and the
inclination from the survey (`survey_16b.csv`).

## The runs

| Run | Tools | Log date | Interval imaged (ft MD) | Logger at bottom | Circulation stopped | Bottom-hole T | Fluid | Source |
|---|---|---|---|---|---|---|---|---|
| 1 | FMI, UBI (main and repeat passes) | 19 May 2023 | 4,840.5 to 6,935.5 (UBI breakout file) | 20:12 | 03:00 | 232 °F | water, 8.3 lb/gal | `UtahForge_Forge16B-78-32_UBI_19May23_BreakoutMain.las` header |
| 2 | FMI, UBI ("Trip2") | 23 May 2023 in the header, 24 May in the file names | 6,643 to 8,590.5 (UBI breakout file) | 09:01 | 12:00 | 272 °F | water, 8.4 lb/gal | `UtahForge_Forge16B-78-32_Trip2_UBI-Breakout.las` header |
| 3 | through-bit FMI (TBFMI) and UBI ("Trip3") | 18 June 2023 | 6,254 to 10,839 (TBFMI); 3,860 to 6,252 in the processed images; UBI 6,252 to 9,444 | 20:30 | 20:30 | 280 °F | water, 8.42 lb/gal | `... TBFMI T3 TOH 6252-10914 DIPS.las` header; processed file names |

- **Datum.** Depths are measured from the kelly bushing, 27 ft above the
  permanent datum at 5,415.6 ft above sea level (headers LMF, APD, EPD). Bit
  size 9.5 in.
- **Logging direction.** The processed images of runs 2 and 3 are labelled TOH
  (logged while pulling out of the hole, upwards from the logger at bottom).
  Run 1's direction is not stated in the files read.
- **Casing.** The 11.75-inch intermediate casing is set at about 4,835 ft
  (the top of run 1's breakout interval, and `SHOE_FT` in
  `validate_forge_pauses.py`). Run 2's top log interval is 60 ft, so it also
  logged inside the casing (the casing-wear comparison), and run 3's
  processed images start at 3,860 ft, inside the casing. Only the intervals
  below 4,835 ft are open hole.
- **Clocks.** The wireline times and the Pason clock may differ by a few hours;
  the times since drilling below are in days and are not sensitive to that.

The breakout LAS files of runs 1 and 2 hold caliper, eccentering and
orientation curves (CDF, CTEM, DCAL, ECCE, ED, GR_EDTC, GTEM, HAZI, HAZIM, ND,
P1AZ, RB, SDEV, SDEVM, STIT, TENS) and no breakout picks. The breakout
widths would have to be read from the images (the `UBI-Breakout` DLIS files
of 549 and 501 MB, or the processed image zips of 0.4 to 1 GB).

## Overlap and time since drilling

Time from when the bit first reached each depth to the logger at bottom of
each run:

| MD (ft) | Inclination | Drilled | Run 1 | Run 2 | Run 3 |
|---|---|---|---|---|---|
| 4,900 | 2° | 11 May 04:10 | 8.7 d |  | 38.7 d |
| 5,250 | 2° | 13 May 10:50 | 6.4 d |  | 36.4 d |
| 5,500 | 0° | 14 May 01:30 | 5.8 d |  | 35.8 d |
| 5,750 | 13° | 14 May 22:50 | 4.9 d |  | 34.9 d |
| 6,000 | 23° | 15 May 19:30 | 4.0 d |  | 34.0 d |
| 6,250 | 29° | 16 May 02:20 | 3.7 d |  | 33.8 d |
| 6,500 | 42° | 16 May 07:50 | 3.5 d |  | 33.5 d |
| 6,650 | 47° | 18 May 01:20 | 1.8 d | 6.3 d | 31.8 d |
| 6,800 | 55° | 18 May 19:00 | 1.1 d | 5.6 d | 31.1 d |
| 6,900 | 62° | 18 May 22:10 | 0.9 d | 5.5 d | 30.9 d |
| 7,200 | 67° | 20 May 11:20 |  | 3.9 d | 29.4 d |
| 7,600 | 66° | 21 May 10:40 |  | 2.9 d | 28.4 d |
| 8,000 | 64° | 21 May 20:00 |  | 2.5 d | 28.0 d |
| 8,400 | 62° | 23 May 06:50 |  | 1.1 d | 26.6 d |
| 8,550 | 61° | 23 May 10:00 |  | 1.0 d | 26.4 d |

- **4,840 to 6,935 ft**, runs 1 and 3: about 1 to 9 days against 31 to 39 days
  after drilling, a ratio of 4 to 34. The hole is near vertical to about
  5,500 ft and builds to 62° by 6,935 ft.
- **6,643 to 6,935 ft**, runs 1 and 2: 0.9 to 1.8 days against 5.5 to 6.3
  days, a ratio of 3.5 to 6, in the build section at 47 to 62°.
- **6,935 to 8,590 ft**, runs 2 and 3: 1 to 4 days against 26 to 30 days, a
  ratio of 7 to 26, on the tangent at 61 to 67°. Here both runs carried the
  UBI, which allows a comparison between the same tool.

## Suitability for paired observations

Two or more runs image the same open-hole interval with times since drilling
that differ by more than a factor of three over about 3,750 ft. This provides
intervals for a possible paired-width comparison. The
best-matched pair is runs 2 and 3 over 6,935 to 8,590 ft, both with the UBI,
on a tangent of nearly constant inclination; runs 1 and 2 add a short
overlap at the shortest times, under two days.

The following limits apply to a paired comparison:

- Most of the overlap is in a hole inclined at 47 to 67°. Breakout widths
  there depend on the hole's orientation in the stress field, so a pair is
  compared at the same depth, and the stability model would need the
  deviated-hole stress concentration to predict either width.
- Run 3 images the deep interval with the through-bit FMI, a different
  resistivity tool from run 1's FMI, and its UBI covers only 6,252 to
  9,444 ft. Pairs should be like for like where possible.
- The hole was circulated between runs, at the temperatures of the IDP trial
  (21 to 29 May) and later bit runs, so the time since drilling is not the
  only difference between the images: the wall's thermal history differs.
  The Pason record gives that history for each depth.
- The image data for the pairs are the UBI breakout DLIS files of runs 1 and 2
  in `Wireline data.zip` (5.1 GB) and run 3's processed images in
  `Processed FMI and UBI.zip` (9.1 GB). The files can be fetched one at a
  time by range requests, as the listing was.
- What the files read do not give: run 1's logging direction, and whether
  Schlumberger or Utah FORGE picked the breakouts in each run (a
  `UBI-Breakout-Customer` DLIS exists for runs 1 and 2). Utah FORGE could
  confirm both, and any breakout interpretation made for 16B.

The [maintenance notes](https://github.com/ldocallaghan/BoreTHM/blob/main/docs/maintenance/development.md#forge-image-log-follow-up) record the proposed follow-up. This inventory does not contain a completed paired breakout-width analysis.
