Build a coverage-guided fuzz driver for the local `dispatchdsl` package.

Save:
- `/root/transfer3_fuzz.py`
- `/root/transfer3_dispatch.log`
- `/root/transfer3_instrumentation_report.md`

Requirements:
- target `dispatchdsl.load_config`
- the loader is imported by the harness bootstrap before setup, so make sure coverage is still visible
- keep malformed text inputs non-fatal
- run the driver long enough to produce an instrumentation log
- explain the instrumentation strategy in `transfer3_instrumentation_report.md`
