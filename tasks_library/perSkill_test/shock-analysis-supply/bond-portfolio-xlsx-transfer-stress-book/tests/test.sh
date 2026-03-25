#!/bin/bash

mkdir -p /logs/verifier

if [ -f /root/bond-stress-book.xlsx ]; then
  mkdir -p /tmp/bond-stress-verify /root/bond-stress-verify-out
  cp /root/bond-stress-book.xlsx /tmp/bond-stress-verify/bond-stress-book.xlsx
  libreoffice --headless --convert-to ods --outdir /tmp/bond-stress-verify /tmp/bond-stress-verify/bond-stress-book.xlsx >/tmp/bond-stress-verify/convert1.log 2>&1
  if [ -f /tmp/bond-stress-verify/bond-stress-book.ods ]; then
    libreoffice --headless --convert-to xlsx:"Calc MS Excel 2007 XML" --outdir /root/bond-stress-verify-out /tmp/bond-stress-verify/bond-stress-book.ods >/tmp/bond-stress-verify/convert2.log 2>&1
    if [ -f /root/bond-stress-verify-out/bond-stress-book.xlsx ]; then
      cp /root/bond-stress-verify-out/bond-stress-book.xlsx /root/bond-stress-book.xlsx
    fi
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

if [ -f /root/bond-stress-book.xlsx ]; then
  cp /root/bond-stress-book.xlsx /logs/verifier/bond-stress-book.xlsx
fi

exit 0
