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

build_log="/workspace/reactor-release-console/target/verifier-mvn-verify.log"
if [ -f "$build_log" ]; then
    cp "$build_log" /logs/verifier/mvn-verify.log
fi

jar_file="/workspace/reactor-release-console/cli-app/target/cli-app-1.0-SNAPSHOT.jar"
if [ -f "$jar_file" ]; then
    cp "$jar_file" /logs/verifier/cli-app-1.0-SNAPSHOT.jar
fi

exit "$test_exit_code"
