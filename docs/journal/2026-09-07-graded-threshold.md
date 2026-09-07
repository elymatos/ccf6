> **Reverted on the same day.** The graded threshold made the network's behaviour worse
> than the linear transfer it replaced, and it was removed from the code and the
> documentation. `recurrent_gain` went back to 0.55. This entry is kept as the record of
> what was tried and what it measured, not as a description of the current system.

# 2026-09-07 — A graded threshold on L4 → L2/3

## The request, and a correction

The change asked for was that L4's output to L2/3 be "some kind of sigmoid function and
not average." One clarification: **L4 → L2/3 was never an average.** It is within-column
and one-to-one — `drive = excitatory * l4`, a linear gain of 0.73, followed by a hard
clamp on the target. The averaging was in the *pooling between Levels*, and that was
already changed to summation earlier today. The substance of the request stands, though:
a linear gain with a hard clamp has no soft knee, so a Column is either proportional or
pinned, with nothing in between.

## What was built

A logistic transfer on L4's contribution to L2/3, anchored so that a silent L4 transmits
exactly nothing:

    sigma(x) = (L(x) - L(0)) / (1 - L(0)),  L(x) = 1 / (1 + exp(-gain * (x - midpoint)))

The anchoring matters. A plain logistic with midpoint 0.30 returns about 0.08 at zero,
and summed over a fan-in of eighteen at every Level that residue is exactly the
background accumulation the transmission threshold exists to prevent.

Midpoints can now be declared per Level, since a single knee turned out to be
insufficient — see below.

## What it exposed

**Recurrence and the threshold are coupled and cannot be set independently.** The L2/3
loop settles at `0.73 * sigma / (1 - excitatory * recurrent_gain)`. The sigmoid raises
`sigma` near the top of its range, which made the loop super-critical at the existing
recurrent gain of 0.55 and pinned L2/3 at its ceiling — 166 of 344 Columns. The loop is
sub-critical only for `recurrent_gain <= 0.37`. Lowered to **0.30**.

**A fixed knee has no right setting.** Measured L4 ranges after 250 ticks:

| Level | position Area | colour Area |
|---|---|---|
| L1 | 0.018 – 0.730 | 0.018 – 0.730 |
| L2 | 0.506 – 0.998 | 0.018 – 0.367 |
| L3 | 0.778 – 0.994 | 0.073 (constant) |

The two Areas move in **opposite directions**: drive rises with depth in the position
Area and falls in the colour Area, because one is 64 Columns wide with local pooling and
the other is 8. A midpoint low enough to pass the colour Area's top saturates the
position Area; one high enough to grade the position Area silences the colour Area. The
transition is sharp — between 0.50 and 0.55 the network flips from saturated-and-deep to
graded-and-shallow, with nothing in between.

Per-Level midpoints were implemented and do not fix it, because the two Areas need
opposite profiles rather than the same profile at different scales.

## Where it was left

`l4_sigmoid_midpoint` is **0.30**, marked provisional in `params.py`. That keeps the
whole cascade transmitting at the cost of saturating L2/3 in the wider Area. Selectivity
is unchanged to slightly better where the network is not saturated: colour selectivity at
`colour.L1` rose from 0.929 to **0.943** and `colour.L2` holds at **0.893**. The Hub's
colour score is still 0.000 — problem 5 from the first run is untouched by this change.

## The decision this forces

A threshold fixed in absolute terms cannot serve Columns whose drive differs by more than
an order of magnitude. The threshold has to be set relative to the drive a Column
actually receives. Three ways to do that:

1. **Divisive normalization at L4** — divide the summed drive by a semi-saturation
   constant plus the drive itself. This is the standard answer and it would revise
   ADR-0006, which excluded divisive normalization on the grounds that the source
   demonstration did not need it. That source is a hand-wired circuit of about twenty
   nodes with no fan-in; the exclusion does not survive a hierarchy.
2. **Homeostatic threshold adaptation** — each Column moves its own knee toward a target
   activity level. Well motivated: the source tradition lists threshold adjustment as a
   physical realization of learning. But it is a new mechanism and a form of learning,
   which the first experiment deliberately excludes.
3. **Scale the drive by fan-in before the threshold** — cheapest, but it reintroduces the
   attenuation that killed the very first run, in weaker form.

ADR-0006 has been annotated as under review rather than superseded. This is a decision
to take, not a parameter to sweep, and no more tuning should happen before it is taken.
