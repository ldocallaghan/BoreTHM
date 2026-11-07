# FORGE 58-32 thermal record availability

The tables inventory the depth and time pressure-temperature logs,
the November survey workbook and the Pason return channel in
[Geothermal Data Repository submission 1006](https://gdr.openei.org/submissions/1006).
They contain dates, depths and counts of available readings.
The availability test checks for a numeric value and excludes the
source null marker.

LAS dates are the header log dates. A clock offset between the logging
tool and Pason has not been established. Time-series depths use the LAS
logger depth where reported. Elapsed time stays relative to the first
point in each LAS time series. The November workbook supplies one
imperial record per depth. Its metric representation is a duplicate.

For the PT dates, the clock calculation uses the last Pason bin above
100 US gal/min and the continuity of flow, inlet temperature and bit
depth on the 10-second input clock. A surface return is measured
continuously. Its source table reports dated availability and simultaneous
input counts, with the age since the last observed circulation
summarised over rows with an available return. A positive age is
time since a reported flow above 100 US gal/min. A long file gap
can make this an upper bound. A later protocol must check the
individual intervals on the input clock.
