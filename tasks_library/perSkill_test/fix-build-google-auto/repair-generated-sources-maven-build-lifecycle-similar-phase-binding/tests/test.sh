#!/bin/bash
set -u

mkdir -p /logs/verifier

set +e
python3 -m pytest /tests/test_outputs.py -rA -v
test_exit_code=$?
set -e

if [ "$test_exit_code" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

generated_file="/workspace/build-metadata-service/target/generated-sources/build-meta/com/acme/build/BuildMetadata.java"
if [ -f "$generated_file" ]; then
    cp "$generated_file" /logs/verifier/BuildMetadata.java
fi

exit "$test_exit_code"
