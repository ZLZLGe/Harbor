#!/bin/bash
set -euo pipefail

cat > /root/transfer3_fuzz.py <<'PY'
import sys
import atheris

from dispatchdsl import load_config


@atheris.instrument_func
def TestOneInput(data):
    try:
        load_config(data.decode("utf-8", errors="ignore"))
    except Exception:
        return


atheris.instrument_all()
atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
PY

python /root/transfer3_fuzz.py -atheris_runs=25 >/dev/null 2>/root/transfer3_dispatch.log

cat > /root/transfer3_instrumentation_report.md <<'EOF'
# Instrumentation report

- target function: `dispatchdsl.load_config`
- instrumentation strategy: `atheris.instrument_all()` plus `@atheris.instrument_func` on `TestOneInput`
- reason: the dispatcher bootstrap imports helper modules before setup, so explicit global instrumentation keeps branch coverage visible
EOF
