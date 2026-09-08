"""The Index: what happened where.

Binds a content activation to a Schema state — *this thing, here* — and completes the
pair from either half. Written in one exposure, because anything needing repetition
cannot serve as episodic memory.

The rule is Hebbian and local: co-active units strengthen their connection. That is a
local rule in the sense of ADR-0005, not a gradient, so it is available to the
foundation even though no *slow* learning happens yet — nothing in the Web or the
Schema changes, nothing is recruited, and nothing is promoted.

Completion is a similarity match against stored bindings rather than a settling
dynamic over one superposed matrix. Superposition is what makes an associative memory
average its entries under load, and averaging is precisely what this structure exists
not to do (§2.1): its pressure is separation. Keeping bindings addressable
individually is the cheapest way to hold that line, and it makes "did the entries
merge?" a question the tests can actually ask.
"""

from __future__ import annotations

import numpy as np


class Index:
    """A store of conjunctions, sparse and separating."""

    def __init__(self, content_size: int, schema_size: int, floor: float = 1e-9):
        self.content_size = content_size
        self.schema_size = schema_size
        self.floor = floor
        self._content: list[np.ndarray] = []
        self._schema: list[np.ndarray] = []

    @property
    def entries(self) -> int:
        return len(self._content)

    def reset(self) -> None:
        self._content.clear()
        self._schema.clear()

    def write(self, content: np.ndarray, schema_state: np.ndarray) -> None:
        """Bind one content to one Schema state, in a single exposure."""
        if content.size != self.content_size or schema_state.size != self.schema_size:
            raise ValueError(
                f"expected content of {self.content_size} and state of {self.schema_size}, "
                f"got {content.size} and {schema_state.size}"
            )
        self._content.append(np.asarray(content, dtype=np.float64).copy())
        self._schema.append(np.asarray(schema_state, dtype=np.float64).copy())

    def complete(
        self, content: np.ndarray | None = None, schema_state: np.ndarray | None = None
    ) -> tuple[np.ndarray, np.ndarray]:
        """Recover the whole binding from either half, or from both.

        Returns `(content, schema_state)`. With nothing stored, or a cue matching
        nothing, both come back empty: an Index must not invent a binding.
        """
        if content is None and schema_state is None:
            raise ValueError("completion needs a content cue, a Schema state, or both")

        empty = (np.zeros(self.content_size), np.zeros(self.schema_size))
        if not self._content:
            return empty

        similarity = np.zeros(self.entries)
        if content is not None:
            similarity += _match(np.stack(self._content), content)
        if schema_state is not None:
            similarity += _match(np.stack(self._schema), schema_state)

        if similarity.max() <= self.floor:
            return empty

        # Winner takes most rather than all: a graded blend over what actually matched,
        # so a cue between two stored bindings reports the ambiguity instead of hiding
        # it behind an arbitrary tie-break.
        weights = np.where(similarity > self.floor, similarity, 0.0)
        weights = weights / weights.sum()
        return (
            weights @ np.stack(self._content),
            weights @ np.stack(self._schema),
        )

    def stored(self) -> list[tuple[np.ndarray, np.ndarray]]:
        """Every binding, as (content, Schema state). For measurement and drawing."""
        return list(zip(self._content, self._schema))

    def describe(self) -> dict:
        return {
            "content_size": self.content_size,
            "schema_size": self.schema_size,
            "entries": self.entries,
        }


def _match(stored: np.ndarray, cue: np.ndarray) -> np.ndarray:
    """Cosine similarity of a cue against every stored half.

    Cosine rather than a dot product so that a partial cue — a third of a pattern —
    matches as strongly as the whole, which is what "completes from a partial cue"
    has to mean.
    """
    cue_norm = np.linalg.norm(cue)
    if cue_norm <= 1e-12:
        return np.zeros(stored.shape[0])
    norms = np.linalg.norm(stored, axis=1)
    scores = stored @ cue
    safe = norms > 1e-12
    out = np.zeros(stored.shape[0])
    np.divide(scores, norms * cue_norm, out=out, where=safe)
    return np.maximum(out, 0.0)
