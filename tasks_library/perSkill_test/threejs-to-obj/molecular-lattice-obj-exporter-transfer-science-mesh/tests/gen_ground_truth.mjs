import * as THREE from 'three';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { createHash } from 'crypto';
import fs from 'fs';
import { pathToFileURL } from 'url';

function parseObjVerticesAndFaces(objText) {
  const vertices = [];
  let faceCount = 0;

  for (const line of objText.split('\n')) {
    if (line.startsWith('v ')) {
      const [, x, y, z] = line.trim().split(/\s+/);
      vertices.push([Number.parseFloat(x), Number.parseFloat(y), Number.parseFloat(z)]);
    } else if (line.startsWith('f ')) {
      faceCount += 1;
    }
  }

  return { vertices, faceCount };
}

function bbox(points) {
  const dims = [0, 1, 2];
  const minimum = dims.map((axis) => Math.min(...points.map((point) => point[axis])));
  const maximum = dims.map((axis) => Math.max(...points.map((point) => point[axis])));
  return {
    min: minimum,
    max: maximum,
    extents: maximum.map((value, axis) => value - minimum[axis]),
  };
}

function centroid(points) {
  const totals = [0, 0, 0];
  for (const point of points) {
    totals[0] += point[0];
    totals[1] += point[1];
    totals[2] += point[2];
  }
  return totals.map((value) => value / points.length);
}

function vertexDigest(points) {
  const ordered = points
    .map((point) => point.map((value) => value.toFixed(6)).join(','))
    .sort()
    .join('\n');
  return createHash('sha256').update(ordered).digest('hex');
}

async function main() {
  const sceneModule = await import(pathToFileURL('/root/data/lattice.js').href);
  const root = sceneModule.createMolecularLatticeScene();
  root.updateMatrixWorld(true);

  const axisMatrix = new THREE.Matrix4().makeRotationX(-Math.PI / 2);
  const worldMatrix = new THREE.Matrix4();
  const instanceMatrix = new THREE.Matrix4();
  const geometries = [];

  const addGeometry = (sourceGeometry, matrix) => {
    let geometry = sourceGeometry.clone();
    geometry.applyMatrix4(matrix);
    geometry.applyMatrix4(axisMatrix);
    if (geometry.index) {
      geometry = geometry.toNonIndexed();
    }
    if (!geometry.attributes.normal) {
      geometry.computeVertexNormals();
    }
    geometries.push(geometry);
  };

  root.traverse((object) => {
    if (object.isInstancedMesh) {
      const count = object.count ?? object.instanceCount ?? 0;
      for (let index = 0; index < count; index += 1) {
        object.getMatrixAt(index, instanceMatrix);
        worldMatrix.copy(object.matrixWorld).multiply(instanceMatrix);
        addGeometry(object.geometry, worldMatrix);
      }
      return;
    }

    if (object instanceof THREE.Mesh) {
      addGeometry(object.geometry, object.matrixWorld);
    }
  });

  const mergedGeometry = mergeGeometries(geometries, false);
  const mergedMesh = new THREE.Mesh(mergedGeometry);
  const exporter = new OBJExporter();
  const objText = exporter.parse(mergedMesh);
  const { vertices, faceCount } = parseObjVerticesAndFaces(objText);
  const bounds = bbox(vertices);

  fs.mkdirSync('/root/ground_truth', { recursive: true });
  fs.writeFileSync('/root/ground_truth/lattice.obj', objText);
  fs.writeFileSync(
    '/root/ground_truth/lattice_signature.json',
    JSON.stringify(
      {
        vertex_count: vertices.length,
        face_count: faceCount,
        bbox_min: bounds.min,
        bbox_max: bounds.max,
        bbox_extents: bounds.extents,
        centroid: centroid(vertices),
        vertex_digest: vertexDigest(vertices),
      },
      null,
      2,
    ),
  );
}

main().catch((error) => {
  console.error('Failed to generate lattice ground truth:', error);
  process.exit(1);
});
