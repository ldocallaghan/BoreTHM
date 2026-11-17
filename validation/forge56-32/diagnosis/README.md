# FORGE 56-32 shallow assemblies: post-hoc diagnosis

## Classification rule (post-hoc)

This rule was written after the declared score was known and after the energy balance in `energy_balance.csv` had been calculated. It was fixed before any window was classified by it.

For each scored window:

- the measured heat gain is Q = ṁ c_p (T_return − T_inlet), from the Pason means over the window's qualified seconds;
- the rock bound is the larger of `rock_model_W` and `conduction_bound_W`;
- the hydraulic heat is the standpipe pressure times the volumetric flow.

A window is **energy-inconsistent** when its measured heat gain exceeds 1.25 times the sum of the rock bound and the hydraulic heat. Otherwise it is **energy-consistent**.

The 25 % margin is for error in the measured heat gain: 10 % for the flow, which comes from pump strokes, and 15 % for the mud density, its heat capacity and the two temperature readings. The rock bound and the hydraulic heat are upper bounds by construction, so no margin is added to them.
