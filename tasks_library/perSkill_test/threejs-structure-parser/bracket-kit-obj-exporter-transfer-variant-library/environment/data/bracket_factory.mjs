import * as THREE from 'three';

function buildBoxComponent(component) {
  const geometry = new THREE.BoxGeometry(...component.size);
  const mesh = new THREE.Mesh(geometry);
  mesh.name = component.name;
  mesh.position.fromArray(component.center);
  return mesh;
}

function buildCylinderComponent(component) {
  const radialSegments = component.radial_segments || 24;
  const geometry = new THREE.CylinderGeometry(
    component.radius,
    component.radius,
    component.length,
    radialSegments
  );
  const mesh = new THREE.Mesh(geometry);
  mesh.name = component.name;

  if (component.axis === 'x') {
    mesh.rotation.z = Math.PI / 2;
  } else if (component.axis === 'z') {
    mesh.rotation.x = Math.PI / 2;
  }

  mesh.position.fromArray(component.center);
  return mesh;
}

export function buildComponent(component) {
  if (component.kind === 'box') {
    return buildBoxComponent(component);
  }
  if (component.kind === 'cylinder') {
    return buildCylinderComponent(component);
  }
  throw new Error(`Unsupported component kind: ${component.kind}`);
}

export function buildBracketVariant(variantSpec) {
  const group = new THREE.Group();
  group.name = variantSpec.name;

  for (const component of variantSpec.components) {
    group.add(buildComponent(component));
  }

  return group;
}

export function buildBracketKit(specDocument) {
  const group = new THREE.Group();
  group.name = specDocument.kit_name;

  for (const variantSpec of specDocument.variants) {
    const variantGroup = buildBracketVariant(variantSpec);
    variantGroup.position.fromArray(variantSpec.kit_offset);
    group.add(variantGroup);
  }

  return group;
}
