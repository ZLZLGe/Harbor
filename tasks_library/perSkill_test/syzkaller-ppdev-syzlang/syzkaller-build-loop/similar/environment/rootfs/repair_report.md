# Repair Report: Parallel Diagnostics

The shipped package is broken. `make descriptions` fails because the current files have multiple issues:

- the resource name should be `fd_ppdiag`
- the opener should return `fd_ppdiag`
- `PPDIAG_GETMODE` must use `ptr[out, int32]`
- `PPDIAG_SETMODE` must use `ptr[in, flags[ppdiag_modes, int32]]`
- `PPDIAG_FROB` must use `ptr[in, ppdiag_window]`
- the `.const` file must use `arches = amd64, 386`
- `PPDIAG_RELEASE`, `PPDIAG_GETMODE`, `PPDIAG_SETMODE`, and `PPDIAG_FROB` are missing or wrong in the current constants file

Keep iterating until both `make descriptions` and `make all` pass.
