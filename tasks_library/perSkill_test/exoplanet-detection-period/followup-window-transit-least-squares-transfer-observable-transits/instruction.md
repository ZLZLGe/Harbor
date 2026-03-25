Analyze the discovery light curve at `/root/data/followup_lightcurve.csv` and the future visibility windows at `/root/data/visibility_windows.json`.

The light-curve CSV contains these columns:
- `time_bjd`: observation time in BJD_TDB days
- `flux`: normalized stellar flux
- `flux_err`: 1-sigma flux uncertainty
- `quality`: cadence quality flag, where `0` means usable data
- `segment_id`: observing block label

The visibility JSON is an array of window objects. Each object contains:
- `window_id`
- `start_bjd`
- `end_bjd`
- `site`

This target has one transiting planet, but the light curve also includes low-frequency stellar variability, scattered outliers, and several data gaps. Recover the planet ephemeris from the light curve, then forecast which future mid-transits fall inside the allowed visibility windows.

Write `/root/observable_transits.json` as a JSON object with exactly these keys:
- `period_days`: the recovered orbital period in days
- `t0_bjd`: the first modeled mid-transit time, in BJD_TDB days, that falls within the retained `quality == 0` light-curve time range
- `observable_transits`: an array of the predicted future transits whose mid-transit times fall inside one of the visibility windows

Each object in `observable_transits` must contain exactly these keys:
- `window_id`: the matching visibility-window identifier
- `transit_number`: the non-negative integer cycle count satisfying `mid_transit_bjd = t0_bjd + transit_number * period_days`
- `mid_transit_bjd`: the predicted mid-transit time in BJD_TDB days

Additional requirements:
- Enumerate predicted mid-transits from the earliest visibility-window start through the latest visibility-window end
- Keep only mid-transits that fall inside a listed visibility window, using inclusive window bounds
- Sort `observable_transits` by ascending `mid_transit_bjd`
- Round every reported floating-point value to 5 decimal places
- Do not include any extra keys

Example format:
```json
{
  "period_days": 7.12345,
  "t0_bjd": 2461001.23456,
  "observable_transits": [
    {
      "window_id": "WIN-02",
      "transit_number": 8,
      "mid_transit_bjd": 2461058.22216
    }
  ]
}
```
