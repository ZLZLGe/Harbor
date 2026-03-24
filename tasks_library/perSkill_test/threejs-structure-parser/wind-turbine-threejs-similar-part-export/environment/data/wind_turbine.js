import * as THREE from 'three';

function makeStrut(start, end, radius, name) {
    const direction = new THREE.Vector3().subVectors(end, start);
    const length = direction.length();
    const geometry = new THREE.CylinderGeometry(radius, radius, length, 18);
    const mesh = new THREE.Mesh(geometry);
    mesh.name = name;
    mesh.position.copy(start).addScaledVector(direction, 0.5);
    mesh.quaternion.setFromUnitVectors(
        new THREE.Vector3(0, 1, 0),
        direction.clone().normalize(),
    );
    return mesh;
}

function makeBlade(name, yawOffset, colorOffset) {
    const blade = new THREE.Group();
    blade.name = name;
    blade.rotation.z = yawOffset;

    const bladeRoot = new THREE.Mesh(
        new THREE.BoxGeometry(0.9, 7.5, 0.8),
    );
    bladeRoot.name = `${name}_root`;
    bladeRoot.position.y = 4.2;
    bladeRoot.rotation.z = 0.08 + colorOffset;
    blade.add(bladeRoot);

    const bladeTip = new THREE.Mesh(
        new THREE.BoxGeometry(0.45, 9.8, 0.35),
    );
    bladeTip.name = `${name}_tip`;
    bladeTip.position.set(0.2, 12.3, 0.05);
    bladeTip.rotation.z = -0.12 + colorOffset;
    blade.add(bladeTip);

    const winglet = new THREE.Mesh(
        new THREE.BoxGeometry(0.22, 1.8, 0.18),
    );
    winglet.name = `${name}_winglet`;
    winglet.position.set(0.38, 17.8, 0.1);
    winglet.rotation.set(0.12, 0.22, 0.3);
    blade.add(winglet);

    return blade;
}

export function createScene() {
    const root = new THREE.Group();

    const pedestal = new THREE.Group();
    pedestal.name = 'pedestal';
    root.add(pedestal);

    const plinth = new THREE.Mesh(new THREE.CylinderGeometry(5.8, 6.2, 1.8, 24));
    plinth.name = 'plinth';
    plinth.position.y = 0.9;
    pedestal.add(plinth);

    const anchorRing = new THREE.Mesh(new THREE.TorusGeometry(4.6, 0.35, 12, 32));
    anchorRing.name = 'anchor_ring';
    anchorRing.rotation.x = Math.PI / 2;
    anchorRing.position.y = 1.82;
    pedestal.add(anchorRing);

    const tower = new THREE.Group();
    tower.name = 'tower';
    root.add(tower);

    const towerShell = new THREE.Group();
    towerShell.position.y = 1.8;
    tower.add(towerShell);

    const lowerSection = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 3.6, 18, 28));
    lowerSection.name = 'lower_section';
    lowerSection.position.y = 9;
    towerShell.add(lowerSection);

    const upperSection = new THREE.Mesh(new THREE.CylinderGeometry(1.9, 2.8, 16, 28));
    upperSection.name = 'upper_section';
    upperSection.position.y = 26;
    towerShell.add(upperSection);

    const accessCollar = new THREE.Mesh(new THREE.TorusGeometry(2.25, 0.16, 8, 20));
    accessCollar.name = 'access_collar';
    accessCollar.rotation.x = Math.PI / 2;
    accessCollar.position.y = 17.5;
    towerShell.add(accessCollar);

    const nacelle = new THREE.Group();
    nacelle.name = 'nacelle';
    nacelle.position.set(0, 35.6, 0.4);
    nacelle.rotation.z = 0.04;
    root.add(nacelle);

    const nacelleBody = new THREE.Mesh(new THREE.BoxGeometry(8.8, 4.2, 4.4));
    nacelleBody.name = 'nacelle_body';
    nacelleBody.position.x = 1.4;
    nacelle.add(nacelleBody);

    const nacelleRoof = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.7, 8.5, 20, 1, false, 0, Math.PI));
    nacelleRoof.name = 'nacelle_roof';
    nacelleRoof.rotation.z = Math.PI / 2;
    nacelleRoof.position.set(1.4, 2.12, 0);
    nacelle.add(nacelleRoof);

    const intake = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.4, 1.4, 20));
    intake.name = 'cooling_intake';
    intake.rotation.z = Math.PI / 2;
    intake.position.set(-3.4, -0.4, 0);
    nacelle.add(intake);

    const servicePlatform = new THREE.Group();
    servicePlatform.name = 'service_platform';
    servicePlatform.position.set(2.1, -2.4, 0);
    nacelle.add(servicePlatform);

    const platformDeck = new THREE.Mesh(new THREE.BoxGeometry(3.8, 0.28, 2.6));
    platformDeck.name = 'platform_deck';
    servicePlatform.add(platformDeck);

    const railLeft = makeStrut(
        new THREE.Vector3(-1.7, 0.65, 1.12),
        new THREE.Vector3(1.7, 0.65, 1.12),
        0.08,
        'rail_left',
    );
    servicePlatform.add(railLeft);

    const railRight = makeStrut(
        new THREE.Vector3(-1.7, 0.65, -1.12),
        new THREE.Vector3(1.7, 0.65, -1.12),
        0.08,
        'rail_right',
    );
    servicePlatform.add(railRight);

    const hub = new THREE.Group();
    hub.name = 'hub';
    hub.position.set(6.15, 0.1, 0);
    hub.rotation.x = Math.PI / 2;
    nacelle.add(hub);

    const spinner = new THREE.Mesh(new THREE.ConeGeometry(1.7, 3.2, 24));
    spinner.name = 'spinner';
    spinner.rotation.z = -Math.PI / 2;
    spinner.position.x = 1.7;
    hub.add(spinner);

    const hubSleeve = new THREE.Mesh(new THREE.CylinderGeometry(1.45, 1.45, 2.8, 24));
    hubSleeve.name = 'hub_sleeve';
    hubSleeve.rotation.z = -Math.PI / 2;
    hub.add(hubSleeve);

    const bladeAlpha = makeBlade('blade_alpha', 0, 0);
    bladeAlpha.position.x = 0.3;
    hub.add(bladeAlpha);

    const bladeBeta = makeBlade('blade_beta', (Math.PI * 2) / 3, 0.02);
    bladeBeta.position.x = 0.3;
    hub.add(bladeBeta);

    const bladeGamma = makeBlade('blade_gamma', (Math.PI * 4) / 3, -0.015);
    bladeGamma.position.x = 0.3;
    hub.add(bladeGamma);

    return root;
}
