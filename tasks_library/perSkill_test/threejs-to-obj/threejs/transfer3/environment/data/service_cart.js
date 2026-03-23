import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();

  const cartBody = new THREE.Group();
  cartBody.name = 'cart_body';
  root.add(cartBody);

  const baseTub = new THREE.Mesh(
    new THREE.BoxGeometry(1.5, 0.18, 0.9),
    new THREE.MeshBasicMaterial()
  );
  baseTub.name = 'base_tub';
  baseTub.position.set(0.0, 0.32, 0.0);
  cartBody.add(baseTub);

  const topTray = new THREE.Group();
  topTray.name = 'top_tray';
  topTray.position.set(0.0, 1.12, 0.0);
  cartBody.add(topTray);

  const tray = new THREE.Mesh(
    new THREE.BoxGeometry(1.4, 0.1, 0.82),
    new THREE.MeshBasicMaterial()
  );
  tray.name = 'tray';
  topTray.add(tray);

  const handleSet = new THREE.Group();
  handleSet.name = 'handle_set';
  handleSet.position.set(-0.72, 0.95, 0.0);
  cartBody.add(handleSet);

  const handleBar = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04, 0.04, 1.05, 20),
    new THREE.MeshBasicMaterial()
  );
  handleBar.name = 'handle_bar';
  handleBar.rotation.z = Math.PI / 2;
  handleBar.position.set(0.0, 0.2, 0.0);
  handleSet.add(handleBar);

  const wheelPair = new THREE.Group();
  wheelPair.name = 'wheel_pair';
  wheelPair.position.set(0.0, 0.08, 0.0);
  cartBody.add(wheelPair);

  const leftWheel = new THREE.Group();
  leftWheel.name = 'left_wheel';
  leftWheel.position.set(-0.55, 0.0, 0.34);
  wheelPair.add(leftWheel);

  const leftTire = new THREE.Mesh(
    new THREE.TorusGeometry(0.17, 0.06, 12, 24),
    new THREE.MeshBasicMaterial()
  );
  leftTire.name = 'left_tire';
  leftTire.rotation.y = Math.PI / 2;
  leftWheel.add(leftTire);

  const rightWheel = new THREE.Group();
  rightWheel.name = 'right_wheel';
  rightWheel.position.set(0.55, 0.0, -0.34);
  wheelPair.add(rightWheel);

  const rightTire = new THREE.Mesh(
    new THREE.TorusGeometry(0.17, 0.06, 12, 24),
    new THREE.MeshBasicMaterial()
  );
  rightTire.name = 'right_tire';
  rightTire.rotation.y = Math.PI / 2;
  rightWheel.add(rightTire);

  return root;
}
