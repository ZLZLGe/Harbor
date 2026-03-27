Create a coverage-guided fuzz driver for the local `rulematcher` package.

Save:
- `/root/transfer2_fuzz.py`
- `/root/transfer2_regex_fuzz.log`
- `/root/transfer2_hook_report.txt`

Requirements:
- target `rulematcher.evaluate_rule_line`
- treat the input as text data and keep malformed cases non-fatal
- enable the runtime hooks needed for regex-heavy and string-heavy parsing
- run the driver long enough to produce an instrumentation log
- record the enabled hooks and target function in `transfer2_hook_report.txt`
