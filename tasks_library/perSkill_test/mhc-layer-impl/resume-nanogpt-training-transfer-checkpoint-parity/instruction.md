You are given a local GPT training scaffold in `/root/src` and a compact tokenized dataset in `/root/data`:

- `/root/data/resume_train.bin`
- `/root/data/resume_val.bin`
- `/root/data/resume_manifest.json`

Build one Python entrypoint that audits resumable training parity for a compact autoregressive GPT on this local corpus.

Requirements:

1. Run the same model architecture and optimizer configuration in two scenarios:
   - one uninterrupted reference run for the full training schedule,
   - one interrupted run that saves a checkpoint exactly at step `6`, restores from it, and finishes the remaining steps.
2. Read all fixed hyperparameters from `resume_manifest.json`, including the seed, total step count, checkpoint step, batch size, block size, and model size.
3. Use a real optimizer and record its state continuity. The resumed run must restore model weights, optimizer state, scaler state, and the randomness needed to continue the same stochastic training trajectory.
4. The training data stream must also resume from the exact point where the checkpoint was saved. Saving a replayable sampler or generator state is acceptable.
5. Keep the run compact enough to finish in the provided CPU-only container. You do not need a large model, but the run must perform real optimization and use the supplied token files.
6. Save the checkpoint to `/root/checkpoints/resume_step_6.pt`.
7. Write `/root/resume_consistency_report.json` with exactly these top-level fields:

```json
{
  "dataset": "resume_parity_tokens",
  "seed": 0,
  "total_steps": 0,
  "checkpoint_step": 0,
  "batch_size": 0,
  "block_size": 0,
  "continuous_loss_trace": [0.0],
  "resumed_loss_trace": [0.0],
  "continuous_final_val_loss": 0.0,
  "resumed_final_val_loss": 0.0,
  "max_train_loss_delta": 0.0,
  "final_val_loss_delta": 0.0,
  "max_parameter_delta": 0.0,
  "max_exp_avg_delta": 0.0,
  "max_exp_avg_sq_delta": 0.0,
  "continuous_final_lr": 0.0,
  "resumed_final_lr": 0.0,
  "continuous_tokens_seen": 0,
  "resumed_tokens_seen": 0,
  "scaler_enabled": true,
  "scaler_scale_delta": 0.0,
  "checkpoint_path": "/root/checkpoints/resume_step_6.pt"
}
```

Additional expectations:

- `continuous_loss_trace` and `resumed_loss_trace` must each contain exactly `12` loss values, one per optimization step.
- `max_train_loss_delta` must be computed from the elementwise absolute difference between the two training-loss traces.
- `final_val_loss_delta` must be the absolute difference between the two reported final validation losses.
- The checkpoint must be loadable with `torch.load(...)` and include at least the completed step index, model state, optimizer state, scaler state, RNG state, and training-data replay state.
- All reported metrics must come from the actual uninterrupted and resumed runs, not from hard-coded constants.
