#!/bin/bash
set -euo pipefail

cat > /root/transfer1_fuzz.py <<'PY'
import json
import sys
import zlib

import atheris

with atheris.instrument_imports():
    from zipmanifest import load_manifest


@atheris.instrument_func
def TestOneInput(data):
    try:
        load_manifest(data)
    except Exception:
        return


def CustomMutator(data, max_size, seed):
    try:
        raw = zlib.decompress(data)
    except zlib.error:
        raw = b'{"route":"/healthz","metadata":{"owner":"ops","critical":false},"retries":1}'
    mutated = atheris.Mutate(raw, max_size)
    try:
        json.loads(mutated.decode("utf-8"))
        payload = mutated
    except Exception:
        payload = b'{"route":"/admin/reindex","metadata":{"owner":"ops","critical":true},"retries":5}'
    return zlib.compress(payload)


atheris.Setup(sys.argv, TestOneInput, custom_mutator=CustomMutator)
atheris.Fuzz()
PY

python /root/transfer1_fuzz.py -atheris_runs=25 >/dev/null 2>/root/transfer1_custom_mutator.log

python - <<'PY'
import json
from pathlib import Path

Path("/root/transfer1_summary.json").write_text(
    json.dumps(
        {
            "target_function": "zipmanifest.load_manifest",
            "uses_custom_mutator": True,
            "log_file": "/root/transfer1_custom_mutator.log",
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY
