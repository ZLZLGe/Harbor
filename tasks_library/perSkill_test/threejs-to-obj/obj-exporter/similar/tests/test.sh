#!/bin/bash
set -e

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh
source "$HOME/.local/bin/env"

mkdir -p /logs/verifier
chmod 777 /logs/verifier

cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
node /root/gen_ground_truth.mjs
rm -f /root/gen_ground_truth.mjs

uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  --with numpy==2.1.3 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

status=$?

mkdir -p /logs/verifier/outputs /logs/verifier/expected
if [ -f "/root/output/pedestal_showpiece.obj" ]; then
  cp -f /root/output/pedestal_showpiece.obj /logs/verifier/outputs/pedestal_showpiece.obj
fi
if [ -f "/root/ground_truth/pedestal_showpiece.obj" ]; then
  cp -f /root/ground_truth/pedestal_showpiece.obj /logs/verifier/expected/pedestal_showpiece.obj
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
