# 0005 — Local learning rules only; no gradient descent

Status: accepted · 2026-09-07

## Context

The two source traditions disagree about where the learning signal comes from. TEM
learns by backpropagation through time across hundreds of environments — on the order of
50,000 gradient updates for 2D worlds. The neurocognitive-linguistics tradition holds
that a connection strengthens when its activation contributes to the successful
activation of its target: a local rule, with no global error signal.

## Decision

CCF6 uses local rules only. No autodiff framework, no backpropagation, no gradients.

## Alternatives considered

**Reproduce TEM first, then attempt local rules.** This was recommended, on the grounds
that reproducing a published result gives ground truth against which a failed local rule
can be interpreted. Rejected by the project owner.

**Both, as comparable arms.** Rejected as designing for a comparison before either side
exists.

## Consequences

There is no ground truth for the tasks CCF6 runs, so a negative result is ambiguous
between "the task is impossible" and "the rule is inadequate". This is mitigated by
measuring a **selectivity baseline** from arbitrary connectivity before any learning: the
number a learning rule must beat. Whether a local rule can reach what a gradient reaches
becomes the project's central scientific question rather than an implementation detail.
