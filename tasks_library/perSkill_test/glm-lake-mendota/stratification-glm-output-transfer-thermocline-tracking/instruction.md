Please run the supplied General Lake Model setup for Lake Mendota and track the seasonal thermocline during the 2013 stratification window using the analyst reference file in `/root/manual_thermocline_reference.csv`.

Use these inputs:
1. Meteorological and hydrological forcing data in `/root/bcs/`
2. Analyst thermocline interpretations in `/root/manual_thermocline_reference.csv`
3. The GLM configuration file in `/root/glm3.nml`

Your simulation output must be written to `/root/output/output.nc`.
Then create `/root/output/thermocline_tracking.csv` with one row for every calendar day from `2013-04-29` through `2013-10-29`, sorted by `date`, and these columns in this order:
1. `date`
2. `model_stratified`
3. `model_thermocline_depth_m`
4. `model_max_gradient_c_per_m`
5. `reference_available`
6. `reference_stratified`
7. `reference_thermocline_depth_m`
8. `depth_error_m`
9. `abs_depth_error_m`

When building the tracking table:
1. Use the daily GLM output timestamps inside the requested window
2. Convert GLM layer heights in `output.nc` to depth below the water surface using the lake depth from `/root/glm3.nml`
3. For each day, sort the valid model layers from shallow to deep, compute the temperature gradient between adjacent layers, and choose the pair with the largest positive gradient
4. Mark `model_stratified = 1` only when that maximum positive gradient is at least `1.0` degrees Celsius per meter and the midpoint depth of the selected pair is between `2.0` m and `20.0` m; otherwise use `0` and leave `model_thermocline_depth_m` blank
5. Join the analyst reference file on `date`; keep `reference_available = 1` on referenced dates and `0` otherwise
6. Leave `depth_error_m` and `abs_depth_error_m` blank whenever either the model thermocline depth or the reference thermocline depth is missing
7. Round every numeric output column to 4 decimal places

I will rerun `glm` with your final `/root/glm3.nml`, and the final tracking table must cover the full season with at least 75% matched coverage on stratified reference dates and mean absolute depth error below 3.5 meters.
