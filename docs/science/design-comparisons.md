# Design comparisons at Soultz and United Downs

No evaluated single-lever setting or evaluated pair made either deep-site programme pass. These are NO-GO results for this programme and these assumptions. Only one pair per site was evaluated; sampled continuous searches do not establish a complete operating envelope. The IDs L1-L8 identify the saved design interventions.

## Evaluation and search

Each new physical setting reruns the reference programme evaluation, including the drilling and trip fluid iteration, ROP and exposure, every depth's common windows and their refinement, tools, coating, pumps and rig capacity. The reference flows are 40 L/s at Soultz and 50 L/s at United Downs, with TK-Drakon pipe and a 4,000 m shoe. Flow stays fixed during L1 to L7. Only L7 changes the immediate-exposure rule. The trip uses a uniform trip-fluid column from its start.

A candidate must pass every physical and numerical prerequisite. Coating qualification may remain explicitly INDETERMINATE. MPD also retains an explicit thermal qualification unknown for its RCD. A failed circulation solve or unsettled depth refinement cannot be a passing bracket. Simulated weights must lie inside every open common window; upward rounding to 0.1 kg/m3 is smaller than the reference 2 kg/m3 iteration tolerance.

The continuous searches sample the base, midpoint and endpoint. L1 also samples the thermal target-pressure bands obtained from those runs. A failing and passing full-site evaluation would trigger bisection and a second search at half the tolerance. No such full-site bracket was found, so there is no confirmed minimum reopening setting. L5's coating-only threshold and Soultz's bit-only flow threshold have retained failing and passing brackets, each checked at half the tolerance. They do not constitute a full-site minimum. Unsearched interior settings remain outside the claim.

L1, L6 and L8 are operating practice. L2 is well design. L3 to L5 concern equipment. L7 is a scientific assumption whose failure-free delay is unsupported by the cited observations.

In the tables, D and T mean drilling and trip. Window widths are upper minus lower in surface SG; a negative width is closed. The fluid columns show the actual simulated weights and the lower-bound demands. A closed window has no valid prescription even when a numerical lower-bound weight is listed. The selected row is the changed setting with the largest narrower-window width among converged, refined trials. L5 uses its refined coating threshold, and Soultz L8 uses its refined bit-only flow threshold. Full trial histories and every setting are linked in each row.

Tool run-in peaks report the best stage schedule attempted. When no schedule passes, the native coating check uses its FORGE-practice fallback. The JSON retains both the best attempted tool peak and the practice peak, together with the coating history's maxima and time above rating.

Empty MPD density families retain finite diagnostic gaps in the JSON. Their negative widths identify a failed intersection; their magnitudes do not give a feasible operating margin. Pair ranking excludes MPD runs with unachievable control. Higher-pressure MPD settings with unsettled depth refinement remain INDETERMINATE.

## Soultz: NO-GO for this programme and these assumptions

Where an upper bound is the same in every stress and strength case, the tables name the first case. In the rows listed here the case named for the upper bound does not set it alone: at Soultz, L2 to L8 and the L2 + L4 pair; at United Downs, L2 to L8 and the L3 + L7 pair. The L1 trials keep no bounds for each case, so their rows are not included.

