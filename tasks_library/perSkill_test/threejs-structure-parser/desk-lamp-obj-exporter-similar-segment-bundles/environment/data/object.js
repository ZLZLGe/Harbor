import * as THREE from 'three';

function createCylinderBeam(start, end, radius, name) {
    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();
    const geometry = new THREE.CylinderGeometry(radius, radius, length, 18);
    const mesh = new THREE.Mesh(geometry);
    mesh.name = name;
    mesh.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        direction.clone().normalize(),
    );
    mesh.position.copy(start).add(direction.multiplyScalar(0.5));
    return mesh;
}

export function createScene() {
    const root = new THREE.Group();
    root.name = 'desk_lamp';

    const lamp_base = new THREE.Group();
    lamp_base.name = 'lamp_base';
    root.add(lamp_base);

    const weightedBase = new THREE.Mesh(
        new THREE.CylinderGeometry(4.8, 5.6, 1.2, 40),
    );
    weightedBase.name = 'weighted_base';
    weightedBase.position.y = 0.6;
    lamp_base.add(weightedBase);

    const stemColumn = new THREE.Mesh(
        new THREE.CylinderGeometry(0.42, 0.5, 2.6, 20),
    );
    stemColumn.name = 'stem_column';
    stemColumn.position.set(-0.8, 2.1, 0);
    lamp_base.add(stemColumn);

    const baseKnob = new THREE.Mesh(
        new THREE.SphereGeometry(0.45, 18, 14),
    );
    baseKnob.name = 'base_knob';
    baseKnob.position.set(2.9, 1.0, 1.5);
    lamp_base.add(baseKnob);

    const lower_arm = new THREE.Group();
    lower_arm.name = 'lower_arm';
    lower_arm.position.set(-0.8, 3.3, 0);
    lower_arm.rotation.z = -0.95;
    root.add(lower_arm);

    const lowerArmRig = new THREE.Group();
    lowerArmRig.position.set(0, 0.2, 0);
    lower_arm.add(lowerArmRig);

    lowerArmRig.add(
        createCylinderBeam(
            new THREE.Vector3(-0.35, 0, 0),
            new THREE.Vector3(-0.35, 6.2, 0),
            0.14,
            'lower_bar_left',
        ),
    );
    lowerArmRig.add(
        createCylinderBeam(
            new THREE.Vector3(0.35, 0, 0),
            new THREE.Vector3(0.35, 6.2, 0),
            0.14,
            'lower_bar_right',
        ),
    );

    const lowerCrossPin = new THREE.Mesh(
        new THREE.CylinderGeometry(0.18, 0.18, 1.1, 16),
    );
    lowerCrossPin.name = 'lower_cross_pin';
    lowerCrossPin.rotation.z = Math.PI / 2;
    lowerCrossPin.position.set(0, 5.9, 0);
    lowerArmRig.add(lowerCrossPin);

    const upper_arm = new THREE.Group();
    upper_arm.name = 'upper_arm';
    upper_arm.position.set(4.95, 6.95, 0);
    upper_arm.rotation.z = 1.05;
    root.add(upper_arm);

    const upperArmRig = new THREE.Group();
    upperArmRig.position.set(0.15, 0.1, 0);
    upper_arm.add(upperArmRig);

    upperArmRig.add(
        createCylinderBeam(
            new THREE.Vector3(-0.24, 0, 0),
            new THREE.Vector3(-0.24, 5.2, 0),
            0.12,
            'upper_bar_left',
        ),
    );
    upperArmRig.add(
        createCylinderBeam(
            new THREE.Vector3(0.24, 0, 0),
            new THREE.Vector3(0.24, 5.2, 0),
            0.12,
            'upper_bar_right',
        ),
    );

    const upperMountBlock = new THREE.Mesh(
        new THREE.BoxGeometry(1.0, 0.42, 0.95),
    );
    upperMountBlock.name = 'upper_mount_block';
    upperMountBlock.position.set(0, 5.0, 0);
    upperArmRig.add(upperMountBlock);

    const lamp_head = new THREE.Group();
    lamp_head.name = 'lamp_head';
    lamp_head.position.set(4.6, 11.6, 0);
    lamp_head.rotation.z = -0.38;
    lamp_head.rotation.x = 0.16;
    root.add(lamp_head);

    const headRig = new THREE.Group();
    headRig.position.set(0.15, 0.1, 0);
    lamp_head.add(headRig);

    const headShell = new THREE.Mesh(
        new THREE.CylinderGeometry(1.2, 2.4, 3.1, 32, 1, true),
    );
    headShell.name = 'head_shell';
    headShell.rotation.z = Math.PI / 2;
    headRig.add(headShell);

    const headRim = new THREE.Mesh(
        new THREE.TorusGeometry(2.35, 0.12, 12, 36),
    );
    headRim.name = 'head_rim';
    headRim.rotation.y = Math.PI / 2;
    headRim.position.x = 1.52;
    headRig.add(headRim);

    const headBulb = new THREE.Mesh(
        new THREE.SphereGeometry(0.72, 24, 18),
    );
    headBulb.name = 'head_bulb';
    headBulb.position.x = 0.95;
    headRig.add(headBulb);

    const headSocket = new THREE.Mesh(
        new THREE.CylinderGeometry(0.38, 0.38, 0.9, 18),
    );
    headSocket.name = 'head_socket';
    headSocket.rotation.z = Math.PI / 2;
    headSocket.position.x = -0.8;
    headRig.add(headSocket);

    return root;
}
