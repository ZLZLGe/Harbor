# Repair Report: Sensor Hub

Current build notes:

- the resource must be `fd_sensorhub`
- the opener must return `fd_sensorhub`
- `SNS_GET_SNAPSHOT` must use `ptr[out, sensor_snapshot]`
- `SNS_SET_THRESH` must use `ptr[in, sensor_threshold]`
- `sensor_modes` must list `SENSOR_MODE_IDLE, SENSOR_MODE_FAST, SENSOR_MODE_STREAM`
- the `.const` file must use `arches = amd64, 386`
- `SNS_SET_MODE` currently has the wrong numeric value
- `SENSOR_MODE_STREAM` is missing

Fix the package until `make descriptions` and `make all` both succeed.
