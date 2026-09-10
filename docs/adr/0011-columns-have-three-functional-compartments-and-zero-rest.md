# Columns have three functional compartments and zero rest

Status: accepted · 2026-09-09

A Column retains three private compartments, now defined functionally as Input, Integration, and Output rather than by anatomical layer identity. Input integrates sensory and ascending activity, Integration combines Input with recurrent, descending, and inhibitory activity, and Output applies a graded learned threshold before broadcasting. Resting activity is exactly zero because a nonzero floor made unrelated population vectors artificially similar; numerical stability uses an epsilon without injecting activity.

This supersedes ADR-0002 and ADR-0006. Experiment definitions continue to declare numerical constants, while the specification now fixes equations, bounds, synchronous update order, and settling semantics.
