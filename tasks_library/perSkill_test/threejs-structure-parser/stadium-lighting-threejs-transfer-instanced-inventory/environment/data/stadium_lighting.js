import * as THREE from 'three';

function createInstancedBank(name, size, instances) {
    const geometry = new THREE.BoxGeometry(size[0], size[1], size[2]);
    const material = new THREE.MeshStandardMaterial();
    const bank = new THREE.InstancedMesh(geometry, material, instances.length);
    bank.name = name;

    const matrix = new THREE.Matrix4();
    const position = new THREE.Vector3();
    const rotation = new THREE.Euler();
    const quaternion = new THREE.Quaternion();
    const scale = new THREE.Vector3();

    instances.forEach((instance, index) => {
        position.set(...instance.position);
        rotation.set(...instance.rotation);
        quaternion.setFromEuler(rotation);
        scale.set(...(instance.scale || [1, 1, 1]));
        matrix.compose(position, quaternion, scale);
        bank.setMatrixAt(index, matrix);
    });

    bank.instanceMatrix.needsUpdate = true;
    return bank;
}

function createTruss(length) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(length, 0.25, 0.25));
    mesh.name = 'truss_frame';
    return mesh;
}

export function createScene() {
    const root = new THREE.Group();
    root.position.set(3.5, 1.2, -4.0);
    root.rotation.y = Math.PI / 15;

    const northTruss = new THREE.Group();
    northTruss.name = 'north_truss';
    northTruss.position.set(-10.0, 14.0, 7.0);
    northTruss.rotation.z = 0.05;
    root.add(northTruss);

    const northHelper = new THREE.Group();
    northHelper.position.set(0.0, 0.6, 0.0);
    northHelper.rotation.x = -0.14;
    northTruss.add(northHelper);
    northHelper.add(createTruss(12.0));
    northHelper.add(
        createInstancedBank('beam_spots', [0.85, 0.45, 1.15], [
            { position: [-4.6, -0.9, 0.0], rotation: [0.42, 0.0, 0.04] },
            { position: [-1.5, -0.8, 0.2], rotation: [0.38, 0.1, -0.03] },
            { position: [1.7, -0.85, -0.1], rotation: [0.36, -0.12, 0.02] },
            { position: [4.8, -0.95, 0.1], rotation: [0.4, 0.05, -0.05] },
        ]),
    );
    northHelper.add(
        createInstancedBank('wash_panels', [1.4, 0.25, 0.6], [
            { position: [-2.6, -1.35, 0.45], rotation: [0.62, 0.0, 0.0] },
            { position: [2.8, -1.35, -0.35], rotation: [0.62, 0.0, 0.0] },
        ]),
    );

    const centerRing = new THREE.Group();
    centerRing.name = 'center_ring';
    centerRing.position.set(0.0, 18.0, 0.0);
    centerRing.rotation.x = 0.08;
    centerRing.rotation.y = -0.35;
    root.add(centerRing);

    const centerHelper = new THREE.Group();
    centerHelper.position.set(0.0, -0.4, 0.0);
    centerHelper.rotation.x = 0.08;
    centerRing.add(centerHelper);
    centerHelper.add(new THREE.Mesh(new THREE.BoxGeometry(9.0, 0.25, 9.0)));
    centerHelper.add(
        createInstancedBank('ring_spot_bank', [0.7, 0.4, 1.0], [
            { position: [-3.2, 0.0, 2.8], rotation: [0.35, 0.1, 0.0] },
            { position: [3.0, 0.1, 2.6], rotation: [0.32, -0.12, 0.05] },
            { position: [-2.7, -0.1, -2.9], rotation: [0.3, 0.08, 0.02] },
            { position: [2.9, 0.0, -2.7], rotation: [0.34, -0.05, -0.04] },
        ]),
    );
    centerHelper.add(
        createInstancedBank('ring_wash_bank', [1.3, 0.28, 0.55], [
            { position: [0.0, -0.45, 3.7], rotation: [0.55, 0.0, 0.0] },
            { position: [0.0, -0.45, -3.7], rotation: [0.55, Math.PI, 0.0] },
        ]),
    );

    const sidelineCatwalk = new THREE.Group();
    sidelineCatwalk.name = 'sideline_catwalk';
    sidelineCatwalk.position.set(11.0, 11.0, -8.0);
    sidelineCatwalk.rotation.y = 0.48;
    root.add(sidelineCatwalk);

    const sidelineHelper = new THREE.Group();
    sidelineHelper.position.set(0.0, 0.3, 0.0);
    sidelineHelper.rotation.z = -0.09;
    sidelineCatwalk.add(sidelineHelper);
    sidelineHelper.add(createTruss(8.0));
    sidelineHelper.add(
        createInstancedBank('followspots', [1.0, 0.55, 1.6], [
            { position: [-2.5, -0.6, 0.0], rotation: [0.28, 0.15, 0.0] },
            { position: [0.0, -0.55, 0.1], rotation: [0.3, 0.0, 0.0] },
            { position: [2.6, -0.65, -0.1], rotation: [0.27, -0.18, 0.03] },
        ]),
    );
    sidelineHelper.add(
        createInstancedBank('laser_tiles', [0.9, 0.18, 0.9], [
            { position: [-1.2, -1.15, 0.65], rotation: [0.7, 0.0, 0.1] },
            { position: [1.3, -1.15, -0.7], rotation: [0.7, 0.0, -0.1] },
        ]),
    );

    return root;
}
