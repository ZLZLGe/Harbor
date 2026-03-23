import * as THREE from 'three';

export function createScene() {
  const root = new THREE.Group();

  const baseFrame = new THREE.Group();
  baseFrame.name = 'base_frame';
  baseFrame.position.set(0.2, 0.0, -0.1);
  root.add(baseFrame);

  const leftPost = new THREE.Mesh(
    new THREE.BoxGeometry(0.16, 1.8, 0.16),
    new THREE.MeshBasicMaterial()
  );
  leftPost.name = 'left_post';
  leftPost.position.set(-0.7, 0.9, 0.0);
  baseFrame.add(leftPost);

  const rightPost = leftPost.clone();
  rightPost.name = 'right_post';
  rightPost.position.x = 0.7;
  baseFrame.add(rightPost);

  const deck = new THREE.Mesh(
    new THREE.BoxGeometry(1.65, 0.12, 0.65),
    new THREE.MeshBasicMaterial()
  );
  deck.name = 'deck';
  deck.position.set(0.0, 0.45, 0.0);
  baseFrame.add(deck);

  const doorPanel = new THREE.Group();
  doorPanel.name = 'door_panel';
  doorPanel.position.set(0.72, 0.92, 0.31);
  doorPanel.rotation.y = -Math.PI / 8;
  baseFrame.add(doorPanel);

  const doorLeaf = new THREE.Mesh(
    new THREE.BoxGeometry(0.04, 1.1, 0.58),
    new THREE.MeshBasicMaterial()
  );
  doorLeaf.name = 'door_leaf';
  doorPanel.add(doorLeaf);

  const handle = new THREE.Mesh(
    new THREE.CylinderGeometry(0.03, 0.03, 0.42, 20),
    new THREE.MeshBasicMaterial()
  );
  handle.name = 'pull_handle';
  handle.position.set(0.0, 0.02, 0.17);
  handle.rotation.x = Math.PI / 2;
  doorPanel.add(handle);

  const topLight = new THREE.Group();
  topLight.name = 'top_light';
  topLight.position.set(-0.1, 1.95, -0.12);
  topLight.rotation.z = Math.PI / 20;
  root.add(topLight);

  const housing = new THREE.Mesh(
    new THREE.BoxGeometry(1.2, 0.16, 0.28),
    new THREE.MeshBasicMaterial()
  );
  housing.name = 'housing';
  topLight.add(housing);

  const diffuser = new THREE.Mesh(
    new THREE.BoxGeometry(1.05, 0.05, 0.18),
    new THREE.MeshBasicMaterial()
  );
  diffuser.name = 'diffuser';
  diffuser.position.set(0.0, -0.08, 0.02);
  topLight.add(diffuser);

  return root;
}
