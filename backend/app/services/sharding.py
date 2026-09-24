from typing import List, Tuple


def create_shards(
    data: List,
    num_clients: int,
) -> List[List]:
    """
    Split data into approximately equal-sized shards.

    Any remainder is distributed across the first few clients.
    """

    if num_clients <= 0:
        raise ValueError("num_clients must be greater than 0")

    if not data:
        return [[] for _ in range(num_clients)]

    num_clients = min(num_clients, len(data))

    base_size = len(data) // num_clients
    remainder = len(data) % num_clients

    shards = []
    start = 0

    for i in range(num_clients):
        size = base_size + (1 if i < remainder else 0)
        shards.append(data[start:start + size])
        start += size

    return shards


def create_index_shards(
    total_samples: int,
    num_clients: int,
) -> List[Tuple[int, int]]:
    """
    Return (start, end) index ranges for each client.
    End index is exclusive.
    """

    indices = create_shards(
        list(range(total_samples)),
        num_clients,
    )

    return [
        (shard[0], shard[-1] + 1) if shard else (0, 0)
        for shard in indices
    ]