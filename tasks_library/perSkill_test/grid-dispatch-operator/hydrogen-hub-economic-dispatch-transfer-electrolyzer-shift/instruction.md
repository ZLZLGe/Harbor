You are preparing one production shift for a coastal hydrogen hub.

Read these input files:

- `/root/shift_requirements.yaml`
- `/root/electrolyzer_fleet.csv`

Every listed electrolyzer stack is available for the full shift. Choose one scheduled load for each stack so that all of the following hold:

1. For every stack, `min_load_MW <= scheduled_load_MW <= max_load_MW`.
2. Total scheduled load does not exceed `site_power_cap_MW`.
3. Total idle headroom is at least `required_idle_flexibility_MW`, where `idle_headroom_MW = max_load_MW - scheduled_load_MW`.
4. Total hydrogen production is at least `hydrogen_target_kg`, where `hydrogen_kg = scheduled_load_MW * shift_hours * hydrogen_yield_kg_per_MWh`.

Among all feasible shift schedules, minimize total operating cost:

- `stack_cost_dollars = scheduled_load_MW * shift_hours * (power_price_dollars_per_MWh + stack_wear_dollars_per_MWh)`

Write `/root/electrolyzer_shift.md` with exactly these section titles and Markdown tables:

```markdown
# Hydrogen Hub Shift Dispatch

## Shift Summary
| field | value |
| --- | --- |
| hub_name | Lingang Hydrogen Hub |
| shift_label | Night Shift B |
| shift_start | 2026-09-03T22:00:00+08:00 |
| shift_hours | 8.0 |
| hydrogen_target_kg | 5312.0 |
| site_power_cap_MW | 34.0 |
| required_idle_flexibility_MW | 15.0 |

## Stack Dispatch
| stack_id | technology | scheduled_load_MW | hydrogen_kg | stack_cost_dollars | idle_headroom_MW |
| --- | --- | ---: | ---: | ---: | ---: |
| PEM_A | PEM | 7.9 | 1264.0 | 3223.2 | 1.1 |

## Totals
| metric | value |
| --- | --- |
| total_power_MW | 33.9 |
| achieved_hydrogen_kg | 5312.0 |
| total_operating_cost_dollars | 13612.0 |
| reserved_flexibility_MW | 16.1 |
```

Additional output requirements:

- Keep the `Stack Dispatch` rows in the same order as `electrolyzer_fleet.csv`.
- Copy `hub_name`, `shift_label`, and `shift_start` exactly from `shift_requirements.yaml`.
- `hydrogen_kg`, `stack_cost_dollars`, and `idle_headroom_MW` must follow the formulas above for each stack.
- `total_power_MW` must equal the sum of all `scheduled_load_MW` values.
- `achieved_hydrogen_kg` must equal the sum of all `hydrogen_kg` values.
- `total_operating_cost_dollars` must equal the sum of all `stack_cost_dollars` values.
- `reserved_flexibility_MW` must equal the sum of all `idle_headroom_MW` values.
- Use decimal numbers for every numeric table cell.
