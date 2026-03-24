import * as THREE from 'three';

export const VARIANT_NAMES = ['west-roof', 'courtyard-canopy', 'service-shed'];

const PANEL_WIDTH = 2.2;
const PANEL_THICKNESS = 0.08;
const PANEL_HEIGHT = 1.15;

const VARIANT_SPECS = {
    'west-roof': {
        origin: [-12.0, 4.2, 6.0],
        yawDeg: -32,
        tiltDeg: 26,
        rows: 2,
        cols: 3,
        columnGap: 2.55,
        rowGap: 1.65,
        panelCentroidY: 1.9,
        postHeight: 1.55,
    },
    'courtyard-canopy': {
        origin: [7.5, 5.1, -9.0],
        yawDeg: 18,
        tiltDeg: 12,
        rows: 1,
        cols: 4,
        columnGap: 2.4,
        rowGap: 1.8,
        panelCentroidY: 2.45,
        postHeight: 2.1,
    },
    'service-shed': {
        origin: [13.0, 3.8, 11.5],
        yawDeg: 74,
        tiltDeg: 34,
        rows: 2,
        cols: 2,
        columnGap: 2.7,
        rowGap: 1.9,
        panelCentroidY: 1.75,
        postHeight: 1.4,
    },
};

function centeredOffset(index, count, spacing) {
    return (index - (count - 1) / 2) * spacing;
}

function arrayWidth(spec) {
    return (spec.cols - 1) * spec.columnGap + PANEL_WIDTH;
}

function arrayDepth(spec) {
    return (spec.rows - 1) * spec.rowGap + PANEL_HEIGHT;
}

function roofWidth(spec) {
    return arrayWidth(spec) + 4.2;
}

function roofDepth(spec) {
    return Math.max(arrayDepth(spec) + 3.5, 5.6);
}

function addRoofContext(root, spec) {
    const context = new THREE.Group();
    context.name = 'roof_context';
    root.add(context);

    const deck = new THREE.Mesh(
        new THREE.BoxGeometry(roofWidth(spec), 0.24, roofDepth(spec)),
    );
    deck.name = 'roof_deck';
    deck.position.set(0, 0.12, 0);
    context.add(deck);

    const parapetNorth = new THREE.Mesh(
        new THREE.BoxGeometry(roofWidth(spec), 0.65, 0.18),
    );
    parapetNorth.name = 'parapet_north';
    parapetNorth.position.set(0, 0.445, roofDepth(spec) / 2 - 0.09);
    context.add(parapetNorth);

    const parapetSouth = new THREE.Mesh(
        new THREE.BoxGeometry(roofWidth(spec), 0.65, 0.18),
    );
    parapetSouth.name = 'parapet_south';
    parapetSouth.position.set(0, 0.445, -roofDepth(spec) / 2 + 0.09);
    context.add(parapetSouth);

    const walkway = new THREE.Mesh(
        new THREE.BoxGeometry(arrayWidth(spec) - 0.6, 0.06, 0.9),
    );
    walkway.name = 'service_walkway';
    walkway.position.set(0, 0.27, -roofDepth(spec) / 2 + 1.15);
    context.add(walkway);

    const inverter = new THREE.Mesh(
        new THREE.BoxGeometry(0.8, 1.2, 0.45),
    );
    inverter.name = 'inverter_cabinet';
    inverter.position.set(roofWidth(spec) / 2 - 0.9, 0.72, -0.8);
    context.add(inverter);
}

function addRack(root, spec) {
    const rack = new THREE.Group();
    rack.name = 'rack_assembly';
    root.add(rack);

    const railLength = arrayWidth(spec) - 0.25;
    const tieLength = railLength - 0.4;
    const railGroupY = spec.panelCentroidY - 0.24;
    const railOffsetsZ = [-0.34, 0.34];

    for (let row = 0; row < spec.rows; row += 1) {
        const rowZ = centeredOffset(row, spec.rows, spec.rowGap);

        const railFrame = new THREE.Group();
        railFrame.name = `rail_frame_r${row + 1}`;
        railFrame.position.set(0, railGroupY, rowZ);
        railFrame.rotation.x = THREE.MathUtils.degToRad(-spec.tiltDeg);
        rack.add(railFrame);

        railOffsetsZ.forEach((offsetZ, railIndex) => {
            const rail = new THREE.Mesh(
                new THREE.BoxGeometry(railLength, 0.08, 0.12),
            );
            rail.name = `rail_r${row + 1}_${railIndex + 1}`;
            rail.position.set(0, 0, offsetZ);
            railFrame.add(rail);
        });

        const tie = new THREE.Mesh(
            new THREE.BoxGeometry(tieLength, 0.1, 0.1),
        );
        tie.name = `tie_r${row + 1}`;
        tie.position.set(0, 0.32, rowZ);
        rack.add(tie);

        for (let col = 0; col < spec.cols; col += 1) {
            const columnX = centeredOffset(col, spec.cols, spec.columnGap);

            const post = new THREE.Mesh(
                new THREE.BoxGeometry(0.12, spec.postHeight, 0.12),
            );
            post.name = `post_r${row + 1}_c${col + 1}`;
            post.position.set(columnX, spec.postHeight / 2, rowZ);
            rack.add(post);

            const foot = new THREE.Mesh(
                new THREE.BoxGeometry(0.35, 0.12, 0.35),
            );
            foot.name = `foot_r${row + 1}_c${col + 1}`;
            foot.position.set(columnX, 0.06, rowZ);
            rack.add(foot);
        }
    }

    const spine = new THREE.Mesh(
        new THREE.BoxGeometry(0.16, 0.16, arrayDepth(spec) + 0.9),
    );
    spine.name = 'center_spine';
    spine.position.set(0, 0.22, 0);
    rack.add(spine);
}

function addPanels(root, spec) {
    const panelField = new THREE.Group();
    panelField.name = 'panel_field';
    root.add(panelField);

    for (let row = 0; row < spec.rows; row += 1) {
        const rowGroup = new THREE.Group();
        rowGroup.name = `row_${row + 1}`;
        rowGroup.position.z = centeredOffset(row, spec.rows, spec.rowGap);
        panelField.add(rowGroup);

        for (let col = 0; col < spec.cols; col += 1) {
            const mount = new THREE.Group();
            mount.name = `mount_r${row + 1}_c${col + 1}`;
            mount.position.set(
                centeredOffset(col, spec.cols, spec.columnGap),
                spec.panelCentroidY,
                0,
            );
            mount.rotation.x = THREE.MathUtils.degToRad(-spec.tiltDeg);
            rowGroup.add(mount);

            const panelMesh = new THREE.Mesh(
                new THREE.BoxGeometry(PANEL_WIDTH, PANEL_THICKNESS, PANEL_HEIGHT),
            );
            panelMesh.name = `panel_r${row + 1}_c${col + 1}`;
            mount.add(panelMesh);
        }
    }
}

export function createVariantScene(variantName) {
    const spec = VARIANT_SPECS[variantName];
    if (!spec) {
        throw new Error(`Unknown variant: ${variantName}`);
    }

    const root = new THREE.Group();
    root.name = variantName;
    root.position.set(...spec.origin);
    root.rotation.y = THREE.MathUtils.degToRad(spec.yawDeg);

    addRoofContext(root, spec);
    addRack(root, spec);
    addPanels(root, spec);

    root.updateMatrixWorld(true);
    return root;
}
