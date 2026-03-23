# Repair Report: Capture Ring

Observed issues:

- the resource must be `fd_capring`
- the opener must return `fd_capring`
- `read$capring` must use `ptr[out, array[int8, 64]]`
- `write$capring` must use `ptr[in, array[int8, 64]]`
- `CAPRING_GET_SLOT` has the wrong direction and constant value
- `CAPRING_ENABLE_TRACE` is missing from the constants file

Keep editing until both build commands pass.
