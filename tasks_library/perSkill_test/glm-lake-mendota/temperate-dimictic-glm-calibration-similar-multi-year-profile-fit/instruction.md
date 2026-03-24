Please run the General Lake Model to simulate the vertical water temperature for a temperate dimictic deep lake over the 2010-01-01 to 2015-12-30 period. The overall RMSE between the observation profiles and the simulation should be smaller than 1.8 degrees Celsius.

The data that you may use includes:
1. Meteorological and hydrological forcing data in `/root/forcing/`
2. Screened field profile observations in `/root/deep_profile_obs.csv`
3. GLM configuration file in `/root/glm3.nml`

You should generate the simulation output at `/root/output/dimictic_profile.nc`.
In addition, I will check that GLM can run successfully with the parameters you used, so keep your final calibrated parameters saved in `/root/glm3.nml`.
