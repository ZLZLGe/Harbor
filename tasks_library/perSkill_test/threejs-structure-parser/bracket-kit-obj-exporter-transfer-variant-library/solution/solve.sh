#!/bin/bash
set -euo pipefail

mkdir -p /root/output/variants

cat > /root/export_brackets.mjs <<'EOF'
import fs from 'fs';
import { OBJExporter } from 'three/examples/jsm/exporters/OBJExporter.js';
import { buildBracketKit, buildBracketVariant } from '/root/data/bracket_factory.mjs';

const specDocument = JSON.parse(fs.readFileSync('/root/data/bracket_specs.json', 'utf8'));
const outputDir = '/root/output/variants';
const exporter = new OBJExporter();

function exportObject3D(object3D, outputPath) {
  object3D.updateMatrixWorld(true);
  const objText = exporter.parse(object3D);
  fs.writeFileSync(outputPath, objText);
}

const manifest = {
  kit_name: specDocument.kit_name,
  overview_file: specDocument.overview_file,
  variant_names: specDocument.variants.map((variant) => variant.name),
  variants: {},
};

for (const variant of specDocument.variants) {
  const variantGroup = buildBracketVariant(variant);
  exportObject3D(variantGroup, `${outputDir}/${variant.name}.obj`);

  manifest.variants[variant.name] = {
    component_count: variant.components.length,
    component_names: variant.components.map((component) => component.name),
    kit_offset: variant.kit_offset,
  };
}

const kitGroup = buildBracketKit(specDocument);
exportObject3D(kitGroup, `${outputDir}/${specDocument.overview_file}`);

fs.writeFileSync(
  `${outputDir}/variant_manifest.json`,
  `${JSON.stringify(manifest, null, 2)}\n`
);
EOF

node /root/export_brackets.mjs
