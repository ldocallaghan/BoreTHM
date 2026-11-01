# Catalogue-scenario predictions

These model-only budgets were calculated before Pason pressure-window access. Each directory contains the same 62 planned windows and three calculations as the [primary archive](../model-only/README.md), with one registered catalogue scenario applied. [The protocol](../protocol.md#catalogue-assumptions-and-separate-sensitivities) defines every dimension. No measured pressure appears in these predictions.

`heavy_pipe` uses a 3.240-in ordinary-pipe bore. `wide_joint` uses a 2.688-in internal connection bore. `larger_pipe` uses a 4.500-in ordinary-pipe body with a 3.826-in bore. Every other choice retains its registered setting. The original calculation has no new hydraulic joint objects, so its `wide_joint` result retains its primary geometry.

Each scenario records every seeded convergence status in `window-budget.csv`, component terms in `component-budget.csv` and event reductions in `event-budget.csv` and `event-components.csv`. `starting-profile.csv` gives the additional original-reference checks initialised from the working profile. These checks do not replace seeded failures. The manifest records file hashes and numerical failures.

The [paired-coverage clarification](../coverage-clarification.md) requires all three calculations for every comparison cohort. Scenarios cannot be selected from pressure agreement.
