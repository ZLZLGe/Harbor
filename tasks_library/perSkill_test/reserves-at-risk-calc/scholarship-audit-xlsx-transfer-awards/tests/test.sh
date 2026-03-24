#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

if [ -f /root/output/scholarship_audit_result.xlsx ]; then
    cd /root/output
    ssconvert -S scholarship_audit_result.xlsx review.csv >/dev/null 2>&1 || true
fi

cd /root
set +e
python3 -m pytest /tests/test_outputs.py -rA -v
status=$?
set -e

if [ $status -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/output/scholarship_audit_result.xlsx ]; then
    cp /root/output/scholarship_audit_result.xlsx /logs/verifier/
fi
cp /root/output/review.csv.* /logs/verifier/ 2>/dev/null || true

exit 0
