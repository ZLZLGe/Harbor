import * as THREE from "three";

function beam(length, radius, name) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 14));
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = "bridge_response_kit";

  const deckSegment = new THREE.Group();
  deckSegment.name = "deck_segment";
  root.add(deckSegment);

  const deckPlate = new THREE.Mesh(new THREE.BoxGeometry(4.5, 0.22, 1.8));
  deckPlate.name = "deck_plate";
  deckPlate.position.set(0, 0.11, 0);
  deckSegment.add(deckPlate);

  const edgeRailLeft = beam(4.5, 0.05, "edge_rail_left");
  edgeRailLeft.rotation.z = Math.PI / 2;
  edgeRailLeft.position.set(0, 0.55, -0.75);
  deckSegment.add(edgeRailLeft);

  const edgeRailRight = beam(4.5, 0.05, "edge_rail_right");
  edgeRailRight.rotation.z = Math.PI / 2;
  edgeRailRight.position.set(0, 0.55, 0.75);
  deckSegment.add(edgeRailRight);

  const bracePack = new THREE.Group();
  bracePack.name = "brace_pack";
  bracePack.position.set(0.8, 0.25, -1.6);
  bracePack.rotation.y = -Math.PI / 8;
  root.add(bracePack);

  const braceA = beam(1.8, 0.07, "brace_a");
  braceA.rotation.z = Math.PI / 4;
  bracePack.add(braceA);

  const braceB = beam(1.8, 0.07, "brace_b");
  braceB.rotation.z = -Math.PI / 4;
  bracePack.add(braceB);

  const anchorBlock = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.45, 0.45));
  anchorBlock.name = "anchor_block";
  anchorBlock.position.set(0.1, -0.15, 0);
  bracePack.add(anchorBlock);

  const sensorPost = new THREE.Group();
  sensorPost.name = "sensor_post";
  sensorPost.position.set(-1.9, 0, 1.5);
  root.add(sensorPost);

  const post = beam(2.4, 0.08, "sensor_post_column");
  post.position.set(0, 1.2, 0);
  sensorPost.add(post);

  const sensorHead = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.35, 0.3));
  sensorHead.name = "sensor_head";
  sensorHead.position.set(0.18, 2.35, 0.05);
  sensorPost.add(sensorHead);

  const solarCap = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.05, 0.45));
  solarCap.name = "solar_cap";
  solarCap.position.set(0, 2.55, 0);
  solarCap.rotation.z = 0.2;
  sensorPost.add(solarCap);

  const powerSled = new THREE.Group();
  powerSled.name = "power_sled";
  powerSled.position.set(2.0, 0.18, 1.7);
  powerSled.rotation.y = Math.PI / 6;
  root.add(powerSled);

  const sledBase = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.2, 0.9));
  sledBase.name = "sled_base";
  sledBase.position.set(0, 0.1, 0);
  powerSled.add(sledBase);

  const batteryCase = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.6, 0.6));
  batteryCase.name = "battery_case";
  batteryCase.position.set(-0.25, 0.5, 0);
  powerSled.add(batteryCase);

  const towBar = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.08, 0.12));
  towBar.name = "tow_bar";
  towBar.position.set(0.92, 0.25, 0);
  towBar.rotation.z = 0.08;
  powerSled.add(towBar);

  return root;
}
