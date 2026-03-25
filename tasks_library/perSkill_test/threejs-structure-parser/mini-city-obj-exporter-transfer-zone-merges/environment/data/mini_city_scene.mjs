import * as THREE from 'three';

function makeBox(name, size, color) {
  const geometry = new THREE.BoxGeometry(size[0], size[1], size[2]);
  const material = new THREE.MeshStandardMaterial({ color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  mesh.castShadow = false;
  mesh.receiveShadow = false;
  return mesh;
}

function makeCylinder(name, radiusTop, radiusBottom, height, radialSegments, color) {
  const geometry = new THREE.CylinderGeometry(radiusTop, radiusBottom, height, radialSegments);
  const material = new THREE.MeshStandardMaterial({ color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  return mesh;
}

function makeGroundStrip(name, width, depth, color) {
  const geometry = new THREE.BoxGeometry(width, 0.08, depth);
  const material = new THREE.MeshStandardMaterial({ color });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.name = name;
  return mesh;
}

export function createScene() {
  const root = new THREE.Group();
  root.name = 'mini_city_root';

  const northDistrict = new THREE.Group();
  northDistrict.name = 'north_district';
  northDistrict.position.set(-7.5, 0, -4.0);
  northDistrict.rotation.y = 0.18;
  root.add(northDistrict);

  const northGateway = new THREE.Group();
  northGateway.name = 'north_gateway';
  northGateway.position.set(-1.8, 0, 0.6);
  northDistrict.add(northGateway);

  const sidewalkNorth = makeGroundStrip('sidewalk_north_main', 6.5, 1.6, 0xc9c7c1);
  sidewalkNorth.position.set(0.4, 0.04, 0.0);
  sidewalkNorth.userData.zone = 'pedestrian_paths';
  sidewalkNorth.userData.block = 'north_gateway';
  northGateway.add(sidewalkNorth);

  const towerCluster = new THREE.Group();
  towerCluster.name = 'tower_cluster';
  towerCluster.position.set(1.2, 0, -1.1);
  towerCluster.rotation.y = -0.23;
  northGateway.add(towerCluster);

  const towerShellAlpha = makeBox('tower_shell_alpha', [2.2, 8.8, 2.4], 0x8da3b5);
  towerShellAlpha.position.set(0, 4.4, 0);
  towerShellAlpha.userData.semanticTag = 'residential_mass';
  towerShellAlpha.userData.block = 'north_gateway';
  towerCluster.add(towerShellAlpha);

  const towerBalconyAlpha = makeBox('tower_balcony_alpha', [2.8, 0.35, 0.9], 0xb0b7c0);
  towerBalconyAlpha.position.set(0.15, 3.2, 1.15);
  towerBalconyAlpha.rotation.y = 0.14;
  towerBalconyAlpha.userData.zone = 'building_shells';
  towerBalconyAlpha.userData.block = 'north_gateway';
  towerCluster.add(towerBalconyAlpha);

  const plazaArcade = new THREE.Group();
  plazaArcade.name = 'plaza_arcade';
  plazaArcade.position.set(3.8, 0, 2.0);
  plazaArcade.rotation.y = 0.33;
  northDistrict.add(plazaArcade);

  const plazaStrip = makeGroundStrip('plaza_strip_arc', 5.8, 1.4, 0xd6d0c2);
  plazaStrip.position.set(0.0, 0.04, 0.0);
  plazaStrip.userData.semanticTag = 'walkway_surface';
  plazaStrip.userData.block = 'plaza_arcade';
  plazaArcade.add(plazaStrip);

  const kioskGroup = new THREE.Group();
  kioskGroup.name = 'kiosk_group';
  kioskGroup.position.set(-0.7, 0, 1.7);
  kioskGroup.rotation.y = -0.42;
  plazaArcade.add(kioskGroup);

  const kioskRoof = makeBox('kiosk_roof_arc', [2.4, 0.4, 1.8], 0xe18b45);
  kioskRoof.position.set(0.0, 1.8, 0.0);
  kioskRoof.userData.semanticTag = 'shop_canopy';
  kioskRoof.userData.block = 'plaza_arcade';
  kioskGroup.add(kioskRoof);

  const southDistrict = new THREE.Group();
  southDistrict.name = 'south_district';
  southDistrict.position.set(8.8, 0, 6.2);
  southDistrict.rotation.y = -0.27;
  root.add(southDistrict);

  const marketCorner = new THREE.Group();
  marketCorner.name = 'market_corner';
  marketCorner.position.set(-1.2, 0, -1.4);
  southDistrict.add(marketCorner);

  const crosswalkMarket = makeGroundStrip('crosswalk_market', 3.2, 0.9, 0xf3f1eb);
  crosswalkMarket.position.set(0.0, 0.05, 0.0);
  crosswalkMarket.rotation.y = 0.09;
  crosswalkMarket.userData.semanticTag = 'crosswalk_marking';
  crosswalkMarket.userData.block = 'market_corner';
  marketCorner.add(crosswalkMarket);

  const marketStalls = new THREE.Group();
  marketStalls.name = 'market_stalls';
  marketStalls.position.set(1.9, 0, 1.1);
  marketStalls.rotation.y = 0.58;
  marketCorner.add(marketStalls);

  const awningEast = makeBox('awning_market_east', [2.3, 0.28, 1.2], 0xc95a49);
  awningEast.position.set(0.8, 2.5, 0.2);
  awningEast.userData.semanticTag = 'shop_canopy';
  awningEast.userData.block = 'market_corner';
  marketStalls.add(awningEast);

  const awningWest = makeBox('awning_market_west', [2.0, 0.28, 1.1], 0xc95a49);
  awningWest.position.set(-0.9, 2.35, -0.4);
  awningWest.rotation.z = 0.06;
  awningWest.userData.zone = 'retail_frontage';
  awningWest.userData.block = 'market_corner';
  marketStalls.add(awningWest);

  const southTransit = new THREE.Group();
  southTransit.name = 'south_transit';
  southTransit.position.set(3.4, 0, 2.8);
  southTransit.rotation.y = -0.31;
  southDistrict.add(southTransit);

  const platformPath = makeGroundStrip('tram_platform_path', 4.6, 1.2, 0xbab7af);
  platformPath.position.set(0.5, 0.04, -0.2);
  platformPath.userData.zone = 'pedestrian_paths';
  platformPath.userData.block = 'south_transit';
  southTransit.add(platformPath);

  const benchStopA = makeBox('bench_stop_a', [1.6, 0.45, 0.55], 0x6d4c41);
  benchStopA.position.set(-1.4, 0.55, 0.65);
  benchStopA.rotation.y = 0.48;
  benchStopA.userData.semanticTag = 'street_fixture';
  benchStopA.userData.block = 'south_transit';
  southTransit.add(benchStopA);

  const planterStopB = makeCylinder('planter_stop_b', 0.45, 0.55, 0.9, 18, 0x3f7d4a);
  planterStopB.position.set(1.6, 0.45, 0.95);
  planterStopB.userData.zone = 'street_furniture';
  planterStopB.userData.block = 'south_transit';
  southTransit.add(planterStopB);

  return root;
}
