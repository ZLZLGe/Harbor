from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class ObjectiveConfig:
    beta: float = 2.5
    gamma: float = 0.8


def _masked_sums(token_logps: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    positions = np.arange(token_logps.shape[1])
    mask = positions[None, :] < lengths[:, None]
    return (token_logps * mask).sum(axis=1)


def length_normalized_bt_loss(
    chosen_token_logps: np.ndarray,
    rejected_token_logps: np.ndarray,
    chosen_lengths: np.ndarray,
    rejected_lengths: np.ndarray,
    beta: float,
    gamma: float,
) -> np.ndarray:
    """Return the per-example loss from the paper's length-normalized BT objective."""
    raise NotImplementedError("Implement Eq. (4) and Eq. (6) from the paper PDF.")


class RankingObjective:
    def __init__(self, config: Optional[ObjectiveConfig] = None) -> None:
        self.config = config or ObjectiveConfig()

    def compute_losses(
        self,
        chosen_token_logps: np.ndarray,
        rejected_token_logps: np.ndarray,
        chosen_lengths: np.ndarray,
        rejected_lengths: np.ndarray,
    ) -> np.ndarray:
        return length_normalized_bt_loss(
            chosen_token_logps=chosen_token_logps,
            rejected_token_logps=rejected_token_logps,
            chosen_lengths=chosen_lengths,
            rejected_lengths=rejected_lengths,
            beta=self.config.beta,
            gamma=self.config.gamma,
        )
