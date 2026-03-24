You are given a sparse ground-based transit campaign split into individual nights under `/root/data/nights/`.

Each nightly CSV has the columns:

1. `time_bjd_tdb`
2. `relative_flux`
3. `flux_err`
4. `airmass`
5. `quality_flag` (`0` means usable cadence)

You are also given `/root/data/campaign_manifest.csv`, which lists the observing windows for each night.

The campaign contains irregular cadence, nightly systematics, changing airmass, and several nights with only partial transit coverage. Your job is to combine the nights into one analysis and recover a reproducible transit ephemeris.

Use a workflow like this:

1. Filter unusable cadences and obvious outliers in each night
2. Remove nightly trends without erasing transit-shaped dips
3. Recover the orbital period from the sparse multi-night data
4. Estimate a reference mid-transit time and the set of observed mid-transit times covered by the campaign

Write `/root/ephemeris.json` with this JSON structure:

```json
{
  "period_days": 4.23760,
  "reference_mid_transit_bjd_tdb": 2459821.68829,
  "observed_mid_transits_bjd_tdb": [
    2459821.65375,
    2459825.95959
  ],
  "time_system": "BJD_TDB"
}
```

Requirements:

- `period_days` must be a single numerical value in days
- `reference_mid_transit_bjd_tdb` must be a single numerical value in BJD_TDB
- `observed_mid_transits_bjd_tdb` must be a JSON array of numerical mid-transit times in ascending order
- `time_system` must be the string `"BJD_TDB"`
- Do not write any extra keys
