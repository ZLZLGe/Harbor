# Feedstock Waste Factors

Use this table to estimate how much incoming material is lost during purge, support removal, and setup for each material.

| Material ID | Waste Factor | Process Note |
| :--- | :--- | :--- |
| **1** | 0.50 | Debris and dust are mostly discarded. |
| **10** | 0.08 | Steel runs have moderate powder reclaim loss. |
| **25** | 0.06 | Aluminum trimming losses are comparatively low. |
| **42** | 0.12 | Proprietary alloy jobs require extra purge and calibration stock. |
| **99** | 0.15 | Lead setup uses a larger discard allowance. |

## Formula

`Required Feedstock Mass = Net Part Mass / (1 - Waste Factor)`

`Estimated Waste Mass = Required Feedstock Mass - Net Part Mass`

The waste factor is a fraction of incoming feedstock mass lost before the finished part is complete.
