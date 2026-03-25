The files `/root/data/mini_city_scene.mjs` and `/root/data/zone_rules.json` describe a nested procedural city block scene plus fallback semantic grouping rules.

Generate exports under `/root/output/zones` with this contract:

1. Load the scene from `createScene()` in `/root/data/mini_city_scene.mjs`.
2. Traverse every `THREE.Mesh` in the scene and assign it to exactly one zone:
   - If `mesh.userData.zone` is a non-empty string, use that zone.
   - Otherwise, read `mesh.userData.semanticTag` and resolve it through `fallback_zone_by_semantic_tag` in `/root/data/zone_rules.json`.
   - Ignore meshes that match neither rule.
3. Apply world transforms before exporting. Every exported OBJ must reflect the placed scene geometry, not local coordinates.
4. Merge all meshes that resolve to the same zone and export them to `/root/output/zones/<zone>.obj`.
5. Write `/root/output/zones/zone_manifest.json` as a JSON object keyed by zone name. Each zone entry must contain:
   - `mesh_names`: array of contributing mesh names
   - `source_blocks`: array of distinct `mesh.userData.block` values for that zone
   - `mesh_count`: number of contributing meshes
6. The provided data resolves to these zone files:
   - `pedestrian_paths.obj`
   - `building_shells.obj`
   - `retail_frontage.obj`
   - `street_furniture.obj`
7. Your result must include `/root/output/zones/pedestrian_paths.obj`.

Expected layout:

```text
/root/output/
└── zones/
    ├── building_shells.obj
    ├── pedestrian_paths.obj
    ├── retail_frontage.obj
    ├── street_furniture.obj
    └── zone_manifest.json
```
