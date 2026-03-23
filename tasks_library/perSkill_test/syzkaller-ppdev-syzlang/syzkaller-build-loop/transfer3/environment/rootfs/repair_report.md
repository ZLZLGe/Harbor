# Repair Report: Bridge Port

The current package still fails validation:

- the resource must be `fd_bridgectl`
- the opener must return `fd_bridgectl`
- `BPORT_QUERY_PORT` must use `ptr[inout, ifreq_t[int16]]`
- `BPORT_GET_INDEX` must use `ptr[out, int32]`
- the `.const` file must use `arches = amd64, 386`
- `BPORT_QUERY_PORT` and `BR_PORT_FLOOD` are wrong or missing in the constants file

Fix the package and rerun the build loop until it passes.
