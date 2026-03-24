#!/bin/bash
set -euo pipefail

TASK_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export HARBOR_TASK_DIR="$TASK_DIR"

python3 - <<'PY'
import json
import math
import os
import random
import sys
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import torch


def resolve_root():
    if Path("/root/data/resume_manifest.json").exists():
        return Path("/root")
    fallback = os.environ.get("HARBOR_TASK_DIR")
    if fallback:
        return Path(fallback) / "environment"
    return Path.cwd()


ROOT = resolve_root()
DATA_DIR = ROOT / "data"
SRC_DIR = ROOT / "src"
OUTPUT_PATH = ROOT / "resume_consistency_report.json"
CHECKPOINT_PATH = ROOT / "checkpoints" / "resume_step_6.pt"
CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SRC_DIR))
from model import GPT, GPTConfig  # noqa: E402


with (DATA_DIR / "resume_manifest.json").open() as f:
    manifest = json.load(f)


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class DummyScaler:
    def __init__(self):
        self._scale = 1.0

    def scale(self, loss):
        return loss

    def unscale_(self, optimizer):
        return None

    def step(self, optimizer):
        optimizer.step()

    def update(self):
        return None

    def state_dict(self):
        return {"enabled": False, "scale": self._scale}

    def load_state_dict(self, state):
        self._scale = float(state.get("scale", 1.0))

    def get_scale(self):
        return self._scale

    def is_enabled(self):
        return False


def make_scaler():
    try:
        scaler = torch.amp.GradScaler("cpu")
        return scaler
    except Exception:
        return DummyScaler()


class TokenWindowDataset:
    def __init__(self, path, block_size, batch_size, seed):
        self.tokens = np.memmap(path, dtype=np.uint16, mode="r")
        self.block_size = block_size
        self.batch_size = batch_size
        self.generator = torch.Generator(device="cpu")
        self.generator.manual_seed(seed)
        self.batches_emitted = 0

    def get_batch(self, device):
        max_start = len(self.tokens) - self.block_size - 1
        starts = torch.randint(
            0,
            max_start,
            (self.batch_size,),
            generator=self.generator,
        )

        x = torch.empty(self.batch_size, self.block_size, dtype=torch.long)
        y = torch.empty(self.batch_size, self.block_size, dtype=torch.long)
        for row, start in enumerate(starts.tolist()):
            window = np.asarray(self.tokens[start : start + self.block_size + 1], dtype=np.int64)
            window = torch.from_numpy(window)
            x[row] = window[:-1]
            y[row] = window[1:]

        self.batches_emitted += 1
        return x.to(device), y.to(device)

    def state_dict(self):
        return {
            "generator_state": self.generator.get_state(),
            "batches_emitted": self.batches_emitted,
        }

    def load_state_dict(self, state):
        self.generator.set_state(state["generator_state"])
        self.batches_emitted = int(state["batches_emitted"])


def make_amp_state():
    scaler = make_scaler()
    enabled = bool(getattr(scaler, "is_enabled", lambda: False)())
    return scaler, enabled


def build_components():
    config = GPTConfig(
        vocab_size=manifest["vocab_size"],
        block_size=manifest["block_size"],
        n_layer=manifest["model"]["n_layer"],
        n_head=manifest["model"]["n_head"],
        n_embd=manifest["model"]["n_embd"],
        dropout=manifest["dropout"],
        bias=False,
    )
    model = GPT(config, use_rope=True).to("cpu")
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=manifest["learning_rate"],
        betas=(0.9, 0.95),
        weight_decay=manifest["weight_decay"],
    )
    scaler, amp_enabled = make_amp_state()
    dataset = TokenWindowDataset(
        DATA_DIR / "resume_train.bin",
        block_size=manifest["block_size"],
        batch_size=manifest["batch_size"],
        seed=manifest["seed"] + 17,
    )
    return config, model, optimizer, scaler, amp_enabled, dataset


