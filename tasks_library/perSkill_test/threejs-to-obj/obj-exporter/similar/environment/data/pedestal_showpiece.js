import * as THREE from "three";

export function createScene() {
  const root = new THREE.Group();
  root.name = "pedestal_showpiece";

  const pedestalAssembly = new THREE.Group();
  pedestalAssembly.name = "pedestal_assembly";
  pedestalAssembly.position.set(0, 0.55, 0);
  root.add(pedestalAssembly);

  const plinth = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.5, 1.1, 40));
  plinth.name = "plinth";
  plinth.position.set(0, 0.55, 0);
  pedestalAssembly.add(plinth);

  const riser = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.35, 2.4, 32));
  riser.name = "riser";
  riser.position.set(0, 2.0, 0);
  pedestalAssembly.add(riser);

  const plaqueAnchor = new THREE.Group();
  plaqueAnchor.name = "plaque_anchor";
  plaqueAnchor.position.set(1.45, 0.95, -1.2);
  plaqueAnchor.rotation.y = Math.PI / 7;
  plaqueAnchor.scale.set(1.15, 0.65, -0.85);
  pedestalAssembly.add(plaqueAnchor);

  const plaqueTilt = new THREE.Group();
  plaqueTilt.name = "plaque_tilt";
  plaqueTilt.rotation.x = -Math.PI / 10;
  plaqueTilt.rotation.z = Math.PI / 18;
  plaqueAnchor.add(plaqueTilt);

  const plaque = new THREE.Mesh(new THREE.BoxGeometry(1.25, 0.18, 0.52));
  plaque.name = "plaque";
  plaqueTilt.add(plaque);

  const sculptureMount = new THREE.Group();
  sculptureMount.name = "sculpture_mount";
  sculptureMount.position.set(0, 3.35, 0);
  sculptureMount.rotation.y = Math.PI / 6;
  sculptureMount.rotation.z = -Math.PI / 20;
  pedestalAssembly.add(sculptureMount);

  const orbitRing = new THREE.Mesh(new THREE.TorusGeometry(1.75, 0.13, 18, 72));
  orbitRing.name = "orbit_ring";
  orbitRing.rotation.x = Math.PI / 2.8;
  orbitRing.rotation.z = Math.PI / 9;
  sculptureMount.add(orbitRing);

  const core = new THREE.Mesh(new THREE.SphereGeometry(0.92, 32, 20));
  core.name = "core";
  core.position.set(0.18, 0.05, -0.08);
  sculptureMount.add(core);

  const fin = new THREE.Mesh(new THREE.BoxGeometry(0.28, 2.6, 0.7));
  fin.name = "fin";
  fin.position.set(-0.35, 0.1, 0.12);
  fin.rotation.z = Math.PI / 5;
  fin.rotation.x = Math.PI / 11;
  sculptureMount.add(fin);

  const accentPins = new THREE.Group();
  accentPins.name = "accent_pins";
  sculptureMount.add(accentPins);

  const pinGeometry = new THREE.CylinderGeometry(0.07, 0.07, 0.85, 18);
  const pinMaterial = new THREE.MeshBasicMaterial();
  const pins = new THREE.InstancedMesh(pinGeometry, pinMaterial, 4);
  pins.name = "pins";

  const helper = new THREE.Object3D();
  const pinRadius = 1.35;
  for (let index = 0; index < 4; index += 1) {
    const angle = index * (Math.PI / 2);
    helper.position.set(Math.cos(angle) * pinRadius, 0.0, Math.sin(angle) * pinRadius);
    helper.rotation.z = Math.PI / 2;
    helper.rotation.y = angle;
    helper.updateMatrix();
    pins.setMatrixAt(index, helper.matrix);
  }
  pins.instanceMatrix.needsUpdate = true;
  accentPins.add(pins);

  return root;
}
