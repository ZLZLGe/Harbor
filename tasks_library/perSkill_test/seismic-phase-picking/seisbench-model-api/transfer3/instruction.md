You have mission types at `/root/data/mission_types.csv`.

Create `/root/transfer3_capability_matrix.csv`.

Requirements:
1. Preserve input row order.
2. Write exactly these columns: `mission_id`, `target_task`, `recommended_model_family`, `api_mode`, `output_shape`.
3. Use this mapping:
   - `phase_picking` -> `phasenet`, `classify`, `discrete-picks`
   - `detection` -> `cred`, `classify`, `discrete-detections`
   - `denoising` -> `deepdenoiser`, `annotate`, `annotation-stream`
   - `depth_estimation` -> `depthphasenet`, `classify`, `discrete-estimates`
4. Do not read anything from `/tests`.
