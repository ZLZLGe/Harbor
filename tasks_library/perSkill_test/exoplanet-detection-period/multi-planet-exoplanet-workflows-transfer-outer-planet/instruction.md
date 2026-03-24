You are given a TESS light curve for a star with two transiting planets at `/root/data/two_planet_tess_lc.txt`.

The file columns are:

1. Time (MJD, in days)
2. Normalized flux
3. Quality flag (`0` means good cadence)
4. Flux uncertainty

The dominant transit signal comes from a shorter-period inner planet, but your target is the outer planet. Recover the outer planet's orbital period with this workflow:

1. Filter out bad cadences and obvious outliers
2. Remove long-timescale stellar variability while keeping transit-shaped dips
3. Find the strongest inner-planet transit signal, then mask or ignore those transit windows
4. Search the remaining light curve for the outer planet and refine its period

Write the final outer-planet period to `/root/outer_planet_period.txt` in this format:

- A single numerical value in days
- Rounded to exactly 5 decimal places
- No extra text

Example:
```text
9.27463
```
