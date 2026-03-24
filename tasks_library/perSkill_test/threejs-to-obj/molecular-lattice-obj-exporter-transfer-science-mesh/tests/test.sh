#!/bin/bash

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

source "$HOME/.local/bin/env"

mkdir -p /logs/verifier
chmod 777 /logs/verifier

if [ -f "/root/data/lattice.js" ]; then
  cp /tests/gen_ground_truth.mjs /root/gen_ground_truth.mjs
  node /root/gen_ground_truth.mjs
  rm -f /root/gen_ground_truth.mjs
fi

uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  --with numpy==2.1.3 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

status=$?

mkdir -p /logs/verifier/outputs /logs/verifier/expected
if [ -f "/root/output/lattice.obj" ]; then
  cp -f /root/output/lattice.obj /logs/verifier/outputs/lattice.obj
fi
if [ -f "/root/ground_truth/lattice.obj" ]; then
  cp -f /root/ground_truth/lattice.obj /logs/verifier/expected/lattice.obj
fi
if [ -f "/root/ground_truth/lattice_signature.json" ]; then
  cp -f /root/ground_truth/lattice_signature.json /logs/verifier/expected/lattice_signature.json
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
