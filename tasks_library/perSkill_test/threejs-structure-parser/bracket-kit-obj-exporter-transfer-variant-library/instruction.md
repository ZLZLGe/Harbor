The files `/root/data/bracket_specs.json` and `/root/data/bracket_factory.mjs` describe a small parameterized bracket kit.

Generate outputs under `/root/output/variants` with this contract:

1. Read `/root/data/bracket_specs.json`.
2. For each entry in `variants`, build a fresh bracket assembly from the provided component specification:
   - Use `/root/data/bracket_factory.mjs`.
   - Each variant export must reflect the variant's local component coordinates with all transforms applied.
3. Export one OBJ per variant to `/root/output/variants/<variant_name>.obj`.
4. Build one combined inspection kit that contains every variant positioned by its `kit_offset`, and export it to `/root/output/variants/brace_kit_overview.obj`.
5. Write `/root/output/variants/variant_manifest.json` as JSON with:
   - `kit_name`
   - `overview_file`
   - `variant_names`
   - `variants`, keyed by variant name, where each value contains:
     - `component_count`
     - `component_names`
     - `kit_offset`
6. The provided specification currently resolves to these variant files:
   - `brace_single_slot.obj`
   - `brace_double_slot.obj`
   - `brace_offset_bridge.obj`
   - `brace_service_riser.obj`
7. Your result must include `/root/output/variants/brace_double_slot.obj`.

Expected layout:

```text
/root/output/
└── variants/
    ├── brace_single_slot.obj
    ├── brace_double_slot.obj
    ├── brace_offset_bridge.obj
    ├── brace_service_riser.obj
    ├── brace_kit_overview.obj
    └── variant_manifest.json
```
