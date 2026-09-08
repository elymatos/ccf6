# 0009 — Contrast is not the input code

Status: accepted · 2026-09-08

Reverses the boundary premise stated in `docs/first-experiment.md` §"Contrast: what
actually reaches the network" and narrows `docs/architecture.md` §8.3.

## Context

From the first substrate onwards, what reached the Thalamus was not the World's colour
field but its **contrast**: the fraction of a cell's eight neighbours whose colour
differs from its own. The premise was that a framework meant to record relations between
things should be shown relations rather than things, so a region with no internal
relations registers as empty.

Contrast then acquired a second job. It was passed to `Thalamus.project` as `strength` —
*how hard* the boundary drives — while the signal itself determined *which* Columns are
driven. Columns add their inputs, so they are sensitive to strength, and strength was
therefore free to carry information the signal did not.

The first substrate recorded this as open problem 5: "strength and identity are
confused". It was carried forward into the two-abstractors foundation unresolved. Two
measurements now close it.

**Contrast is not translation invariant, so it contradicts ADR-0004.** The full
neighbourhood is the divisor everywhere, which fixed the border *inflation* — but
off-field neighbours count as not differing, so a figure cell touching the World frame
scores lower than the same cell in the middle. One Object at its 80 fitting origins in a
12x12 World produces **nine distinct contrast signatures**; only 48 origins see the
interior one. The same arrangement at a different World position is supposed to be the
same Object. Under contrast coding it is not.

**That non-invariance is the drive magnitude, so it reaches every Space.** Because
contrast is `strength` for every encoder, a colour Space is driven at a magnitude that
depends on where the figure sits. The unlearned baseline scores 0.64 on position against
0.008 on shape at the top of the convergence Space, with no position Space built and no
position encoder in the network. Contrast-as-strength is the only route position had.

The premise test that should have caught this compares `contrast().sum()` at two
*interior* origins, so it passed throughout.

## Decision

Contrast is removed from the input path. Specifically:

1. **The Thalamus is driven at unit strength.** There is no separate magnitude channel
   at the boundary. What is shown determines which Columns are driven, and nothing
   determines how hard.
2. **The local form encoder reads the colour neighbourhood**, not the contrast
   neighbourhood. It remains a *sensory* code for what is here.
3. **`World.contrast()` survives as analysis, not as input.** It is a property one can
   compute about a World and draw in the workbench. Nothing in the encoding path calls
   it. `Presentation.of_contrast` and `World.sampled_positions` keep it, and keep their
   explicit thresholds, for the case where the question really is "look wherever there
   is structure" — which is a segmentation question this project has not solved and does
   not claim to.

The translation-invariance premise test is strengthened to assert per-cell equality of
what the boundary encodes across **every** fitting origin, not `.sum()` at two of them.

## Alternatives considered

**Keep contrast and pad the World with a border.** Rejected: it buys invariance for
figures that fit inside the pad and moves the discontinuity rather than removing it,
while leaving strength and identity confused.

**Keep contrast as the signal but drive at unit strength.** Rejected as a half-measure:
it fixes the magnitude confound, but a 3x3 contrast patch is still non-invariant near
the frame, so the form Space would still see nine versions of one figure.

**Keep contrast and treat the frame as an edge.** Rejected: it makes the World's frame a
feature of the World, which it is not, and it inverts the problem rather than solving it
— figures would then register *more* strongly at the border.

## Consequences

The claim that CCF6 shows the network relations rather than things is **not abandoned,
it is relocated**. Relations between World positions are what the Schema integrates, and
a Relation is now the only relational quantity supplied at the boundary. Relations
between *cells within a neighbourhood* are no longer supplied at all; if they are needed
they must be learned, which is the honest position for a framework whose next spec is a
learning rule.

`docs/architecture.md` §8.3 — contrast coding yields edges, not regions — no longer
describes the boundary. Its open question, what happens to the interior of a solid
figure, becomes moot at the boundary and reappears untouched wherever local relations
are later learned.

The baseline moves. The 0.64 position score is expected to fall, and if it does not,
position is arriving by a route this ADR did not find. The 0.905 form-Space shortcut is
expected to survive: it comes from *locality*, not from contrast, and a 3x3 colour patch
distinguishes a T's junction from a bottom's junction just as well. That trap remains
real and remains the number a relational-learning claim has to beat.

A uniform World no longer produces nothing. Every visited position drives its colour
Column at full strength, white included, because white is an ordinary colour rather than
a gap. What makes an empty region uninteresting is now that Ego has no reason to visit
it, which is a decision about sampling rather than a property of the code.
