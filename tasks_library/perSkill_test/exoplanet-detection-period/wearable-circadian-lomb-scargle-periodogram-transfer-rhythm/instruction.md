You are given wearable skin-temperature samples at `/root/data/wearable_skin_temp.csv`.

The file contains these columns:
- `recorded_at`: ISO-8601 timestamp with timezone offset
- `skin_temp_c`: measured wrist skin temperature in degrees C
- `ambient_temp_c`: nearby ambient temperature in degrees C
- `quality_score`: sensor confidence on a 0 to 1 scale
- `wear_state`: keep only rows with `on_wrist`

The record has charging gaps, irregular sampling, and a visible near-12-hour harmonic, but the goal is to recover the main circadian rhythm from the cleaned skin-temperature series.

Use only rows where:
- `wear_state` is `on_wrist`
- `quality_score` is at least `0.82`

Convert the retained timestamps to elapsed hours from the first retained sample. Search periods from `8.0` to `30.0` hours with a sinusoid-plus-constant least-squares periodogram for uneven timestamps.

For a trial period `P`, define the power as:
- `1 - RSS / RSS0`
- `RSS` is the residual sum of squares after fitting `sin(2*pi*t/P)`, `cos(2*pi*t/P)`, and a constant term
- `RSS0` is the residual sum of squares of the retained `skin_temp_c` values around their mean

Use these reporting rules:
- `selected_period_hours`: the strongest periodogram peak between `18.0` and `30.0` hours
- `harmonic_period_hours`: the strongest periodogram peak between `10.5` and `13.5` hours

Write `/root/circadian_note.md` as Markdown with exactly these four non-empty lines:

```md
# Circadian Rhythm Estimate
selected_period_hours: <number rounded to 2 decimals>
harmonic_period_hours: <number rounded to 2 decimals>
reason: <one sentence saying the near-12-hour candidate is weaker than the selected peak and should be rejected as a harmonic>
```

Do not write any extra text outside those four lines.
