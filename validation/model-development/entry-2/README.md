# String-loss diagnosis

The component budget implements the entry 2 method in the [development log](../../../docs/science/model-development.md). Select one pressure-available window per assembly at the lower median depth rank, resolving equal depths by time and sample identifier. Selection uses recorded inputs. Each calculation uses the original blind mud convention, plastic viscosity referenced to 26.7 °C and film multiplier 1.0, with the declared NC50/EIS scenarios.

| File | Contents |
|---|---|
| [selected-windows.csv](selected-windows.csv) | Selected sample identifier, time and depth, with flow. |
| [pressure-budget.csv](pressure-budget.csv) | Named bore/annulus terms and total pressure, archived legacy string pressure, string increase and the remaining pressure residual. All pressure columns are psi. `sum_residual_psi` checks arithmetic closure; `scoreboard_difference_psi` checks the repeated candidate calculation. |
| [component-budget.csv](component-budget.csv) | Individual component geometry and its source, with pipe-body friction, connection replacement/local losses and other hydraulic contributions. |
| [manifest.json](manifest.json) | Input selection, settings and checksums. |
| [build_breakdown.py](build_breakdown.py) | Reproducible accounting using the fixed sample plan and shared model functions. |

The component table divides the pressure integral by the component's depth interval. The existing 1-m numerical geometry blend can distribute a boundary contribution into the neighbouring interval. Summing all intervals recovers the same integrated budget. A component crossing a casing shoe has multiple rows, each with its own depth interval. Geometry dimensions refer to the component body; separate columns describe any repeated connection restriction.

`body` denotes straight-passage friction. `joint_replacement` replaces body friction over the connection restriction length, while `joint_local` adds its area-change losses. `geometric_local` represents other changes of passage area. `supplied_local` and `tool` represent explicitly supplied coefficients or tool curves. A zero in a supplied-tool column means no operating-loss curve was specified. It does not demonstrate zero physical tool loss. No proprietary curve is inferred from the residual.

The string and annulus totals, nozzle pressure and signed density-column term are combined with the surface loss. The signed density-column term is a pressure contribution and supplies no frictional heat. Surface loss uses the declared API layout-5 assumption and supplies no downhole heat. Recorded motor differential is handled consistently with the frozen comparison; this diagnosis adds no motor no-load heat or rotary work.
