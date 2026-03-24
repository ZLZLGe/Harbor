You are preparing an assay-screening analysis bundle in `/app`.

Use JAX to read the provided inputs from `/app/data/` and write these five output files into `/app`:

1. Read `plate_readings.npy` and compute the mean of each measurement channel across all wells. Save the length-6 vector as `assay_channel_summary.npy`.
2. Read `residual_bundle.npz`, subtract `expected` from `observed`, square the residuals elementwise, and save the full tensor as `residual_energy_map.npy`.
3. Read `binary_panel.npz` and compute the gradient of the mean logistic loss `mean(log(1 + exp(-y * (x @ w))))` with respect to `w`. The labels are already encoded as `-1` or `1`. Save the gradient as `binder_loss_grad.npy`.
4. Read `assay_rollout.npz` and run a recurrent state rollout over `seq` with zero initial hidden state. For each step, compute `h_new = tanh(Wx @ x_t + Wh @ h + b)` and collect every hidden state in order. Save the stacked states as `assay_state_rollout.npy`.
5. Read `network_stack.npz` and run a two-layer network on `X`: first `relu(X @ W1 + b1)`, then a linear layer with `W2` and `b2`. JIT-compile this network before executing it. Save the batch logits as `screening_head_logits.npy`.

All outputs must be stored as `.npy` files with exactly the names above. The primary output file is `assay_state_rollout.npy`.
