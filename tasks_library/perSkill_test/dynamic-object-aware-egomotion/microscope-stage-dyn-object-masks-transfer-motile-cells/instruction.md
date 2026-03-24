Given the microscope video `/root/microscope_stage_drift.mp4`, sample it at `4 fps` and write a single output file to `/root/motile_cells_dyn_masks.npz`.

For each sampled frame, produce a binary mask that marks cells showing independent motion or clear shape change. Apparent motion caused only by slow microscope stage drift must not be marked, and static adhered cells or fixed debris should stay background.

Store the masks in CSR sparse format:
- Save the shared mask size under the key `shape` as `[H, W]`.
- For each sampled frame `i`, save the sparse mask with keys `f_{i}_data`, `f_{i}_indices`, and `f_{i}_indptr`.

The file should contain one sparse mask for every sampled frame in temporal order.
