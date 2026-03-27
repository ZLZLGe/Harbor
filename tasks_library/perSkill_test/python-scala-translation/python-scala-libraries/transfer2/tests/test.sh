#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if python3 /tests/test_outputs.py /root/libraries_transfer2.scala /root/build.sbt /root/TokenizerSpec.scala --project-dir localtest > /logs/verifier/output.log 2>&1; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit 0