| Lever | Reopens / minimum | Selected evaluated setting | Binding constraints | Verdict and fluid evaluation | Availability |
|---|---|---|---|---|---|
| L1 constant-BHP MPD | No; none found | BHP 141.575 MPa; [trials](../../results/levers/soultz/L1/summary.json) | trip: lower trip 10700 m (SHmax lower bound (0.90 Sv), lab UCS 100); upper trip 10700 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: drilling_fluid, trip_fluid, wall stability, MPD pressure control / working-pressure rating | NO-GO; D/T widths -0.00051/-0.00249; simulated 1.35947/1.35947 SG; demands 1.35892/1.35892 SG; tool D/connection/run-in 196.15/196.47/197.52 C | Available practice; thermal qualification unknown [1,2] |
| L2 deeper shoe | No; none found | shoe 10200 m; [trials](../../results/levers/soultz/L2/summary.json) | drilling: lower connection 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper drilling 10700 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, drilling_fluid, wall stability | NO-GO; D/T widths -0.01603/+0.00137; simulated 1.37987/1.41110 SG; demands 1.37987/1.41107 SG; tool D/connection/run-in 198.06/198.39/202.84 C | Available casing practice; this geometry unqualified [8] |
| L3 lower PV | No; none found | PV fraction 0.515866; [trials](../../results/levers/soultz/L3/summary.json) | trip: lower trip 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper trip 4000 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.05540/-0.07928; simulated 1.37827/1.44322 SG; demands 1.37832/1.44327 SG; tool D/connection/run-in 197.19/197.51/201.29 C | Hypothetical idealised bound [4] |
| L4 insulated pipe | No; none found | dual-wall; [trials](../../results/levers/soultz/L4/summary.json) | trip: lower trip 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper trip 10700 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: pump limit, rig capacity, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.00978/-0.04285; simulated 1.35113/1.43666 SG; demands 1.35105/1.43658 SG; tool D/connection/run-in 79.79/80.21/125.93 C | Hypothetical as drill pipe [5] |
| L5 coating rating | No; none found | rating 274.342 C (coating only); [trials](../../results/levers/soultz/L5/summary.json) | trip: lower trip 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper trip 4000 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.06637/-0.07901; simulated 1.37884/1.44355 SG; demands 1.37892/1.44362 SG; tool D/connection/run-in 196.99/197.31/201.21 C | Hypothetical at the required cycle rating [3,5] |
| L6 surge / swab | No; none found | allowance 0.010 SG; [trials](../../results/levers/soultz/L6/summary.json) | drilling: lower connection 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper drilling 4000 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.06637/-0.05884; simulated 1.37884/1.43347 SG; demands 1.37892/1.43355 SG; tool D/connection/run-in 196.99/197.31/200.76 C | Available trip-speed control; zero allowance is a bound [7] |
| L7 failure timing | No; none found | formation time 2.00 h; [trials](../../results/levers/soultz/L7/summary.json) | trip: lower trip 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper trip 4000 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, trip_fluid, wall stability | NO-GO; D/T widths +0.09337/-0.07758; simulated 1.21180/1.44045 SG; demands 1.21175/1.44046 SG; tool D/connection/run-in 189.96/190.25/201.21 C | Hypothetical, unsupported delay [6] |
| L8 lower flow | No; none found | flow 39.043 L/s; [trials](../../results/levers/soultz/L8/summary.json) | trip: lower trip 10700 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper trip 4000 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.06480/-0.07958; simulated 1.38070/1.44457 SG; demands 1.38078/1.44465 SG; tool D/connection/run-in 199.72/200.00/203.86 C | Available flow control; tool and cleaning limits apply [9] |

The selected pair is L2 + L4. Its settings are pipe=dual-wall, shoe_m=10200.0. NO-GO; D/T widths -0.00949/+0.00839; simulated 1.35149/1.38580 SG; demands 1.35141/1.38568 SG; tool D/connection/run-in 79.86/80.27/124.45 C. drilling: lower connection 10550 m (SHmax upper bound (1.05 Sv), lab UCS 100); upper drilling 10700 m (SHmax lower bound (0.90 Sv), lab UCS 100). Other failures: pump limit, rig capacity, drilling_fluid, wall stability.

[Pair and ranking evidence](../../results/levers/soultz/PAIR-L2-L4/summary.json). Pair selection ranks the increase in the narrower common pressure-window width in SG. It excludes unconverged or unrefined runs and MPD runs with unachievable control. It keeps other physical gate failures visible. There is one pair evaluation per site; its settings are taken from the single-lever trials and are not jointly optimised.

### Settings evaluated

| Lever | Settings |
|---|---|
| L1 | BHP 139.747 MPa; BHP 141.575 MPa; BHP 143.404 MPa; BHP 140.683 MPa; BHP 140.739 MPa; BHP 140.741 MPa |
| L2 | shoe 4000 m; shoe 7100 m; shoe 10200 m |
| L3 | PV fraction 1.000000; PV fraction 0.515866; PV fraction 0.031732 |
| L4 | TK-Drakon coated; dual-wall; vacuum-insulated (sensitivity) |
| L5 | rating 204.000 C (coating only); rating 300.000 C (coating only); rating 400.000 C (coating only); rating 302.000 C (coating only); rating 253.000 C (coating only); rating 277.500 C (coating only); rating 265.250 C (coating only); rating 271.375 C (coating only); rating 274.438 C (coating only); rating 272.906 C (coating only); rating 273.672 C (coating only); rating 274.055 C (coating only); rating 274.246 C (coating only); rating 274.342 C (coating only); rating 274.294 C (coating only) |
| L6 | allowance 0.040 SG; allowance 0.020 SG; allowance 0.010 SG; allowance 0.000 SG |
| L7 | formation time 0.00 h; formation time 1.00 h; formation time 2.00 h |
| L8 | flow 40.000 L/s; flow 22.500 L/s; flow 5.000 L/s; flow 31.250 L/s; flow 35.625 L/s; flow 37.812 L/s; flow 38.906 L/s; flow 39.453 L/s; flow 39.180 L/s; flow 39.043 L/s |

