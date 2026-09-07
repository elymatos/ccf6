# 0002 — The Column is the primitive, with three private Layers

Status: accepted · 2026-09-07

## Context

A connectionist framework must choose its smallest addressable thing. The choice
determines what can be drawn, pointed at, and lesioned, and it is the hardest decision
to reverse.

## Decision

The primitive is a **Column** holding three private activations — L4 (input), L2/3
(processing and competition), L5 (output) — arranged as a simplified cortical circuit.
L4 receives from lower Levels and from the Thalamus and projects to L2/3. L2/3 receives
from L4, from L5 feedback above, and inhibitorily from grid neighbours, holds a
recurrent state, and projects to L5. L5 receives from L2/3 and projects to L4 above and
L2/3 below. No Column reads another's Layers except through declared connections.

## Alternatives considered

**A unit with a single scalar activation.** Classical, and the original decision. Given
up because it cannot express the input/process/output separation the circuit needs, and
because with one scalar there is nowhere for competition to act that is distinct from
where drive arrives.

**A population with an internal vector state.** Rejected: the individual element stops
being addressable, and the picture on screen stops being the thing in memory.

**Arrays with no element identity.** Faster; rejected because CCF6 is optimised for
being looked at, not for speed.

## Consequences

Grid position becomes mechanical rather than decorative, since lateral competition is
defined over neighbourhood. Each Level has three drawable fields rather than one. State
per Area is three floats per Column, which is negligible.
