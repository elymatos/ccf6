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

    The factors are whatever the experiment crossed. Keeping their names out of this
    calculation lets the same measurement evaluate different sensory and conceptual
    populations.

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


def conjunction_selectivity(responses: np.ndarray) -> np.ndarray:
    """How much of each Column's variance neither factor explains on its own.

    This measures whether an association Column integrates two factors. A Column that follows shape
    scores its variance under shape; one that follows colour scores it under colour; a
    Column that answers to a *particular shape in a particular colour* and not to that
    shape in another colour has variance that neither main effect predicts. That
    residual is the conjunction.

    With one presentation per cell there is no replication, so everything the two main
    effects leave over is the interaction. Returns a vector in [0, 1] per Column, and
    the three parts sum to 1 wherever a Column moved at all.
    """
    first, second = two_way_selectivity(responses)
    return np.clip(1.0 - first - second, 0.0, 1.0) * (first + second > 0)


def figure_separation(responses: np.ndarray) -> np.ndarray:
    """How far apart the figures' responses are, per Column, relative to their size.

    Needed because the two-way ratio went degenerate. Once the boundary became
    translation invariant (ADR-0009) the second factor contributes *exactly* zero
    variance, so `shape / (shape + position)` is 1.0 wherever a Column moves at all and
    0.0 where it does not. It no longer distinguishes a Population that separates the
    confusion set from one that barely twitches.

    This one can. Average the pairwise distance between the figures' mean responses and
    divide by the population's own magnitude, so a large but undifferentiated response
    scores low. Zero means the figures are indistinguishable here. It is the number a
    learning rule has to beat, and unlike a variance ratio the other factor going quiet
    cannot inflate it.
    """
    means = responses.mean(axis=1)                      # (n_figures, n_columns)
    n = means.shape[0]
    if n < 2:
        return np.zeros(means.shape[1])
    scale = np.linalg.norm(means, axis=0)
    gaps = np.zeros(means.shape[1])
    pairs = 0
    for a in range(n):
        for b in range(a + 1, n):
            gaps += np.abs(means[a] - means[b])
            pairs += 1
    gaps /= pairs
    out = np.zeros_like(gaps)
    np.divide(gaps, scale, out=out, where=scale > 1e-12)
    return out


def population_separation(responses: np.ndarray) -> tuple[float, np.ndarray]:
    """How far apart the figures are as *patterns over a whole population*.

    `figure_separation` scores one Column at a time, and a Column is not where a figure
    lives. What stands for a figure at a Level is the pattern across every Column that
    reached it, so a per-Column score answers a different question: not "does this Level
    tell the figures apart" but "does this Column, alone, tell them apart".

    The difference is not cosmetic, and it runs the wrong way with depth. A Level doing
    its job concentrates a figure onto fewer Columns, which lowers the per-Column mean
    exactly when the Level has got better. Averaging over Columns therefore penalizes
    successful convergence.

    So: the mean Euclidean distance between the figures' mean population vectors,
    divided by the population's own rms magnitude. Returns that mean and the full
    pairwise matrix, because a mean cannot show *which* figures a Level has merged, and
    merging two of four is the failure worth seeing.
    """
    means = responses.mean(axis=1)                       # (n_figures, n_columns)
    n = means.shape[0]
    matrix = np.zeros((n, n))
    if n < 2:
        return 0.0, matrix

    scale = float(np.linalg.norm(means) / np.sqrt(n))
    if scale <= 1e-12:
        return 0.0, matrix

    for a in range(n):
        for b in range(a + 1, n):
            d = float(np.linalg.norm(means[a] - means[b]) / scale)
            matrix[a, b] = matrix[b, a] = d
    return float(matrix[np.triu_indices(n, 1)].mean()), matrix


def summarise_by_level(
    first: np.ndarray,
    second: np.ndarray,
    labels: list[str],
    names: tuple[str, str] = ("shape", "position"),
    separation: np.ndarray | None = None,
    responses: np.ndarray | None = None,
    figures: list[str] | None = None,
    traces: np.ndarray | None = None,
    conjunction: np.ndarray | None = None,
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
        if conjunction is not None:
            summary[level_name]["conjunction_selectivity_max"] = float(conjunction[idx].max())
            summary[level_name]["conjunction_selectivity_mean"] = float(conjunction[idx].mean())
        if separation is not None:
            summary[level_name]["separation_max"] = float(separation[idx].max())
            summary[level_name]["separation_mean"] = float(separation[idx].mean())
        if traces is not None:
            # The same population measure over the ordered traversal instead of its
            # average: stop k's activity stays at position k, so two traversals of one
            # figure's cells in different orders are different vectors.
            ordered = traces[:, :, :, idx].reshape(traces.shape[0], traces.shape[1], -1)
            mean, matrix = population_separation(ordered)
            summary[level_name]["traversal_separation"] = mean
        if responses is not None:
            mean, matrix = population_separation(responses[:, :, idx])
            summary[level_name]["population_separation"] = mean
            # Which figures a Level has merged, not merely how much it separates on
            # average. Labelled by figure so the matrix cannot be read in the wrong
            # order once it is out of this function.
            summary[level_name]["figure_distances"] = {
                f"{figures[a]} vs {figures[b]}": float(matrix[a, b])
                for a in range(matrix.shape[0])
                for b in range(a + 1, matrix.shape[0])
            } if figures else matrix.tolist()
    return summary
