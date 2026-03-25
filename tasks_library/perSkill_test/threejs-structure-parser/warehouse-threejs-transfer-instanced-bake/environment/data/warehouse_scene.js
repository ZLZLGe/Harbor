import * as THREE from 'three';

function composeMatrix(position, rotationEuler, scale) {
    const quaternion = new THREE.Quaternion().setFromEuler(rotationEuler);
    return new THREE.Matrix4().compose(position, quaternion, scale);
}

function addRackPost(group, x, y, z) {
    const post = new THREE.Mesh(new THREE.BoxGeometry(0.35, 7.2, 0.35));
    post.position.set(x, y, z);
    group.add(post);
}

function addShelfBeam(group, x, y, z, width) {
    const beam = new THREE.Mesh(new THREE.BoxGeometry(width, 0.24, 0.3));
    beam.position.set(x, y, z);
    group.add(beam);
}

export function createScene() {
    const root = new THREE.Group();

    const aisle = new THREE.Group();
    aisle.position.set(3.5, 0.4, -2.5);
    aisle.rotation.y = 0.22;
    root.add(aisle);

    const building = new THREE.Group();
    building.scale.set(1.0, 1.0, 1.08);
    aisle.add(building);

    const floor = new THREE.Mesh(new THREE.BoxGeometry(34, 0.4, 18));
    floor.name = 'floor_plate';
    floor.position.set(0, -0.2, 0);
    building.add(floor);

    const backWall = new THREE.Mesh(new THREE.BoxGeometry(34, 9, 0.45));
    backWall.name = 'rear_wall';
    backWall.position.set(0, 4.5, -8.7);
    building.add(backWall);

    const rackAssembly = new THREE.Group();
    rackAssembly.position.set(0, 0, 0.8);
    rackAssembly.rotation.z = -0.03;
    rackAssembly.scale.set(1.05, 1.0, 0.95);
    building.add(rackAssembly);

    const frame = new THREE.Group();
    frame.position.set(0, 0, 0);
    rackAssembly.add(frame);

    addRackPost(frame, -8.5, 3.6, -2.8);
    addRackPost(frame, -8.5, 3.6, 2.8);
    addRackPost(frame, 8.5, 3.6, -2.8);
    addRackPost(frame, 8.5, 3.6, 2.8);

    addShelfBeam(frame, 0, 1.8, -2.85, 17.4);
    addShelfBeam(frame, 0, 1.8, 2.85, 17.4);
    addShelfBeam(frame, 0, 4.2, -2.85, 17.4);
    addShelfBeam(frame, 0, 4.2, 2.85, 17.4);

    const shelfDeck = new THREE.Mesh(new THREE.BoxGeometry(17.2, 0.18, 5.3));
    shelfDeck.name = 'shelf_deck';
    shelfDeck.position.set(0, 4.2, 0);
    frame.add(shelfDeck);

    const cartonFront = new THREE.InstancedMesh(
        new THREE.BoxGeometry(1.4, 1.1, 1.0),
        new THREE.MeshStandardMaterial(),
        12,
    );
    cartonFront.name = 'carton_front_run';
    cartonFront.position.set(-5.8, 0, -1.15);
    cartonFront.rotation.y = 0.18;
    cartonFront.scale.set(1.0, 1.0, 0.96);
    frame.add(cartonFront);

    for (let i = 0; i < 12; i += 1) {
        const column = i % 4;
        const row = Math.floor(i / 4);
        const matrix = composeMatrix(
            new THREE.Vector3(column * 2.15, 4.95 + row * 1.25, 0),
            new THREE.Euler(0, row % 2 === 0 ? 0.06 : -0.04, 0),
            new THREE.Vector3(1.0, 1.0 + row * 0.02, 1.0),
        );
        cartonFront.setMatrixAt(i, matrix);
    }

    const cartonRear = new THREE.InstancedMesh(
        new THREE.BoxGeometry(1.25, 0.95, 1.05),
        new THREE.MeshStandardMaterial(),
        9,
    );
    cartonRear.name = 'carton_rear_stack';
    cartonRear.position.set(-4.7, 0, 1.35);
    cartonRear.rotation.y = -0.12;
    cartonRear.scale.set(0.98, 1.0, 1.02);
    frame.add(cartonRear);

    for (let i = 0; i < 9; i += 1) {
        const column = i % 3;
        const row = Math.floor(i / 3);
        const matrix = composeMatrix(
            new THREE.Vector3(column * 2.55, 4.86 + row * 1.12, 0),
            new THREE.Euler(0, 0.03 * column, 0),
            new THREE.Vector3(1.0, 1.0, 1.0 + row * 0.03),
        );
        cartonRear.setMatrixAt(i, matrix);
    }

    const fastenerCarrier = new THREE.Group();
    fastenerCarrier.position.set(0.1, 0.2, 0);
    fastenerCarrier.rotation.x = 0.08;
    rackAssembly.add(fastenerCarrier);

    const tieBolts = new THREE.InstancedMesh(
        new THREE.CylinderGeometry(0.1, 0.1, 0.5, 16),
        new THREE.MeshStandardMaterial(),
        16,
    );
    tieBolts.name = 'tie_bolts';
    tieBolts.position.set(0, 4.2, 0);
    tieBolts.rotation.z = Math.PI / 2;
    fastenerCarrier.add(tieBolts);

    const boltOffsets = [
        [-8.25, -2.7],
        [-8.25, 2.7],
        [-2.85, -2.7],
        [-2.85, 2.7],
        [2.85, -2.7],
        [2.85, 2.7],
        [8.25, -2.7],
        [8.25, 2.7],
    ];
    for (let i = 0; i < boltOffsets.length; i += 1) {
        const [x, z] = boltOffsets[i];
        const upper = composeMatrix(
            new THREE.Vector3(x, 0.18, z),
            new THREE.Euler(0, 0, 0),
            new THREE.Vector3(1, 1, 1),
        );
        const lower = composeMatrix(
            new THREE.Vector3(x, -2.16, z),
            new THREE.Euler(0, 0, 0),
            new THREE.Vector3(1, 1, 1),
        );
        tieBolts.setMatrixAt(i * 2, upper);
        tieBolts.setMatrixAt(i * 2 + 1, lower);
    }

    const palletCluster = new THREE.Group();
    palletCluster.position.set(6.4, 0.22, 5.3);
    palletCluster.rotation.y = -0.32;
    palletCluster.scale.set(1.0, 1.0, 1.1);
    aisle.add(palletCluster);

    const palletBase = new THREE.Mesh(new THREE.BoxGeometry(4.6, 0.32, 3.2));
    palletBase.name = 'pallet_base';
    palletBase.position.set(0, 0.16, 0);
    palletCluster.add(palletBase);

    const cornerBraces = new THREE.InstancedMesh(
        new THREE.BoxGeometry(0.3, 1.0, 0.3),
        new THREE.MeshStandardMaterial(),
        4,
    );
    cornerBraces.name = 'pallet_corner_braces';
    cornerBraces.position.set(0, 0.66, 0);
    palletCluster.add(cornerBraces);

    const bracePositions = [
        [-2.0, -1.35],
        [-2.0, 1.35],
        [2.0, -1.35],
        [2.0, 1.35],
    ];
    for (let i = 0; i < bracePositions.length; i += 1) {
        const [x, z] = bracePositions[i];
        cornerBraces.setMatrixAt(
            i,
            composeMatrix(
                new THREE.Vector3(x, 0, z),
                new THREE.Euler(0.05 * (i % 2 === 0 ? 1 : -1), 0, 0),
                new THREE.Vector3(1, 1, 1),
            ),
        );
    }

    return root;
}
