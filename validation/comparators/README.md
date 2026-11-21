# Comparators for the reserved thermal measurements

The previous-physics comparator calls BoreTHM with `physics='v1.7.0'`.
All non-physics arguments are the same as for the current calculation.

The analytical circulation comparator solves the forward energy balance
of Kabir et al. with the sample's inlet conditions. Conductances and fluid
properties are evaluated at the sample depth using the v1.8.0 correlations.
The formation gradient follows the line between surface and sample
formation temperatures, divided by measured depth. Rock resistance uses
the Hasan and Kabir dimensionless temperature at the sample's exposure
time. The local conductances are applied to the full well length in this
comparator. Circulation heat generated in the bore or at the bit is absent
from its equations.

For run-in, the undisturbed-formation comparator evaluates formation
temperature at each sensor depth. The persistence comparator repeats
the last reading strictly before the leg begins. It is unavailable when
there is no earlier observation. Persistence can be scored only after
the comparison protocol permits access to the measurements.
