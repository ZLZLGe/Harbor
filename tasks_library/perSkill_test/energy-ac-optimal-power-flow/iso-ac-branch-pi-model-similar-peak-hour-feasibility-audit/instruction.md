You are supporting the morning peak-hour review desk at an Independent System Operator. The AC operating point for one coastal corridor has already been solved, and your job is to audit that snapshot before it is handed to the reliability engineer.

Use `peak_hour_snapshot.json` as the only input. It provides:

- bus load and voltage limits
- generator dispatch
- branch parameters, including one off-nominal transformer tap and phase shift
- the solved bus voltage magnitudes and angles

Compute the bidirectional AC branch flows for every branch, then write `/root/feasibility_audit.json` with the exact structure below. Use MW, MVAr, and MVA for power quantities, per-unit for voltages, and degrees for angles. Sort `branch_audit` by descending `loading_pct`, and sort `bus_balance` by ascending bus number.

```json
{
  "case_id": "iso-peak-hour-2030-local",
  "summary": {
    "baseMVA": 100.0,
    "total_generation_MW": 355.0,
    "total_generation_MVAr": 40.0,
    "total_load_MW": 351.692256,
    "total_load_MVAr": 170.339857,
    "total_real_losses_MW": 3.307744,
    "total_shunt_reactive_injection_MVAr": 10.201,
    "worst_branch_loading_pct": 115.404383,
    "max_p_balance_residual_MW": 0.0,
    "max_q_balance_residual_MVAr": 0.0,
    "max_voltage_violation_pu": 0.0,
    "max_branch_overload_MVA": 14.634164,
    "overloaded_branch_count": 1
  },
  "branch_audit": [
    {
      "rank": 1,
      "id": "T1",
      "from_bus": 102,
      "to_bus": 103,
      "p_from_MW": -106.640064,
      "q_from_MVAr": -18.814937,
      "s_from_MVA": 108.287142,
      "p_to_MW": 108.692479,
      "q_to_MVAr": 14.338577,
      "s_to_MVA": 109.634164,
      "limit_MVA": 95.0,
      "loading_pct": 115.404383,
      "overload_MVA": 14.634164
    }
  ],
  "bus_balance": [
    {
      "bus": 101,
      "vm_pu": 1.03,
      "va_deg": 0.0,
      "p_generation_MW": 150.0,
      "q_generation_MVAr": 25.0,
      "p_load_MW": 65.499058,
      "q_load_MVAr": 32.275312,
      "p_branch_out_MW": 84.500942,
      "q_branch_out_MVAr": -7.275312,
      "p_balance_residual_MW": 0.0,
      "q_balance_residual_MVAr": 0.0,
      "voltage_violation_pu": 0.0
    }
  ],
  "violations": {
    "overloaded_branches": [
      {
        "id": "T1",
        "from_bus": 102,
        "to_bus": 103,
        "loading_pct": 115.404383,
        "overload_MVA": 14.634164
      }
    ],
    "voltage_violations": []
  }
}
```

The power-balance residual at each bus must be based on the provided dispatch, load, bus shunt terms, and the sum of branch injections leaving that bus. The branch loading check must use the larger apparent flow magnitude of the two directions against `rateA_MVA`.
