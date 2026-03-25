import argparse
from pathlib import Path

import numpy as np

from rankbench.objective import ObjectiveConfig, RankingObjective


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "fixed_batch.npz"
DEFAULT_OUTPUT = Path("/root/ranking_losses.npz")


def main(output_path: str = str(DEFAULT_OUTPUT)) -> None:
    batch = np.load(DATA_PATH)
    objective = RankingObjective(ObjectiveConfig(beta=2.5, gamma=0.8))
    losses = objective.compute_losses(
        chosen_token_logps=batch["chosen_token_logps"],
        rejected_token_logps=batch["rejected_token_logps"],
        chosen_lengths=batch["chosen_lengths"],
        rejected_lengths=batch["rejected_lengths"],
    )
    np.savez(output_path, losses=np.asarray(losses, dtype=np.float64))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    main(args.output)