def get_lr(step):
    max_lr = manifest["learning_rate"]
    min_lr = max_lr * 0.2
    warmup_steps = 2
    total_steps = manifest["train_steps"]
    if step < warmup_steps:
        return max_lr * float(step + 1) / float(warmup_steps)
    decay_ratio = (step - warmup_steps) / max(1, total_steps - warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * min(1.0, decay_ratio)))
    return min_lr + coeff * (max_lr - min_lr)


def evaluate(model):
    model.eval()
    eval_dataset = TokenWindowDataset(
        DATA_DIR / "resume_val.bin",
        block_size=manifest["block_size"],
        batch_size=manifest["batch_size"],
        seed=manifest["seed"] + 29,
    )
    losses = []
    with torch.no_grad():
        for _ in range(manifest["eval_batches"]):
            x, y = eval_dataset.get_batch("cpu")
            _, loss = model(x, y)
            losses.append(float(loss.item()))
    model.train()
    return float(sum(losses) / len(losses))


def save_checkpoint(model, optimizer, scaler, dataset, completed_steps):
    checkpoint = {
        "step": completed_steps,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "torch_rng_state": torch.get_rng_state(),
        "numpy_rng_state": np.random.get_state(),
        "python_rng_state": random.getstate(),
        "train_data_state": dataset.state_dict(),
    }
    torch.save(checkpoint, CHECKPOINT_PATH)


def load_checkpoint():
    checkpoint = torch.load(CHECKPOINT_PATH, map_location="cpu")
    _, model, optimizer, scaler, amp_enabled, dataset = build_components()
    model.load_state_dict(checkpoint["model"])
    optimizer.load_state_dict(checkpoint["optimizer"])
    scaler.load_state_dict(checkpoint["scaler"])
    dataset.load_state_dict(checkpoint["train_data_state"])
    torch.set_rng_state(checkpoint["torch_rng_state"])
    np.random.set_state(checkpoint["numpy_rng_state"])
    random.setstate(checkpoint["python_rng_state"])
    return {
        "step": int(checkpoint["step"]),
        "model": model,
        "optimizer": optimizer,
        "scaler": scaler,
        "amp_enabled": amp_enabled,
        "dataset": dataset,
    }


