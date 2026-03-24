The file `/root/data/object.js` exports a small variant generator for rooftop solar layouts. It provides `VARIANT_NAMES` and `createVariantScene(variantName)`. Each generated scene contains rooftop context meshes that should be ignored, a `panel_field` group that contains every photovoltaic panel mesh, and a `rack_assembly` group that contains only the support structure for that variant.

Build every listed variant and export geometry to `/root/output` with this layout:

```text
/root/output/
└── variants/
    ├── west-roof/
    │   ├── panels/
    │   │   ├── panel_r1_c1.obj
    │   │   └── ...
    │   └── rack.obj
    ├── courtyard-canopy/
    └── service-shed/
```

Requirements:

1. Process exactly the variants from `VARIANT_NAMES`, creating one output folder per variant under `/root/output/variants/`.
2. For each variant, traverse `panel_field` and export every panel mesh in world coordinates to `/root/output/variants/<variant>/panels/<mesh_name>.obj`.
3. For each variant, traverse `rack_assembly`, merge all rack meshes for that variant, and export the combined result in world coordinates to `/root/output/variants/<variant>/rack.obj`.
4. Preserve the original panel mesh names in filenames. If a panel mesh is unnamed, fall back to `unnamed_panel_<n>`.
5. Ignore all non-panel rooftop context such as roofs, parapets, walkways, and inverter cabinets.
6. The final output must contain variant folders for `west-roof`, `courtyard-canopy`, and `service-shed`.
