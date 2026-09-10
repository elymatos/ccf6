# 0006 — Dynamics constants are declared, not derived

Status: superseded by ADR-0011 · 2026-09-09

## Context

Neither source tradition supplies usable numbers. The neurocognitive-linguistics
material gives no activation rule, no thresholds and no time constants, and explicitly
forbids treating the few figures it cites as simulator defaults. A working set had to
come from somewhere.

An interactive cortical-column demonstration supplied one. Its model is a bounded leaky
rate model: weighted excitatory, inhibitory and modulatory input produce a clamped
target, and each population relaxes toward that target with a class-dependent time
constant.

## Decision

Adopt that constant set as CCF6's declared defaults: route weights 0.73 excitatory, 0.48
modulatory, 0.90 inhibitory; target clamped to [0.018, 1.0]; exponential relaxation
`a += (target - a)(1 - exp(-dt/tau))` with tau by class. Every constant lives in the
experiment file, never in code.

## Alternatives considered

**Invent our own.** Rejected: a working set that produces bounded competitive dynamics
beats numbers with no provenance at all.

**Derive from the literature.** Rejected: the source material explicitly refuses to
license that, and the exercise would stall the first experiment indefinitely.

## Consequences

These numbers carry **no empirical authority**. They come from a conceptual
demonstration with no parameter fit and no validation, and must never be cited as
evidence about cortex. They are a starting point we own and may change freely.

Two properties are worth keeping deliberately. Exponential relaxation is the exact
solution for a constant target, so it cannot overshoot at any step size — better than
Euler integration for a system meant to be single-stepped. And the clamp floor is
0.018 rather than zero, so no Column is ever perfectly silent and the network cannot get
stuck dead.

Competition is **subtractive**, not divisive: inhibition is simply weighted more heavily
than excitation (0.90 against 0.73). Divisive normalization was considered and is not
used, because the source demonstrates that subtractive inhibition suffices.