def train_loop(model, optimizer, scaler, amp_enabled, dataset, start_step, end_step, loss_prefix=None, save_at_step=None):
    loss_trace = list(loss_prefix or [])
    for step in range(start_step, end_step):
        lr = get_lr(step)
        for group in optimizer.param_groups:
            group["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        x, y = dataset.get_batch("cpu")
        with (torch.autocast(device_type="cpu", dtype=torch.bfloat16) if amp_enabled else nullcontext()):
            _, loss = model(x, y)
        scaled_loss = scaler.scale(loss)
        scaled_loss.backward()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()
        loss_trace.append(float(loss.item()))

        if save_at_step is not None and step + 1 == save_at_step:
            save_checkpoint(model, optimizer, scaler, dataset, step + 1)
            break

    return loss_trace


def compute_max_parameter_delta(model_a, model_b):
    delta = 0.0
    for param_a, param_b in zip(model_a.parameters(), model_b.parameters()):
        if param_a.numel() == 0:
            continue
        delta = max(delta, float((param_a.detach() - param_b.detach()).abs().max().item()))
    return delta


def compute_optimizer_delta(optimizer_a, optimizer_b, key):
    delta = 0.0
    for group_a, group_b in zip(optimizer_a.param_groups, optimizer_b.param_groups):
        for param_a, param_b in zip(group_a["params"], group_b["params"]):
            state_a = optimizer_a.state[param_a]
            state_b = optimizer_b.state[param_b]
            if key not in state_a or key not in state_b:
                continue
            delta = max(
                delta,
                float((state_a[key].detach() - state_b[key].detach()).abs().max().item()),
            )
    return delta


def run_continuous():
    seed_everything(manifest["seed"])
    _, model, optimizer, scaler, amp_enabled, dataset = build_components()
    loss_trace = train_loop(
        model=model,
        optimizer=optimizer,
        scaler=scaler,
        amp_enabled=amp_enabled,
        dataset=dataset,
        start_step=0,
        end_step=manifest["train_steps"],
    )
    final_val_loss = evaluate(model)
    return {
        "model": model,
        "optimizer": optimizer,
        "scaler": scaler,
        "amp_enabled": amp_enabled,
        "loss_trace": loss_trace,
        "final_val_loss": final_val_loss,
        "tokens_seen": manifest["train_steps"] * manifest["batch_size"] * manifest["block_size"],
        "final_lr": optimizer.param_groups[0]["lr"],
    }


def run_resumed():
    seed_everything(manifest["seed"])
    _, model, optimizer, scaler, amp_enabled, dataset = build_components()
    prefix_losses = train_loop(
        model=model,
        optimizer=optimizer,
        scaler=scaler,
        amp_enabled=amp_enabled,
        dataset=dataset,
        start_step=0,
        end_step=manifest["train_steps"],
        save_at_step=manifest["checkpoint_step"],
    )

    resumed = load_checkpoint()
    full_trace = train_loop(
        model=resumed["model"],
        optimizer=resumed["optimizer"],
        scaler=resumed["scaler"],
        amp_enabled=resumed["amp_enabled"],
        dataset=resumed["dataset"],
        start_step=resumed["step"],
        end_step=manifest["train_steps"],
        loss_prefix=prefix_losses,
    )
    final_val_loss = evaluate(resumed["model"])
    return {
        "model": resumed["model"],
        "optimizer": resumed["optimizer"],
        "scaler": resumed["scaler"],
        "amp_enabled": resumed["amp_enabled"],
        "loss_trace": full_trace,
        "final_val_loss": final_val_loss,
        "tokens_seen": manifest["train_steps"] * manifest["batch_size"] * manifest["block_size"],
        "final_lr": resumed["optimizer"].param_groups[0]["lr"],
    }


torch.use_deterministic_algorithms(True)

continuous = run_continuous()
resumed = run_resumed()

loss_deltas = [abs(a - b) for a, b in zip(continuous["loss_trace"], resumed["loss_trace"])]
report = {
    "dataset": manifest["dataset"],
    "seed": manifest["seed"],
    "total_steps": manifest["train_steps"],
    "checkpoint_step": manifest["checkpoint_step"],
    "batch_size": manifest["batch_size"],
    "block_size": manifest["block_size"],
    "continuous_loss_trace": continuous["loss_trace"],
    "resumed_loss_trace": resumed["loss_trace"],
    "continuous_final_val_loss": continuous["final_val_loss"],
    "resumed_final_val_loss": resumed["final_val_loss"],
    "max_train_loss_delta": max(loss_deltas) if loss_deltas else 0.0,
    "final_val_loss_delta": abs(continuous["final_val_loss"] - resumed["final_val_loss"]),
    "max_parameter_delta": compute_max_parameter_delta(continuous["model"], resumed["model"]),
    "max_exp_avg_delta": compute_optimizer_delta(continuous["optimizer"], resumed["optimizer"], "exp_avg"),
    "max_exp_avg_sq_delta": compute_optimizer_delta(continuous["optimizer"], resumed["optimizer"], "exp_avg_sq"),
    "continuous_final_lr": continuous["final_lr"],
    "resumed_final_lr": resumed["final_lr"],
    "continuous_tokens_seen": continuous["tokens_seen"],
    "resumed_tokens_seen": resumed["tokens_seen"],
    "scaler_enabled": bool(continuous["amp_enabled"] and resumed["amp_enabled"]),
    "scaler_scale_delta": abs(float(continuous["scaler"].get_scale()) - float(resumed["scaler"].get_scale())),
    "checkpoint_path": str(CHECKPOINT_PATH),
}

with OUTPUT_PATH.open("w") as f:
    json.dump(report, f, indent=2)

print(f"Wrote {OUTPUT_PATH}")
PY
