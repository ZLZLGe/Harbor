You are given a stitched transit light curve with long observing gaps at `/root/data/alias_validation_lc.txt`.

The file columns are:

1. Time (BJD - 2457000, in days)
2. Normalized flux
3. Quality flag (`0` means usable cadence)
4. Flux uncertainty

You are also given a shortlist of competing period solutions from a first-pass search at `/root/data/candidate_periods.csv`.

Because the observations are split across multiple windows, the shortlist includes obvious `0.5x` and `2x` alias candidates. Your job is to determine which candidate is the true orbital period of the transiting planet.

Use a workflow like this:

1. Filter out bad cadences and obvious outliers
2. Remove long-timescale variability without erasing transit-shaped dips
3. Compare the candidate periods by phase folding and by checking whether predicted transit events stay consistent across the observed windows
4. Confirm the true period and reject the alias solutions

Write the final confirmed period to `/root/validated_period.txt` in this format:

- A single numerical value in days
- Rounded to exactly 5 decimal places
- No extra text

Example:
```text
7.84216
```
