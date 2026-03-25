# Scenario briefs

## city_accelerometer_watch
The city emergency office only needs a fast first-stage screen for larger felt shaking before staff review. The network is built from accelerometers, and the deployment is intentionally lightweight so each district gateway can run simple logic with minimal CPU.

## dam_regulatory_audit
This reservoir monitoring contract is inspected by regulators and every published event bulletin must be defensible. Event volume is low enough that analysts can review everything, and the client is far more concerned about false positives than about squeezing out every extra tiny event automatically.

## temp_nodal_aftershocks
This temporary nodal deployment was installed after a damaging mainshock in an area with sparse permanent coverage. The team wants an automatically generated local aftershock catalog from continuous waveforms, but there is no mature library of template events yet.

## template_swarm_archive
The geothermal swarm has already produced hundreds of well-vetted repeating families. Overnight processing on an offline server is acceptable because the priority is maximum sensitivity to the smallest recurring events within this known cluster.
