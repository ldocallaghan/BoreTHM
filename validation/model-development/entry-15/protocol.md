# Entry 15 comparison protocol

The development events are FORGE 16A transients and FORGE 16B run 17. The held-out events in 16B are opened only after the development scores and adoption decision are committed. Temperature targets for 56-32, 58-32 and 78B-32 are reserved for separate validation.

| Measure | Sample | Temperature statistic |
| --- | --- | --- |
| D1 | Eleven 16A run-in legs | Bit-box peak during the leg |
| D2 | Seven 16A legs with a detected restart | Bit-box peak in the first five minutes after pump-on |
| D3 | Each run 17 trip stage, bit and Black Box separately | Stage peak, first-five-minute restart peak and end of following circulation |
| D4 | Eligible run 17 amended pumps-off events, bit and Black Box separately | Rise across the event and first-five-minute restart peak |
| H1 | Eligible Black Box stages on runs 11–16 | As D3 |
| H2 | Eligible bit and Black Box pauses on runs 11–16 | As D4 |
| H3 | Pason EYE TEMP on EOWR staged trips other than run 17, with stages identified using input channels | First reading after pump-on and last reading of the circulation |
| H4 | Zhang et al. (2026), Tables 2 and 3, values already published | Before and after circulation at each stage. Use the instrument named in the daily reports or the MWD if unspecified, and record the assumption. |

For each measure report bias (calculated minus measured), RMSE for the primary configuration in K, fraction of measured values inside the band, and skill as 1 minus the ratio of the new RMSE to the v1.8.0 RMSE. Use identical samples in each paired comparison. Report the v1.8.0 frozen-column calculation, persistence and the undisturbed formation temperature for every measure. The published run 17 RMSEs for stages 1 and 3 were 2.4 and 2.9 °C at the bit and 4.1 and 4.7 °C for the BHA sensor. The comparison was in-sample and the sensor positions were assumed.

The [event index](event-index.csv) records the D1 through D4 and H1
through H2 event and sensor keys. It is generated from recorded timing
and availability flags. This index contains neither target temperatures
nor predictions.
