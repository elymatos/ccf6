# 0003 — Relations are given before they are enacted

Status: accepted · 2026-09-07

## Context

Learning relational structure requires a **Relation** between sampled positions. TEM
obtains one by acting: the agent moves and the movement selects the transformation.
That requires an agent, a movement policy, and an efference copy. The framework's first
experiment has none of these, and adding them is a substantial mechanism.

I-JEPA demonstrates that a static image suffices: its predictor is conditioned on the
**relative position** of the target it must predict, and it learns structure with no
agent, no time and no actions. The positional conditioning does the work the action
does.

## Decision

A Relation is the offset between two sampled World positions. It may be **given** — two
positions sampled together, geometry supplies the offset — or **enacted** — Ego moves,
movement supplies the offset. CCF6 implements given Relations first; enacted Relations
are layered on later as a measurable addition.

## Alternatives considered

**Enacted first.** Closest to TEM. Rejected as strictly more machinery for the same
structural content, and because a movement policy introduces drift before the dynamics
are trusted.

**Whole field presented at once with no Relations at all.** Rejected: it superposes what
and where, so no conjunction can be formed, and it leaves structure learning with no
mechanism.

## Consequences

The first experiment is one tick per stimulus, which keeps visualization simple.
Enaction becomes an experiment rather than an assumption — the effect of adding it can
be measured against the given-relation baseline. Mirrors the trajectory of the JEPA
line, where action conditioning was added after static prediction worked.