### Constant-BHP equipment check

The RCD and choke cap is 2,500 psi (17.237 MPa), using Nabors' published onshore dynamic working-pressure class [1]. Surface pressure replaces annular friction at connections and the hot-column loss through the trip. It is added to pump discharge pressure. A choke cannot subtract pressure from an already heavy column. The following pressures are the required nonnegative settings; a control error means the target was not achieved, even if all four pressures fit the hardware cap.

| Target BHP, MPa | D / connection / trip start / trip end SBP, MPa | Maximum nominal column BHP error, MPa | Control and rating pass | Verdict |
|---:|---|---:|---|---|
| 139.747 | 0.000/4.746/0.000/1.908 | 2.352 | False | NO-GO |
| 141.575 | 0.000/5.469/5.469/9.448 | 1.504 | False | NO-GO |
| 143.404 | 19.932/27.973/27.973/31.654 | 0.000 | False | INDETERMINATE |
| 140.683 | 0.000/5.046/1.285/5.342 | 1.937 | False | INDETERMINATE |
| 140.739 | 0.000/5.094/0.938/5.002 | 1.886 | False | INDETERMINATE |
| 140.741 | 0.000/5.088/0.848/4.914 | 1.892 | False | INDETERMINATE |

### Coating threshold and flow boundary

Coating peaks: circulation 199.836 C, connection 200.752 C, run-in 274.318 C. A rating above 274.318 C clears this modeled temperature gate. No stronger-cycle insulating coating was verified [3,5]. Rating changes do not alter the fluid or thermal equations, so L5 reuses the identical full physical evaluation and recalculates the qualification gate and time above each proposed rating. Every reuse links its originating trial.

| Search | Failing rating, C | Passing rating, C | Tolerance, C | Full site verdict |
|---|---:|---:|---:|---|
| first | 274.246094 | 274.341797 | 0.100 | NO-GO |
| half tolerance | 274.293945 | 274.341797 | 0.050 | NO-GO |

Bit-temperature boundary only. Run-in and all remaining site gates are assessed in each trial.

| Bit-only flow search | Failing flow, L/s | Passing flow, L/s | Tolerance, L/s | Full site verdict |
|---|---:|---:|---:|---|
| first | 38.906250 | 39.179688 | 0.500 | NO-GO |
| half tolerance | 38.906250 | 39.042969 | 0.250 | NO-GO |

The 5 L/s trial failed the selected circulation solve. Its downstream gates are INDETERMINATE. None of the evaluated lower-flow settings passed every tool state. A full tool-survival boundary therefore has no confirmed passing endpoint in this range.

## United Downs: NO-GO for this programme and these assumptions

