#!/bin/bash

mkdir -p /logs/verifier

if [ -f /root/bottling-expansion-model.xlsx ]; then
  mkdir -p /tmp/bottling-recalc
  cp /root/bottling-expansion-model.xlsx /tmp/bottling-recalc/bottling-expansion-model.xlsx
  libreoffice --headless --convert-to ods --outdir /tmp/bottling-recalc /tmp/bottling-recalc/bottling-expansion-model.xlsx >/tmp/bottling-recalc/convert1.log 2>&1
  if [ -f /tmp/bottling-recalc/bottling-expansion-model.ods ]; then
    rm -f /root/bottling-expansion-model.xlsx
    libreoffice --headless --convert-to xlsx:"Calc MS Excel 2007 XML" --outdir /root /tmp/bottling-recalc/bottling-expansion-model.ods >/tmp/bottling-recalc/convert2.log 2>&1
  fi
fi

set +e
cd /root
pytest /tests/test_outputs.py -q
TEST_EXIT_CODE=$?
set -e

if [ $TEST_EXIT_CODE -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

if [ -f /root/bottling-expansion-model.xlsx ]; then
  cp /root/bottling-expansion-model.xlsx /logs/verifier/bottling-expansion-model.xlsx
fi

exit 0
