from typing import Dict, List, Optional
import torch


class FedAvgError(Exception):
    pass


def fedavg(
    client_updates: List[tuple[Dict[str, torch.Tensor], int]],
) -> Dict[str, torch.Tensor]:
    """
    Weighted Federated Averaging.

    Each update contains:
        (state_dict, samples_trained)
    """

    if not client_updates:
        raise FedAvgError("No client updates provided")

    total_samples = sum(samples for _, samples in client_updates)

    if total_samples <= 0:
        raise FedAvgError("Total samples must be greater than zero")

    averaged = {}

    for key in client_updates[0][0]:
        weighted_sum = torch.zeros_like(
            client_updates[0][0][key],
            dtype=torch.float32,
        )

        for state_dict, samples in client_updates:
            if key not in state_dict:
                raise FedAvgError(
                    f"Missing key '{key}' in client update"
                )

            weight = samples / total_samples
            weighted_sum += state_dict[key].float() * weight

        averaged[key] = weighted_sum

    return averaged