| Lever | Reopens / minimum | Selected evaluated setting | Binding constraints | Verdict and fluid evaluation | Availability |
|---|---|---|---|---|---|
| L1 constant-BHP MPD | No; none found | BHP 164.453 MPa; [trials](../../results/levers/united-downs/L1/summary.json) | trip: lower trip 12857 m (Reinecker et al. (2021), intact, 0 K); upper trip 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, drilling_fluid, trip_fluid, wall stability, MPD pressure control / working-pressure rating | NO-GO; D/T widths -0.00025/-0.00348; simulated 1.27747/1.27747 SG; demands 1.27773/1.27773 SG; tool D/connection/run-in 203.00/203.34/217.95 C | Available practice; thermal qualification unknown [1,2] |
| L2 deeper shoe | No; none found | shoe 12357 m; [trials](../../results/levers/united-downs/L2/summary.json) | drilling: lower connection 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper drilling 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.04534/-0.00282; simulated 1.33197/1.36840 SG; demands 1.33222/1.36865 SG; tool D/connection/run-in 206.72/207.08/224.25 C | Available casing practice; this geometry unqualified [8] |
| L3 lower PV | No; none found | PV fraction 0.515866; [trials](../../results/levers/united-downs/L3/summary.json) | trip: lower trip 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper trip 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.03043/-0.03671; simulated 1.32925/1.40012 SG; demands 1.32942/1.40024 SG; tool D/connection/run-in 204.22/204.58/223.10 C | Hypothetical idealised bound [4] |
| L4 insulated pipe | No; none found | dual-wall; [trials](../../results/levers/united-downs/L4/summary.json) | trip: lower trip 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper trip 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: pump limit, rig capacity, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.03791/-0.04993; simulated 1.30766/1.40036 SG; demands 1.30794/1.40059 SG; tool D/connection/run-in 100.06/100.51/141.49 C | Hypothetical as drill pipe [5] |
| L5 coating rating | No; none found | rating 287.453 C (coating only); [trials](../../results/levers/united-downs/L5/summary.json) | drilling: lower connection 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper drilling 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.04613/-0.03631; simulated 1.33173/1.40116 SG; demands 1.33132/1.40134 SG; tool D/connection/run-in 205.70/206.06/224.48 C | Hypothetical at the required cycle rating [3,5] |
| L6 surge / swab | No; none found | allowance 0.000 SG; [trials](../../results/levers/united-downs/L6/summary.json) | drilling: lower connection 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper drilling 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, drilling_fluid, wall stability | NO-GO; D/T widths -0.04611/+0.00361; simulated 1.33132/1.38130 SG; demands 1.33130/1.38126 SG; tool D/connection/run-in 205.67/206.04/223.42 C | Available trip-speed control; zero allowance is a bound [7] |
| L7 failure timing | No; none found | formation time 1.00 h; [trials](../../results/levers/united-downs/L7/summary.json) | trip: lower trip 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper trip 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, trip_fluid, wall stability | NO-GO; D/T widths +0.08651/-0.03759; simulated 1.20200/1.39883 SG; demands 1.20199/1.39884 SG; tool D/connection/run-in 199.40/199.73/210.35 C | Hypothetical, unsupported delay [6] |
| L8 lower flow | No; none found | flow 27.500 L/s; [trials](../../results/levers/united-downs/L8/summary.json) | drilling: lower connection 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper drilling 6357 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, hole cleaning, drilling_fluid, trip_fluid, wall stability | NO-GO; D/T widths -0.07679/-0.03433; simulated 1.37197/1.41910 SG; demands 1.37198/1.41911 SG; tool D/connection/run-in 269.63/269.86/281.19 C | Available flow control; tool and cleaning limits apply [9] |

The selected pair is L3 + L7. Its settings are pv_fraction=0.5158661751400286, form_h=1.0. NO-GO; D/T widths +0.10196/-0.03788; simulated 1.19960/1.39792 SG; demands 1.19955/1.39793 SG; tool D/connection/run-in 198.33/198.65/208.79 C. trip: lower trip 12857 m (Reinecker et al. (2021), weak zones, 40 K); upper trip 12857 m (Reinecker et al. (2021), intact, 0 K). Other failures: tool, trip_fluid, wall stability.

[Pair and ranking evidence](../../results/levers/united-downs/PAIR-L3-L7/summary.json). Pair selection ranks the increase in the narrower common pressure-window width in SG. It excludes unconverged or unrefined runs and MPD runs with unachievable control. It keeps other physical gate failures visible. There is one pair evaluation per site; its settings are taken from the single-lever trials and are not jointly optimised.

### Settings evaluated

| Lever | Settings |
|---|---|
| L1 | BHP 162.380 MPa; BHP 164.453 MPa; BHP 166.526 MPa; BHP 163.761 MPa; BHP 163.769 MPa; BHP 163.770 MPa |
| L2 | shoe 4000 m; shoe 8179 m; shoe 12357 m |
| L3 | PV fraction 1.000000; PV fraction 0.515866; PV fraction 0.031732 |
| L4 | TK-Drakon coated; dual-wall; vacuum-insulated (sensitivity) |
| L5 | rating 204.000 C (coating only); rating 300.000 C (coating only); rating 400.000 C (coating only); rating 302.000 C (coating only); rating 253.000 C (coating only); rating 277.500 C (coating only); rating 289.750 C (coating only); rating 283.625 C (coating only); rating 286.688 C (coating only); rating 288.219 C (coating only); rating 287.453 C (coating only); rating 287.070 C (coating only); rating 287.262 C (coating only); rating 287.357 C (coating only); rating 287.405 C (coating only) |
| L6 | allowance 0.040 SG; allowance 0.020 SG; allowance 0.010 SG; allowance 0.000 SG |
| L7 | formation time 0.00 h; formation time 1.00 h; formation time 2.00 h |
| L8 | flow 50.000 L/s; flow 27.500 L/s; flow 5.000 L/s |

