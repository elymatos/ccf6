# 0009 — Contrast is not the input code

Status: accepted · 2026-09-08

Reverses the boundary premise in `docs/first-experiment.md` §"Contrast: what actually
reaches the network" and narrows `docs/architecture.md` §8.3.

## Context

From the first substrate onwards, what reached the Thalamus was not the World's colour
field but its **contrast**, the fraction of a cell's eight neighbours whose colour
differs from its own. The premise was that a framework meant to record relations between
things should be shown relations rather than things, so a region with no internal
relations registers as empty.

Contrast then picked up a second job. `Thalamus.project` took it as `strength`, meaning
how hard the boundary drives, while the signal decided which Columns it drives. Columns
add their inputs, so they respond to strength, and strength was free to carry
information the signal did not.

The first substrate wrote this down as open problem 5, "strength and identity are
confused". Nobody looked at it again, and the two-abstractors foundation inherited it.
Two measurements close it now.

**Contrast is not translation invariant, so it contradicts ADR-0004.** The divisor is the
full neighbourhood everywhere, which fixed the border *inflation*. It did not fix the
dependence. Off-field neighbours count as not differing, so a figure cell touching the
World frame scores lower than the same cell in the middle. One Object at its 80 fitting
origins in a 12x12 World produces **nine distinct contrast signatures**, and only 48
origins see the interior one. The same arrangement at a different World position is
supposed to be the same Object. Under contrast coding it is not.

**That non-invariance was also the drive magnitude, so it reached every Space.** A colour
Space was driven at a magnitude depending on where the figure sat. The unlearned baseline
scored 0.64 on position against 0.008 on shape at the top of the convergence Space, with
no position Space built and no position encoder anywhere in the network.
Contrast-as-strength was the only route position had.

The premise test that should have caught this compares `contrast().sum()` at two
*interior* origins. It passed throughout.

## Decision

Contrast leaves the input path.

1. **The Thalamus drives at unit strength.** No encoder takes a magnitude argument, so
   there is nowhere for a second code to hide. What is shown decides which Columns are
   driven. Nothing decides how hard.
2. **The local form encoder reads the colour neighbourhood.** Still a *sensory* code for
   what is here.
3. **`World.contrast()` survives as analysis.** It is something one can compute about a
   World and draw in the workbench, and nothing in the encoding path calls it.
   `Presentation.of_contrast` and `World.sampled_positions` keep it, with their explicit
   thresholds, for the case where the question really is "look wherever there is
   structure". That is a segmentation question this project has not solved and does not
   claim to.

The translation-invariance premise test now asserts per-Column equality of what the
boundary encodes across **every** fitting origin, rather than `.sum()` at two of them.

## Alternatives considered

**Pad the World with a border and keep contrast.** Rejected. It buys invariance for
figures that fit inside the pad, moves the discontinuity rather than removing it, and
leaves strength and identity confused.

**Keep contrast as the signal, drive at unit strength.** Rejected as half a fix. It
settles the magnitude confound, but a 3x3 contrast patch is still non-invariant near the
frame, so the form Space would go on seeing nine versions of one figure.

**Treat the World's frame as an edge.** Rejected. It makes the frame a feature of the
World, which it is not, and it inverts the problem instead of solving it. Figures would
then register *more* strongly at the border.

## Consequences

CCF6 still shows the network relations rather than things. The relation it shows has
moved. A Relation between two sampled World positions is now the only relational
quantity supplied at the boundary, and the Schema is what integrates it. Relations
between cells inside a neighbourhood are not supplied at all any more. If they turn out
to be needed they have to be learned, which is where a project whose next spec is a
learning rule ought to want them.

`docs/architecture.md` §8.3, on contrast coding yielding edges rather than regions, no
longer describes the boundary. Its open question about the interior of a solid figure is
moot there, and returns unchanged wherever local relations are later learned.

The baseline moved further than this ADR expected when it was written. Position variance
is now exactly zero, 1.1e-15, so the old 0.64 was contrast and nothing else. That also
broke the headline metric. Shape-versus-position selectivity is a variance ratio, and
with one factor at zero it reads 1.000 wherever a Column moves at all, so the run needed
a measure that still discriminates. `figure_separation` is it.

The local-feature shortcut survived, as expected. It comes from locality rather than
contrast, and a 3x3 colour patch tells a T's junction from a bottom's just as well. Form
now separates the figures best at its lowest Level, 0.148, and has lost most of the
distinction by its top, 0.050.

A uniform World no longer produces nothing. Every visited position drives its colour
Column at full strength, white included, because white is an ordinary colour rather than
a gap. What now makes an empty region uninteresting is that Ego has no reason to visit
it, which is a decision about sampling rather than a property of the code.
