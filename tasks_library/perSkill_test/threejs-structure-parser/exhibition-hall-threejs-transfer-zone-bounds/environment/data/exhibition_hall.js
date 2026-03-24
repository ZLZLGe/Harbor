import * as THREE from 'three';

function createPanel(width, height, depth, name) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth));
    mesh.name = name;
    return mesh;
}

function createColumn(radius, height, name) {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, 24));
    mesh.name = name;
    return mesh;
}

export function createScene() {
    const hall = new THREE.Group();
    hall.name = 'exhibition_hall';

    const atriumFloor = createPanel(34, 0.4, 24, 'atrium_floor');
    atriumFloor.position.set(0, -0.2, 0);
    hall.add(atriumFloor);

    const atriumSculptureRig = new THREE.Group();
    atriumSculptureRig.position.set(0, 1.8, 0);
    atriumSculptureRig.rotation.y = Math.PI / 5;
    hall.add(atriumSculptureRig);

    const atriumSculpture = createPanel(1.2, 3.2, 1.2, 'atrium_sculpture');
    atriumSculptureRig.add(atriumSculpture);

    const concourseZone = new THREE.Group();
    concourseZone.name = 'concourse_zone';
    concourseZone.position.set(-9, 0, -2);
    hall.add(concourseZone);

    const infoDesk = createPanel(3.2, 1.1, 1.8, 'info_desk');
    infoDesk.position.set(0, 0.55, 0.5);
    concourseZone.add(infoDesk);

    const signageRig = new THREE.Group();
    signageRig.position.set(2.4, 1.6, -1.5);
    signageRig.rotation.z = -0.25;
    concourseZone.add(signageRig);

    const wayfindingPanel = createPanel(2.4, 0.25, 1.1, 'wayfinding_panel');
    signageRig.add(wayfindingPanel);

    const ticketIsland = new THREE.Group();
    ticketIsland.name = 'ticket_island';
    ticketIsland.position.set(3.8, 0, 1.8);
    ticketIsland.rotation.y = Math.PI / 8;
    concourseZone.add(ticketIsland);

    const kioskCounter = createPanel(2.4, 1.0, 2.0, 'kiosk_counter');
    kioskCounter.position.set(0, 0.5, 0);
    ticketIsland.add(kioskCounter);

    const kioskCanopy = createPanel(3.2, 0.18, 2.8, 'kiosk_canopy');
    kioskCanopy.position.set(0, 2.2, 0);
    ticketIsland.add(kioskCanopy);

    const roboticsWing = new THREE.Group();
    roboticsWing.name = 'robotics_wing';
    roboticsWing.position.set(7.5, 0, -4.5);
    hall.add(roboticsWing);

    const robotRunway = createPanel(7.5, 0.3, 3.2, 'robot_runway');
    robotRunway.position.set(0, 0.15, 0);
    roboticsWing.add(robotRunway);

    const gantryRig = new THREE.Group();
    gantryRig.position.set(-2.5, 2.1, 1.6);
    gantryRig.rotation.y = -Math.PI / 6;
    gantryRig.scale.set(1.15, 1, 0.9);
    roboticsWing.add(gantryRig);

    const sensorGantry = createPanel(1.4, 2.6, 0.8, 'sensor_gantry');
    gantryRig.add(sensorGantry);

    const makerStage = new THREE.Group();
    makerStage.name = 'maker_stage';
    makerStage.position.set(2.8, 0.2, 2.4);
    makerStage.rotation.y = -Math.PI / 10;
    roboticsWing.add(makerStage);

    const demoPlatform = createPanel(3.8, 0.5, 3.0, 'demo_platform');
    demoPlatform.position.set(0, 0.25, 0);
    makerStage.add(demoPlatform);

    const prototypePedestal = createColumn(0.45, 1.6, 'prototype_pedestal');
    prototypePedestal.position.set(-0.9, 1.05, 0.7);
    makerStage.add(prototypePedestal);

    const immersiveDome = new THREE.Group();
    immersiveDome.name = 'immersive_dome';
    immersiveDome.position.set(6.5, 0, 6.8);
    immersiveDome.rotation.y = Math.PI / 7;
    hall.add(immersiveDome);

    const domeShell = new THREE.Mesh(new THREE.SphereGeometry(3.2, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2));
    domeShell.name = 'dome_shell';
    domeShell.scale.set(1, 0.7, 1);
    domeShell.position.set(0, 2.2, 0);
    immersiveDome.add(domeShell);

    const entryRampRig = new THREE.Group();
    entryRampRig.position.set(-2.4, 0.35, 0);
    entryRampRig.rotation.z = -0.2;
    immersiveDome.add(entryRampRig);

    const entryRamp = createPanel(3.6, 0.2, 1.4, 'entry_ramp');
    entryRampRig.add(entryRamp);

    const projectionRing = new THREE.Group();
    projectionRing.name = 'projection_ring';
    projectionRing.position.set(0.8, 3.3, -0.4);
    projectionRing.rotation.x = Math.PI / 2;
    immersiveDome.add(projectionRing);

    const lightTrack = new THREE.Mesh(new THREE.TorusGeometry(1.6, 0.12, 12, 48));
    lightTrack.name = 'light_track';
    projectionRing.add(lightTrack);

    const centerBeacon = createColumn(0.22, 1.4, 'center_beacon');
    centerBeacon.position.set(0, 0, 0.7);
    centerBeacon.rotation.z = Math.PI / 2;
    projectionRing.add(centerBeacon);

    const archiveGallery = new THREE.Group();
    archiveGallery.name = 'archive_gallery';
    archiveGallery.position.set(-5.5, 0, 6.2);
    archiveGallery.rotation.y = -Math.PI / 12;
    hall.add(archiveGallery);

    const shelfRig = new THREE.Group();
    shelfRig.position.set(0, 1.5, 0);
    shelfRig.scale.set(1.1, 1, 0.95);
    archiveGallery.add(shelfRig);

    const archiveShelf = createPanel(4.6, 3.0, 0.7, 'archive_shelf');
    shelfRig.add(archiveShelf);

    const timelineWall = createPanel(5.0, 2.4, 0.2, 'timeline_wall');
    timelineWall.position.set(0, 1.6, -2.1);
    archiveGallery.add(timelineWall);

    return hall;
}