### Constant-BHP equipment check

The RCD and choke cap is 2,500 psi (17.237 MPa), using Nabors' published onshore dynamic working-pressure class [1]. Surface pressure replaces annular friction at connections and the hot-column loss through the trip. It is added to pump discharge pressure. A choke cannot subtract pressure from an already heavy column. The following pressures are the required nonnegative settings; a control error means the target was not achieved, even if all four pressures fit the hardware cap.

| Target BHP, MPa | D / connection / trip start / trip end SBP, MPa | Maximum nominal column BHP error, MPa | Control and rating pass | Verdict |
|---:|---|---:|---|---|
| 162.380 | 0.000/7.770/0.000/0.000 | 6.381 | False | NO-GO |
| 164.453 | 0.000/10.591/10.591/15.115 | 0.942 | False | NO-GO |
| 166.526 | 0.000/8.099/8.099/12.636 | 3.856 | False | INDETERMINATE |
| 163.761 | 0.000/9.610/5.355/9.974 | 2.008 | False | INDETERMINATE |
| 163.769 | 0.000/9.587/4.483/9.119 | 2.034 | False | INDETERMINATE |
| 163.770 | 0.000/9.584/4.374/9.012 | 2.038 | False | INDETERMINATE |

### Coating threshold and flow boundary

Coating peaks: circulation 208.788 C, connection 209.484 C, run-in 287.445 C. A rating above 287.445 C clears this modeled temperature gate. No stronger-cycle insulating coating was verified [3,5]. Rating changes do not alter the fluid or thermal equations, so L5 reuses the identical full physical evaluation and recalculates the qualification gate and time above each proposed rating. Every reuse links its originating trial.

| Search | Failing rating, C | Passing rating, C | Tolerance, C | Full site verdict |
|---|---:|---:|---:|---|
| first | 287.357422 | 287.453125 | 0.100 | NO-GO |
| half tolerance | 287.405273 | 287.453125 | 0.050 | NO-GO |

No bit-surviving flow among the evaluated flows at or below the base flow.

The 5 L/s trial failed the selected circulation solve. Its downstream gates are INDETERMINATE. None of the evaluated lower-flow settings passed every tool state. A full tool-survival boundary therefore has no confirmed passing endpoint in this range.

## Sources and qualification limits

Sources checked on 11 October 2026. Availability describes the product or practice; it does not certify the proposed deep-site programme.

