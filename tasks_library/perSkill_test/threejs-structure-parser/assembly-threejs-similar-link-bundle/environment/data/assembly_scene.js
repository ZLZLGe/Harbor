import * as THREE from 'three';

function createBeam(start, end, radius, name) {
    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();
    const geometry = new THREE.CylinderGeometry(radius, radius, length, 20);
    const mesh = new THREE.Mesh(geometry);
    mesh.name = name;
    mesh.position.copy(start).addScaledVector(direction, 0.5);
    mesh.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        direction.clone().normalize(),
    );
    return mesh;
}

export function createScene() {
    const root = new THREE.Group();

    const baseFrame = new THREE.Group();
    baseFrame.name = 'base_frame';
    root.add(baseFrame);

    const basePlate = new THREE.Mesh(new THREE.BoxGeometry(32, 2, 18));
    basePlate.name = 'base_plate';
    basePlate.position.set(0, 1, 0);
    baseFrame.add(basePlate);

    const baseBraceContainer = new THREE.Group();
    baseBraceContainer.position.set(0, 0, 0);
    baseFrame.add(baseBraceContainer);

    baseBraceContainer.add(
        createBeam(
            new THREE.Vector3(-12, 2, -6),
            new THREE.Vector3(-4, 15, -6),
            0.7,
            'brace_left',
        ),
    );
    baseBraceContainer.add(
        createBeam(
            new THREE.Vector3(12, 2, 6),
            new THREE.Vector3(4, 15, 6),
            0.7,
            'brace_right',
        ),
    );

    const driveModuleWrapper = new THREE.Group();
    driveModuleWrapper.position.set(0, 7, 0);
    baseFrame.add(driveModuleWrapper);

    const driveModule = new THREE.Group();
    driveModule.name = 'drive_module';
    driveModule.rotation.y = Math.PI / 6;
    driveModuleWrapper.add(driveModule);

    const driveInner = new THREE.Group();
    driveInner.position.set(0, 3.5, 0);
    driveModule.add(driveInner);

    const motorBody = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 2.8, 8, 24));
    motorBody.name = 'motor_body';
    motorBody.rotation.z = Math.PI / 2;
    driveInner.add(motorBody);

    const couplingRing = new THREE.Mesh(new THREE.TorusGeometry(2.1, 0.45, 16, 32));
    couplingRing.name = 'coupling_ring';
    couplingRing.position.set(4.6, 0, 0);
    couplingRing.rotation.y = Math.PI / 2;
    driveInner.add(couplingRing);

    const gantry = new THREE.Group();
    gantry.name = 'gantry';
    gantry.position.set(0, 16, 0);
    gantry.rotation.z = -Math.PI / 18;
    root.add(gantry);

    const gantryContainer = new THREE.Group();
    gantryContainer.position.set(0, 0, 0);
    gantry.add(gantryContainer);

    const mast = new THREE.Mesh(new THREE.BoxGeometry(4, 16, 4));
    mast.name = 'mast';
    mast.position.set(-2, 8, 0);
    gantryContainer.add(mast);

    const hood = new THREE.Mesh(new THREE.BoxGeometry(10, 3, 6));
    hood.name = 'hood';
    hood.position.set(4, 13, 0);
    hood.rotation.y = Math.PI / 10;
    gantryContainer.add(hood);

    const sensorWrapper = new THREE.Group();
    sensorWrapper.position.set(8, 11, 0);
    gantryContainer.add(sensorWrapper);

    const sensorPod = new THREE.Group();
    sensorPod.name = 'sensor_pod';
    sensorPod.rotation.x = Math.PI / 10;
    sensorWrapper.add(sensorPod);

    const sensorBody = new THREE.Mesh(new THREE.BoxGeometry(5, 3, 4));
    sensorBody.name = 'sensor_body';
    sensorPod.add(sensorBody);

    const lensBarrel = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.2, 4, 20));
    lensBarrel.name = 'lens_barrel';
    lensBarrel.rotation.z = Math.PI / 2;
    lensBarrel.position.set(4, 0, 0);
    sensorPod.add(lensBarrel);

    const capContainer = new THREE.Group();
    capContainer.position.set(6.2, 0, 0);
    sensorPod.add(capContainer);

    const lensCap = new THREE.Mesh(new THREE.ConeGeometry(1.3, 2.5, 20));
    lensCap.name = 'lens_cap';
    lensCap.rotation.z = -Math.PI / 2;
    capContainer.add(lensCap);

    const cableBridge = new THREE.Group();
    cableBridge.name = 'cable_bridge';
    cableBridge.position.set(0, 24, 0);
    root.add(cableBridge);

    const arch = new THREE.Mesh(new THREE.TorusGeometry(8, 0.5, 12, 40, Math.PI));
    arch.name = 'arch_tube';
    arch.rotation.z = Math.PI;
    cableBridge.add(arch);

    const bridgeInner = new THREE.Group();
    bridgeInner.position.set(0, -4.5, 0);
    cableBridge.add(bridgeInner);

    const clamp = new THREE.Mesh(new THREE.BoxGeometry(3, 2, 2.5));
    clamp.name = 'bridge_clamp';
    bridgeInner.add(clamp);

    return root;
}
