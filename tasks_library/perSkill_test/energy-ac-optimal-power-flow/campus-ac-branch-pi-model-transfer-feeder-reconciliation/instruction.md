You are reconciling the morning operating snapshot for a campus medium-voltage feeder before the facilities team closes its settlement sheet. The network topology is fixed, but the telemetry combines feeder-head import, distributed generation, and bus-level load measurements that do not line up perfectly.

Use these two input files:

- `campus_feeder_topology.json`
- `campus_operating_snapshot.json`

The topology file provides the feeder buses, shunt terms, and branch parameters. The snapshot file provides:

- the solved bus voltage magnitudes and angles
- the measured bus loads
- the feeder-head import meter at the intertie bus
- the distributed generation measurements at the remaining buses

For each branch, compute the bidirectional AC branch flows implied by the provided voltages and branch data. Aggregate the branch injections leaving each bus, then reconcile each bus with:

- `known injection = feeder-head import + distributed generation`
- `p_residual_MW = p_known_injection_MW - p_load_MW - p_shunt_consumption_MW - p_branch_out_MW`
- `q_residual_MVAr = q_known_injection_MVAr - q_load_MVAr + q_shunt_injection_MVAr - q_branch_out_MVAr`
- `apparent_imbalance_MVA = sqrt(p_residual_MW^2 + q_residual_MVAr^2)`

Write `/root/feeder_reconciliation.json` with the exact structure below. Use MW, MVAr, MVA, per-unit, and degrees as labeled. Round every floating-point value in the output to 6 decimal places.

- Sort `branch_losses` by descending `p_loss_MW`, then descending `q_loss_MVAr`, then ascending branch `id`.
- Sort `bus_reconciliation` by ascending bus number.
- Set `top_imbalances` to the three buses with the largest `apparent_imbalance_MVA`, breaking ties by larger `abs(q_residual_MVAr)` and then smaller bus number.
- Set `rank` in `top_imbalances` from that sorted order.
- In `summary`, `worst_bus` and `worst_apparent_imbalance_MVA` must come from the first item in `top_imbalances`.

```json
{
  "study_id": "campus-feeder-recon-2034-09-15T07:30:00+08:00",
  "summary": {
    "baseMVA": 10.0,
    "bus_count": 6,
    "branch_count": 5,
    "total_measured_load_MW": 17.03,
    "total_measured_load_MVAr": 12.87,
    "total_known_injection_MW": 17.83,
    "total_known_injection_MVAr": 13.75,
    "total_branch_loss_MW": 0.1221,
    "total_branch_loss_MVAr": 0.186249,
    "max_p_residual_MW": 0.155786,
    "max_q_residual_MVAr": 0.699903,
    "worst_bus": 204,
    "worst_apparent_imbalance_MVA": 0.717031
  },
  "branch_losses": [
    {
      "loss_rank": 1,
      "id": "F24",
      "from_bus": 202,
      "to_bus": 204,
      "p_from_MW": 5.865543,
      "q_from_MVAr": 9.902653,
      "s_from_MVA": 11.509437,
      "p_to_MW": -5.801169,
      "q_to_MVAr": -9.681731,
      "s_to_MVA": 11.286695,
      "p_loss_MW": 0.064374,
      "q_loss_MVAr": 0.220922
    }
  ],
  "bus_reconciliation": [
    {
      "bus": 201,
      "name": "Campus Intertie",
      "vm_pu": 1.015,
      "va_deg": 0.0,
      "p_load_MW": 0.08,
      "q_load_MVAr": 0.04,
      "p_feeder_head_import_MW": 6.03,
      "q_feeder_head_import_MVAr": 3.55,
      "p_distributed_generation_MW": 0.0,
      "q_distributed_generation_MVAr": 0.0,
      "p_known_injection_MW": 6.03,
      "q_known_injection_MVAr": 3.55,
      "p_shunt_consumption_MW": 0.0,
      "q_shunt_injection_MVAr": 0.0,
      "p_branch_out_MW": 5.900458,
      "q_branch_out_MVAr": 3.495576,
      "p_residual_MW": 0.049542,
      "q_residual_MVAr": 0.014424,
      "apparent_imbalance_MVA": 0.051599
    }
  ],
  "top_imbalances": [
    {
      "rank": 1,
      "bus": 204,
      "name": "Research Park",
      "p_residual_MW": 0.155786,
      "q_residual_MVAr": 0.699903,
      "apparent_imbalance_MVA": 0.717031
    }
  ]
}
```
