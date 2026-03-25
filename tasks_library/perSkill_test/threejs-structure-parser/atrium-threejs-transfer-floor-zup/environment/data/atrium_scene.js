import * as THREE from 'three';

function makeMesh({
  geometry,
  name,
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  scale = [1, 1, 1],
}) {
  const mesh = new THREE.Mesh(
    geometry,
    new THREE.MeshStandardMaterial({ color: 0xb7c3d0 })
  );
  mesh.name = name;
  mesh.position.set(...position);
  mesh.rotation.set(...rotation);
  mesh.scale.set(...scale);
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();

  const building = new THREE.Group();
  building.position.set(6, 0, -4);
  building.rotation.set(0, 0.18, 0.05);
  root.add(building);

  const floorLobby = new THREE.Group();
  floorLobby.name = 'floor_lobby';
  floorLobby.rotation.set(0, 0, 0.04);
  building.add(floorLobby);

  const lobbyInterior = new THREE.Group();
  lobbyInterior.position.set(0.4, 0, 0.2);
  floorLobby.add(lobbyInterior);
  lobbyInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(14, 0.5, 10),
      name: 'lobby_slab',
      position: [0, -0.25, 0],
    })
  );
  lobbyInterior.add(
    makeMesh({
      geometry: new THREE.CylinderGeometry(0.7, 0.7, 3.5, 12),
      name: 'lobby_column',
      position: [-3, 1.75, 2],
      rotation: [0.1, 0, 0],
    })
  );

  const mezzanineWrapper = new THREE.Group();
  mezzanineWrapper.position.set(-1.5, 5.2, 1.4);
  mezzanineWrapper.rotation.set(0, -0.12, 0);
  building.add(mezzanineWrapper);

  const floorMezzanine = new THREE.Group();
  floorMezzanine.name = 'floor_mezzanine';
  mezzanineWrapper.add(floorMezzanine);

  const mezzanineInterior = new THREE.Group();
  mezzanineInterior.position.set(0.2, 0, 0);
  floorMezzanine.add(mezzanineInterior);
  mezzanineInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(10, 0.45, 6),
      name: 'mezz_platform',
      position: [0, -0.225, 0],
    })
  );
  mezzanineInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(2.2, 1.1, 0.4),
      name: 'mezz_bar',
      position: [2.5, 0.55, -2.2],
      rotation: [0, 0.2, 0],
    })
  );

  const floorUpper = new THREE.Group();
  floorUpper.name = 'floor_upper';
  floorUpper.position.set(1.2, 10.4, -0.8);
  floorUpper.rotation.set(0.03, 0, -0.06);
  building.add(floorUpper);

  const upperInterior = new THREE.Group();
  upperInterior.position.set(-0.3, 0, 0.5);
  floorUpper.add(upperInterior);
  upperInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(12, 0.45, 8),
      name: 'upper_slab',
      position: [0, -0.225, 0],
    })
  );
  upperInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(1.2, 2.6, 0.35),
      name: 'upper_screen',
      position: [3, 1.3, -3.4],
      rotation: [0, 0.35, 0],
    })
  );

  const floorSkyLounge = new THREE.Group();
  floorSkyLounge.name = 'floor_sky_lounge';
  floorSkyLounge.position.set(2.8, 4.6, 1.8);
  floorSkyLounge.rotation.set(0, 0.42, 0);
  floorUpper.add(floorSkyLounge);

  const skyInterior = new THREE.Group();
  skyInterior.position.set(0.2, 0, 0);
  floorSkyLounge.add(skyInterior);
  skyInterior.add(
    makeMesh({
      geometry: new THREE.BoxGeometry(6, 0.35, 4.5),
      name: 'sky_deck',
      position: [0, -0.175, 0],
    })
  );
  skyInterior.add(
    makeMesh({
      geometry: new THREE.SphereGeometry(0.7, 12, 8),
      name: 'sky_skylight',
      position: [-1.2, 1.1, 1.2],
      scale: [1.4, 0.7, 1.1],
    })
  );

  return root;
}
