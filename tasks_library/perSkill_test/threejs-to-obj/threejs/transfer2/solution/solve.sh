#!/bin/bash
set -euo pipefail

mkdir -p /root/output/meshes

cp /root/.codex/skills/threejs/scripts/export_link_objs.mjs /root/export_link_objs.mjs
cp /root/.codex/skills/threejs/scripts/build_urdf_from_scene.mjs /root/build_urdf_from_scene.mjs

node /root/export_link_objs.mjs \
  --input /root/data/transfer2_scene.js \
  --out-dir /root/output/meshes

node /root/build_urdf_from_scene.mjs \
  --input /root/data/transfer2_scene.js \
  --output /root/output/pallet_sorter.urdf \
  --mesh-dir meshes \
  --robot-name pallet_sorter \
  --joint-map /root/data/joint_types.json
