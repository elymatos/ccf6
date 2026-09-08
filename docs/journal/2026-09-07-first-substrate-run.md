# 2026-09-07 — Deciding the architecture, and the first run

> **Written before the vocabulary split.** "Area" throughout this entry means what
> CCF6 now calls a **Space** — a stack of Levels over one conceptual dimension. "Area"
> now survives only as **Cortical Area** (frontal, parietal, temporal), and **Modality**
> (visual, auditory, tactile, motor, affective) names the channel that was never named
> before. The entry is left in its original wording as the record of what was said at
> the time; see CONTEXT.md for the current terms.

## What happened

A long grilling session settled the architecture from a blank slate, deliberately
without consulting CCF7 (ADR-0001). Then the substrate was built and run for the first
time. It runs; it also found five problems, which is what a first run is for.

## Decisions taken

Recorded as ADRs 0001–0008. The ones that shaped the code most:

- The **Column** is the primitive, holding three private Layers (L4, L2/3, L5). This
  replaced an earlier decision that the primitive was a unit with one scalar
  activation, which could not express input/process/output separation.
- **Relations are given before they are enacted.** I-JEPA showed that a static image
  suffices if the predictor is conditioned on relative position, so a Relation does not
  require movement — only an offset. This is why the first experiment has no fovea.
- **Structure is stored part-relative**, so translation invariance is a property of the
  representation rather than something to be learned.
- **Cardinal Nodes are multimodal by definition**, so they cannot exist inside one Area.
  This forced the Hub into the first configuration rather than deferring it, and it
  meant the top of an Area needed its own name: **Convergence Node**.

Two things decided but not written as ADRs, because they are cheap to reverse: the
workbench is Blade with hand-written CSS, Alpine from a CDN and no build step; Grids are
drawn as canvas heatmaps rather than node-link graphs, since a Grid is image-shaped and
Cytoscape would have been the wrong tool. Cytoscape was dropped from the plan entirely.

## Deviation from the stated architecture

The proposal described seven Levels of 64x64 Columns per Area. The World was then
settled at 8x8, which makes seven Levels of 4,096 Columns absurd for a 64-position
World. The first configuration uses **three Levels** for the spokes and two for the Hub,
on 8x8 Grids. Level count and Grid shape are both experiment-file parameters, so this is
a default rather than a commitment.

## What the first run found

**1. Averaging pooling cannot carry a sparse signal.** Pooling weights were
row-normalised, so one active source among sixteen arrived at 1/16 strength, and the
0.018 activation floor meant the other fifteen contributed background that swamped it.
Nothing propagated past Level 2. Fixed: Columns now *sum* their inputs, and transmit
`max(0, L5 - transmission_threshold)` so the floor keeps the network alive without
accumulating through depth. The threshold, 0.055, comes from the same source as the
route weights, where it gates the displayed signal.

**2. The cascade is twelve laminae deep and thirty ticks is nowhere near settling.**
Three Layers times three Levels plus the Hub, each a first-order filter moving ~12% per
tick. At tick 30 the signal was still climbing through Level 1. Settles by ~200; runs
now use 250. A full factorial run is 448 stimuli in about 20 seconds.

**3. Contrast as a *fraction of neighbours* is not translation-invariant.** Border cells
have fewer neighbours, so the same Object registered more strongly near an edge. Found
by a test, not by inspection. Fixed by dividing by the full neighbourhood and counting
off-field neighbours as not differing: the frame of the World is not an edge in the
World. Interior positions are now exactly invariant; positions within one cell of the
border are attenuated rather than inflated.

**4. Sparse non-local convergence degenerates when fan-in is not smaller than its
source.** With a localist colour code the colour Area is 8 Columns wide and fan-in is
12, so every top Column sampled all 8 and they became identical. Colour selectivity at
the top of the colour Area was 0.001. Swapping in the population colour encoder — 64
Columns, no other change, which is what the Thalamus seam is for — raised it to 0.213.

**5. Drive strength and drive identity are conflated, and strength wins.** Contrast is
used as the amplitude of the thalamic projection, so *which* Column fires carries
colour while *how hard* it fires carries position. Levels that sum their inputs are
sensitive to amplitude, and by the top of the colour Area position explains 99% of the
variance. The Hub then receives position from both spokes and shows essentially no
colour selectivity. **This is unresolved and needs discussion before the next step.**

## The baseline

The number the whole run exists to produce. With arbitrary connectivity and no learning,
the maximum colour selectivity anywhere in the Hub is **0.007** (population encoder) or
**0.000** (localist). That is the null a learning rule has to beat.

Spoke selectivity is uninformative: the position Area scores 1.000 on position because
colour never enters it, which is a fact about the wiring rather than about the network.
Only the Hub number means anything.

## Next

Finding 5 is architectural and should be discussed rather than patched. The obvious
candidates — normalise the thalamic projection to unit strength and let contrast gate
only *whether* a sample occurs, or carry contrast as its own channel — are different
claims about what contrast is, and picking one silently would be the wrong move.
