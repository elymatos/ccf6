"""Measurements over a run's responses.

The first experiment runs with no learning, so whatever selectivity appears comes
from arbitrary connectivity. That number is not a disappointment: it is the null a
learning rule has to beat. Without it, the first learning result would have nothing
to be compared against.
"""

from __future__ import annotations

import numpy as np


def two_way_selectivity(responses: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """How much of each Column's variance each of two factors explains.

    `responses` is (n_first, n_second, n_columns) from a factorial design, so the two
    factors vary independently and the decomposition can say which one a Column
    follows. Returns two vectors of length n_columns, each in [0, 1].

    The factors are whatever the experiment crossed — shape against position, or
    content against place. Keeping the names out of here is what lets one measurement
    serve both generalizations the architecture distinguishes: a readout that could
    not separate them would report structural transfer when only abstraction over
    instances had occurred.

    A Column that never moved has no variance to explain and scores zero on both,
    rather than being credited with perfect selectivity for nothing.
    """
    n_first, n_second, _ = responses.shape
    grand = responses.mean(axis=(0, 1))
    by_first = responses.mean(axis=1)       # (n_first, n_columns)
    by_second = responses.mean(axis=0)      # (n_second, n_columns)

    ss_total = ((responses - grand) ** 2).sum(axis=(0, 1))
    ss_first = n_second * ((by_first - grand) ** 2).sum(axis=0)
    ss_second = n_first * ((by_second - grand) ** 2).sum(axis=0)

    safe = ss_total > 1e-12
    first = np.zeros_like(ss_total)
    second = np.zeros_like(ss_total)
    np.divide(ss_first, ss_total, out=first, where=safe)
    np.divide(ss_second, ss_total, out=second, where=safe)
    return first, second


def summarise_by_level(
    first: np.ndarray,
    second: np.ndarray,
    labels: list[str],
    names: tuple[str, str] = ("shape", "position"),
) -> dict[str, dict[str, float]]:
    """Per-Level maxima and means, which is what tells you whether depth did anything.

    `names` labels the two factors, so a summary cannot report one factor under the
    other's name — a reader has no way to catch that from the numbers alone.
    """
    levels: dict[str, list[int]] = {}
    for index, label in enumerate(labels):
        level_name = label.split("#", 1)[0]
        levels.setdefault(level_name, []).append(index)

    a, b = names
    summary = {}
    for level_name, indices in levels.items():
        idx = np.asarray(indices)
        summary[level_name] = {
            "columns": int(idx.size),
            f"{a}_selectivity_max": float(first[idx].max()),
            f"{a}_selectivity_mean": float(first[idx].mean()),
            f"{b}_selectivity_max": float(second[idx].max()),
            f"{b}_selectivity_mean": float(second[idx].mean()),
            "active_columns": int((first[idx] + second[idx] > 1e-9).sum()),
        }
    return summary
