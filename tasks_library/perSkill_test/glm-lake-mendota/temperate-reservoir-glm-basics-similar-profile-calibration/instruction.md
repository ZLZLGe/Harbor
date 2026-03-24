Run the General Lake Model for a temperate drinking-water reservoir and calibrate the vertical temperature structure against the provided profile surveys.

The data that you may use includes:
1. Meteorological and hydrological forcing data in `/root/bcs/`
2. Growing-season profile observations in `/root/reservoir_profile_obs.csv`
3. GLM configuration file in `/root/glm3.nml`

Adjust the model parameters so that the RMSE between simulated and observed profile temperatures for April through November is smaller than 1.8 degrees Celsius.

Generate the final simulation output at `/root/output/temperate_profile.nc`.
The verifier will also rerun `glm` with the parameters left in `/root/glm3.nml`, so that file must remain runnable.
