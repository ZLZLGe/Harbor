#!/bin/bash
set -e

apt-get update
apt-get install -y curl

curl -LsSf https://astral.sh/uv/0.9.7/install.sh | sh

source "$HOME/.local/bin/env"

mkdir -p /logs/verifier
chmod 777 /logs/verifier

cp /tests/gen_expected_manifest.mjs /root/gen_expected_manifest.mjs
node /root/gen_expected_manifest.mjs

uvx \
  --with pytest==8.4.1 \
  --with pytest-json-ctrf==0.3.5 \
  pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

status=$?

mkdir -p /logs/verifier/outputs
if [ -d "/root/output/part_meshes" ]; then
  cp -r /root/output/part_meshes /logs/verifier/outputs/
fi
if [ -d "/root/output/merged_parts" ]; then
  cp -r /root/output/merged_parts /logs/verifier/outputs/
fi
if [ -f "/root/output/wind_turbine_manifest.json" ]; then
  cp /root/output/wind_turbine_manifest.json /logs/verifier/outputs/
fi
if [ -f "/root/expected_manifest.json" ]; then
  cp /root/expected_manifest.json /logs/verifier/outputs/
fi

if [ $status -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi

exit $status
