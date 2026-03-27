#!/bin/bash
set -euo pipefail

cat > /root/transfer2_fuzz.py <<'PY'
import sys
import atheris

atheris.enabled_hooks.add("RegEx")
atheris.enabled_hooks.add("str")

with atheris.instrument_imports():
    from rulematcher import evaluate_rule_line


@atheris.instrument_func
def TestOneInput(data):
    try:
        evaluate_rule_line(data.decode("utf-8", errors="ignore"))
    except Exception:
        return


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
PY

python /root/transfer2_fuzz.py -atheris_runs=25 >/dev/null 2>/root/transfer2_regex_fuzz.log

cat > /root/transfer2_hook_report.txt <<'EOF'
enabled hook: RegEx
enabled hook: str
target function: rulematcher.evaluate_rule_line
EOF
