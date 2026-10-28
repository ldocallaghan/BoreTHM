# FORGE 56-32 standpipe-pressure comparison

This is the first comparison of BoreTHM's pressure calculation with a well that played no part in its development. The method was registered before any model prediction or target was read: the [protocol](../comparison_protocol.md) at `a1927b3`, its [amendment](../protocol-amendment.md) at `8bbfe2c`, and the [input completion](../input-completion.md) with the primary predictions at `b357326`. Earlier exposure is limited to one BHA sheet's pressure summary, disclosed in the protocol.

## What was compared

Only BHA 9 and BHA 10 have complete inputs, both with the BICO SSS100-B5 motor. That leaves 14 primary off-bottom windows in six events, and 196 secondary on-bottom windows of ten minutes, at 7,219–8,809 ft and 653–686 gal/min. The motor's 475 psi no-load loss has no stated reference flow, so every prediction is an interval: its lower end takes the reference flow as 700 gal/min and its upper end as 300 gal/min. At the secondary windows' flows the interval is about 2,000 psi wide. Residuals are predicted minus measured.

## Results

Secondary windows, target standpipe pressure minus reported differential (median 3,228 psi for BHA 9 and 3,239 psi for BHA 10):

| Calculation | BHA | Windows inside the interval | Lower-end residual, median and range |
|---|---|---|---|
| v1.5.0, PV at 26.7 °C | 9 | 23 of 23 | -1,079 psi (-1,149 to -920) |
| v1.5.0, PV at 26.7 °C | 10 | 173 of 173 | -696 psi (-1,200 to -595) |
| v1.6.0, PV at 48.9 °C (primary) | 9 | 23 of 23 | -295 psi (-355 to -188) |
| v1.6.0, PV at 48.9 °C (primary) | 10 | 65 of 173 | +234 psi (-324 to +357) |
| v1.6.0, PV at 26.7 °C | 9 | 23 of 23 | -439 psi (-514 to -326) |
| v1.6.0, PV at 26.7 °C | 10 | 81 of 173 | +16 psi (-482 to +134) |

As a percentage of the target, the v1.6.0 primary lower end is -9.2% (median) on BHA 9 and +7.2% on BHA 10; v1.5.0's is -33.4% and -21.7%.

Primary off-bottom events, using the median of each event's windows:

| Event | BHA | Bit depth, ft | Measured, psi | v1.5.0 26.7 °C interval | v1.6.0 48.9 °C interval |
|---|---|---|---|---|---|
| off0058 | 9 | 7,424 | 3,298 | 2,192–4,328 | 2,980–5,123 |
| off0059 | 9 | 1,001 | 2,537 | 872–2,039 | 931–2,093 |
| off0064 | 10 | 233–7,646 | 216 | 336–931 | 352–944 |
| off0066 | 10 | 7,932 | 3,193 | 2,546–4,584 | 3,476–5,492 |
| off0068 | 10 | 8,122 | 3,258 | 2,568–4,640 | 3,518–5,571 |
| off0069 | 10 | 8,588 | 3,288 | 2,196–4,244 | 3,087–5,159 |

The full tables are `primary-windows.csv`, `primary-events.csv`, `secondary-windows.csv` and `summary.csv`.

## Points a reader should know

- **Width of the intervals.** The interval is set almost entirely by the motor's unknown reference flow. Every v1.5.0 interval contains the secondary targets because those intervals are wide and sit low. Coverage is therefore a weak test; the lower-end residuals are more informative.
- **Connections.** The NC50 connection scenario adds 620–730 psi to the v1.6.0 standpipe pressure (median change when the restriction length is set to zero). A 58-in restriction adds 150–220 psi more. Most of the difference between v1.5.0 and v1.6.0 comes from this one input, which comes from a catalogue scenario with no measured bore behind it.
- **Surface layout.** Using API case 1 adds about 260 psi to the case-5 prediction, and removing the surface loss takes off about 45 psi.
- **BHA 9 nozzles.** Using the jet-derived area (0.969 in²) lowers BHA 9's prediction by about 130 psi.
- **Mud.** 108 of BHA 10's 173 windows take the 24 February sample, which records a PV of 40 cP between samples of 13 and 14 cP. The registered rule uses it unchanged.
- **Odd primary windows.** Event off0059 is a trip at 1,001 ft whose measured pressure, 1,372–2,540 psi, is above every calculation; event off0064 mixes windows at 233 ft, 3,561 ft and 7,646 ft, and its 3,561-ft window reads 0 psi at 376 gal/min. The original calculation did not converge at that window. These are reported as found.

## Reproduction

```
python validation/forge56-32/compare_pressure.py predict
python validation/forge56-32/compare_pressure.py targets --archive <GDR 1295 ZIP or its 56-32_Pason_Archive.zip>
python validation/forge56-32/compare_pressure.py score
```

`targets.csv` holds the window means of standpipe and differential pressure and their row counts. The nested Pason archive's SHA-256 is `36e142de404b47d9ef812fccfc9fcf80c904fc475cf20089723f51b8166f4463`. Source attribution and licence are in the [extract README](../README.md).
