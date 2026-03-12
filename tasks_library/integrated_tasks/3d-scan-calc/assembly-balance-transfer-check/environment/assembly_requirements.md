# Assembly Balance Requirements

Use these requirements when interpreting the scan:

| Rule | Value | Notes |
| :--- | :--- | :--- |
| Minimum Assembly Component Volume (cm^3) | 10.0 | Smaller connected components are scan debris. |
| Footprint X Min (cm) | -0.80 | Inclusive lower bound. |
| Footprint X Max (cm) | 0.80 | Inclusive upper bound. |
| Footprint Y Min (cm) | -0.50 | Inclusive lower bound. |
| Footprint Y Max (cm) | 0.50 | Inclusive upper bound. |

The assembly is balanced if the projected center of mass `(x, y)` lies inside or on all four footprint bounds.
