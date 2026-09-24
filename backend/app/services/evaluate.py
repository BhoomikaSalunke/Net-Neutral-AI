from dataclasses import dataclass
from typing import Dict

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


@dataclass
class EvalResult:
    accuracy: float
    precision: Dict[int, float]
    recall: Dict[int, float]
    f1: Dict[int, float]
    macro_precision: float
    macro_recall: float
    macro_f1: float
    support: Dict[int, int]
    avg_loss: float
    total_samples: int
    correct: int


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    device: torch.device | None = None,
) -> EvalResult:

    if device is None:
        device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

    model = model.to(device)
    model.eval()

    criterion = nn.CrossEntropyLoss()

    total_loss = 0.0
    num_batches = 0
    predictions = []
    labels = []

    with torch.no_grad():
        for batch_ids, batch_labels in dataloader:
            batch_ids = batch_ids.to(device)
            batch_labels = batch_labels.to(device)

            logits = model(batch_ids)
            loss = criterion(logits, batch_labels)

            total_loss += loss.item()
            num_batches += 1

            preds = logits.argmax(dim=1)

            predictions.extend(preds.cpu().tolist())
            labels.extend(batch_labels.cpu().tolist())

    model.cpu()

    return _compute_metrics(
        predictions,
        labels,
        total_loss / max(num_batches, 1),
    )


def _compute_metrics(
    predictions: list,
    labels: list,
    avg_loss: float,
) -> EvalResult:

    classes = [0, 1]

    total = len(labels)
    correct = sum(
        prediction == label
        for prediction, label in zip(predictions, labels)
    )

    tp = {c: 0 for c in classes}
    fp = {c: 0 for c in classes}
    fn = {c: 0 for c in classes}

    for prediction, label in zip(predictions, labels):
        for c in classes:
            if prediction == c and label == c:
                tp[c] += 1
            elif prediction == c and label != c:
                fp[c] += 1
            elif prediction != c and label == c:
                fn[c] += 1

    precision = {}
    recall = {}
    f1 = {}
    support = {}

    for c in classes:
        support[c] = sum(label == c for label in labels)

        precision[c] = (
            tp[c] / (tp[c] + fp[c])
            if tp[c] + fp[c] > 0
            else 0.0
        )

        recall[c] = (
            tp[c] / (tp[c] + fn[c])
            if tp[c] + fn[c] > 0
            else 0.0
        )

        f1[c] = (
            2 * precision[c] * recall[c]
            / (precision[c] + recall[c])
            if precision[c] + recall[c] > 0
            else 0.0
        )

    macro_precision = sum(precision.values()) / 2
    macro_recall = sum(recall.values()) / 2
    macro_f1 = sum(f1.values()) / 2

    return EvalResult(
        accuracy=correct / total if total else 0.0,
        precision=precision,
        recall=recall,
        f1=f1,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        macro_f1=macro_f1,
        support=support,
        avg_loss=avg_loss,
        total_samples=total,
        correct=correct,
    )