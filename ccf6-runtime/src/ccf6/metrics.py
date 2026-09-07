"""Measurements over a run's responses.

The first experiment runs with no learning, so whatever selectivity appears comes
from arbitrary connectivity. That number is not a disappointment: it is the null a
learning rule has to beat. Without it, the first learning result would have nothing
to be compared against.
"""

from __future__ import annotations

import numpy as np


def two_way_selectivity(responses: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """How much of each Column's variance is explained by colour, and by position.

    `responses` is (n_colours, n_positions, n_columns). Returns two vectors of length
    n_columns, each in [0, 1]. A Column responding to yellow wherever it appears
    scores high on colour and low on position; a Column responding to one World
    position whatever colour is there scores the reverse.

    A Column that never moved has no variance to explain and scores zero on both,
    rather than being credited with perfect selectivity for nothing.
    """
    n_colours, n_positions, _ = responses.shape
    grand = responses.mean(axis=(0, 1))
    by_colour = responses.mean(axis=1)      # (n_colours, n_columns)
    by_position = responses.mean(axis=0)    # (n_positions, n_columns)

    ss_total = ((responses - grand) ** 2).sum(axis=(0, 1))
    ss_colour = n_positions * ((by_colour - grand) ** 2).sum(axis=0)
    ss_position = n_colours * ((by_position - grand) ** 2).sum(axis=0)

    safe = ss_total > 1e-12
    colour = np.zeros_like(ss_total)
    position = np.zeros_like(ss_total)
    np.divide(ss_colour, ss_total, out=colour, where=safe)
    np.divide(ss_position, ss_total, out=position, where=safe)
    return colour, position


def summarise_by_level(
    colour: np.ndarray, position: np.ndarray, labels: list[str]
) -> dict[str, dict[str, float]]:
    """Per-Level maxima and means, which is what tells you whether depth did anything."""
    levels: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        level_name = label.split("#", 1)[0]
        levels.setdefault(level_name, []).append(index)

    summary = {}
    for level_name, indices in levels.items():
        idx = np.asarray(indices)
        summary[level_name] = {
            "columns": int(idx.size),
            "colour_selectivity_max": float(colour[idx].max()),
            "colour_selectivity_mean": float(colour[idx].mean()),
            "position_selectivity_max": float(position[idx].max()),
            "position_selectivity_mean": float(position[idx].mean()),
            "active_columns": int((colour[idx] + position[idx] > 1e-9).sum()),
        }
    return summary
