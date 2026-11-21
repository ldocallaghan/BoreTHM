# Which development gaps the 56-32 records cover

The development labels refer to the [gap table](../../../docs/science/model-development.md).
Depth is measured along the well unless marked TVD, which is depth
vertically below the surface. US gal/min is the volume flow rate.
The [condition distributions](56-32-condition-coverage.csv) give
minima, medians and maxima for each set.

| Gap | Condition | Coverage in the 56-32 forecast |
| --- | --- | --- |
| G1, standpipe pressure | A motor can add an off-bottom pressure drop even at zero load. Missing joint and tool losses also affect total pump pressure. | **Measured records.** All 403 uniquely assigned drilling windows use a motor. All 358 development 16A circulation samples and 64 of 109 16B samples use motors. The 56-32 standpipe and differential pressure are already development data. |
| G2, hydraulic heat | Pump work depends on pressure loss and flow. Where the loss occurs determines where heat enters the fluid. | **Calculated.** The 56-32 drilling median is about 670 US gal/min, against 594 for 16A and 603 for 16B. The selected 56-32 motor classes have zero generic no-load allowance under v1.8.0. The matched pressure results can inform heat placement. |
| G3, deep 16A bit temperatures | High rock temperature and high flow make the downhole thermal balance sensitive to the formation boundary and mud. | **Calculated.** The transferred 56-32 formation profile reaches 219.5 °C in the drilling samples, within the upper 16A and 16B coverage. Its median is 160.3 °C, against 192.7 and 182.4 °C. The 56-32 drilling windows range from 641 to 9,115 ft MD, with a median of 6,086 ft. |
| G4, run-in peaks | Static duration, depth and earlier circulation affect the column encountered by the tool. | **Calculated.** There are 45 downward stages from the recorded inputs, 44 from partial trip histories. The 16A development sample contains eleven partial legs, with nine modelled peaks. Run 17 on 16B provides the eight staged trip observations in the Sanvean extract. |
| G5, 16A return temperature | Return heat depends on the formation-to-fluid exchange, inlet and heat generated along the flow path. | **Measured records.** Return measurements are available in all 618 selected 56-32 intervals. Drilling inlet temperature has a median of 38.0 °C, between 16A's 51.1 °C and 16B's 34.8 °C. |
| G6, 16B regular and insulated pipe | The pipe wall resistance and downhole mud affect the thermal difference between the conduits. | **Measured records.** The 56-32 bit workbook labels all recorded runs with water-based mud. No insulated pipe is recorded in the selected 56-32 assemblies. The 16B development set contains 20 full or partial insulated-pipe samples. The 56-32 drilling plastic-viscosity range is 11–40 cP, against 11–20 for 16A and 1–13 for 16B. |

**Inferred.** The [conditional residual ranges](56-32-conditional-residual-ranges.csv)
give an interval for 266 of the 422 return forecasts. The lowest and
highest endpoints across those intervals are −12.0 and +2.9 °C.
The downhole circulation proxy has 260 intervals, with endpoints
from −12.7 to +24.2 °C. The 16A run-in analogues give intervals for
28 of 45 stages, with endpoints from −54.6 to −7.6 °C. Residuals
are modelled minus measured. These envelopes describe overlapping
development cases; they are not calibrated uncertainty intervals.
The available 56-32 MWD readings fall outside the selected windows,
so the downhole ranges give context without a score set. The
pumps-off and restarted temperature series are retained as distinct
measurements in the 16B development set. The 56-32 return window
comparison can test the circulating heat balance.