1. [Nabors Integra MPD](https://www.nabors.com/managed-pressure-drilling/) lists 500 and 2,500 psi dynamic working-pressure classes for its RCD and choke systems. Its page gives no thermal cycle qualification. [SLB RCD 3](https://www.slb.com/products-and-services/innovating-in-oil-and-gas/well-construction/rigs-and-equipment/managed-pressure-drilling-equipment/rotating-control-devices/rcd-3-rotating-control-device-system) separately lists 5,000 psi static, 1,000 psi dynamic at 120 rpm, and 180 F (82.2 C) maximum fluid temperature. These are different products and rating conditions. The Nabors calculation cannot inherit SLB's thermal rating.
2. [Weatherford Set-Point Choke](https://www.weatherford.com/drilling-and-evaluation/managed-pressure-drilling/set-point-choke/) describes maintaining constant BHP during drilling and connections with surface choke control. Its [Kazakhstan onshore case](https://www.weatherford.com/real-results/drilling/pressurepro-set-point-choke%2C-mpd-technology-drilled-2-hole-sections-to-td-in-longest-horizontal%2C-ex/) describes SBP compensating friction losses at connections and swab pressure during trips at 7,320 m measured depth. This supports the practice, with this programme's thermal losses still calculated by the model.
3. [NOV TK-Drakon flyer](https://www.nov.com/-/media/nov/files/products/wbt/tuboscope/tk-drakon/tk-drakon-flyer.pdf), Rev 01 (2024), specifies 400 F (204 C), with an additional circulation-dependent qualification. It does not supply a numerical rating for the full connection and trip cycle above 204 C. The model uses that stated numerical rating. A higher-rated corrosion coating without the same insulating properties would change L5's physical meaning.
4. [Wang and Ding (2021), Scientific Reports](https://pmc.ncbi.nlm.nih.gov/articles/PMC8458390/), Table 3, reports a 1.3 g/cm3 potassium-formate system with PV 35 mPa s before and 30 mPa s after 200 C hot rolling for 16 h. Rheology was measured at 49 C after cooling. This places a high-temperature-aged fluid near the relevant density; it does not establish water-like PV during a 400 C trip. L3 scales the existing mud PV with the yield point unchanged. Its water-PV endpoint, fraction 0.031732, remains an idealised bound.
5. The dual-wall and vacuum-tubing properties remain those in [materials.md](../../data/materials.md). The modeled geometries have no verified availability as drill pipe. [Emissions Reduction Alberta's Pro-Pipe project](https://www.eralberta.ca/projects/details/insulated-drill-pipe-for-enhanced-geothermal-systems-in-super-hot-dry-rock/) describes planned field trials and a 5,000 m string for 2027; its conductivity and construction are unpublished, so it supplies no qualified replacement for the modeled L4 or L5 settings.
6. [Moore et al. (2011)](https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1029/2010GC003417) reports breakouts imaged within minutes and widening at later observations. These observations do not support assuming an hour or two of failure-free cooling in hot crystalline rock. L7 remains a hypothesis, and no other lever receives this delay.
7. [Salih et al. (2024)](https://ijcpe.uobaghdad.edu.iq/index.php/ijcpe/article/view/1186) shows the dependence of surge and swab on trip speed and clearance. Its 9.51 ppg mud and 9.92 ppg closed-string surge ECD example differ by about 0.049 SG at 60 m/min. This is one field-specific calculation, with no basis for a universal 0 to 0.04 SG range at 10 to 13 km. That range is a sensitivity assumption. Zero allowance is an idealised limit; operating procedures require a well-specific transient calculation.

8. [SLB's intermediate-casing definition](https://glossary.slb.com/en/terms/i/intermediate_casing) describes isolating caving and abnormal-pressure intervals so lower formations can use different fluid weights. This establishes the casing practice. L2 changes only the modeled shoe depth; it does not qualify the casing string's mechanical design or cement placement at the proposed depth.
9. [NOV 14-P-220 technical marketing sheet](https://www.nov.com/media/nov/files/products/rig/rig-equipment/mud-pumps-fluid-mixing-and-processing-systems/14p220-triplex-mud-pump-spec-sheet.pdf) publishes flow at several pump speeds and liner sizes. This is the available equipment basis for varying flow and the existing pressure-dependent rig-capacity check in [materials.md](../../data/materials.md).

### Barite source check

[API's 2023 licensing form](https://www.api.org/-/media/files/certification/monogram-apiqr/0_api-monogram-apiqr/lifs/api_13a_licensing_information_form_20230821.pdf) identifies the barite 4.2 grade used for the 4,200 kg/m3 reference component. [Robie and Hemingway, USGS Bulletin 2131](https://pubs.usgs.gov/bul/2131/report.pdf), printed page 284, gives 101.75 J/mol K at 298.15 K and formula weight 233.391 g/mol, or 435.964 J/kg K. This supports the model's rounded 436 J/kg K at room temperature; the source table increases with temperature, so the constant heat capacity is an approximation.

[Ye et al. (2019)](https://www.hpstar.ac.cn/hpstar_old/upload/files/2019/7/6b7b5a74ff731d99.pdf), printed page 614, fits barite volumetric expansion as 2.52e-5 + 5.25e-8 T per K over 300 to 700 K. It gives about 4.09e-5 at 300 K and 6.20e-5 at 700 K. The code's constant 5e-5 per K is an approximation across that interval. The study retains the reference component-property laws and the mass-conserving composition.

## Evidence and reproduction

The [reviewed trial outputs](../../results/levers/) and their [manifest](../../results/levers/manifest.json) retain all settings and brackets. Fresh release evidence is documented in the [v1.3.4 release verification](../releases/v1.3.4.md). The [historical review](../archive/v1.3.4/design-review.md) records implementation and testing history.

From the repository root, use `python src/levers.py --sites soultz united-downs --levers L1 L2 L3 L4 L5 L6 L7 L8`, followed by `python src/lever_flow_limit.py` and `python src/lever_pairs.py`, to reproduce the study. These are lengthy physical calculations. The [maintenance priorities](../maintenance/development.md) record the already-met timeline trigger and the reason for deferral.
