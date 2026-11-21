# FORGE 56-32 model-only forecast

The [thermal protocol](../thermal_protocol.md) defines the sample
selection and equations. The [conditions table](conditions.csv)
identifies each sample and the measured inputs used for both presets.
It records temperature availability as counts only. The
[model-only predictions](predictions.csv) are independent of the
reserved thermal values.

The current and previous calculations use the same recorded geometry
and operating inputs, with their respective heat-transfer and loss
treatments. On drilling rows, the three circulation predictions include
bit bore temperature, the 84 ft above-bit bore proxy and surface
return. For a pause or trip, circulation outputs refer to the preceding
circulation. Where that profile and the transient inputs are available,
the two BoreTHM presets also give an event peak at the tool proxy.
The analytical column reports the preceding circulation reference for
an event. The formation comparator reports the temperature at the
run-in sensor proxy's final depth.

Input and package-file hashes are in the [manifest](manifest.json).
The [availability source](source-availability.json) identifies the
raw archive used for finite/null counts. Blank numerical fields have
a reason in the calculation or input status, or indicate that the
quantity is outside the comparator's equations. The persistence
comparator requires an earlier observed sensor value.
