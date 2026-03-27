Build a coverage-guided fuzz driver for the local `zipmanifest` package, which expects compressed manifest bytes.

Save:
- `/root/transfer1_fuzz.py`
- `/root/transfer1_custom_mutator.log`
- `/root/transfer1_summary.json`

Requirements:
- target `zipmanifest.load_manifest`
- use a custom mutator that keeps compressed inputs structurally meaningful
- run the driver long enough to produce an instrumentation log
- write `transfer1_summary.json` with the target function, whether a custom mutator was used, and the log path
