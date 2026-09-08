# 2026-09-08 — Contrast leaves the input path, and the baseline changes shape

Second entry for the same day. The foundation ran; this is what re-examining its input
code did to it. ADR-0009.

## What was wrong

The boundary showed the network **contrast** — how much each cell differs from its eight
neighbours — rather than colour, on the premise that a framework meant to record
relations should be shown relations. Contrast was also passed to the Thalamus as
`strength`, the magnitude every encoder was driven at.

Both halves were load-bearing and both were wrong.

**Contrast is not translation invariant.** Off-field neighbours count as not differing,
so a figure touching the World's frame scores *lower* than the same figure in the middle.
The full-neighbourhood divisor, added on 7 September, removed the border inflation and
was mistaken for a fix. It was not: one T at its 80 fitting origins in a 12×12 World has
**nine distinct contrast signatures**, and only 48 origins see the interior one.

**And it was the drive magnitude, so that non-invariance reached every Space at once.**
Columns add their inputs, so a colour Space driven at a contrast-dependent magnitude has
position in it whether or not the colour code carries any.

This is exactly the open problem the first substrate recorded on 7 September — "strength
and identity are confused" — carried forward unresolved into the foundation and never
looked at again.

The premise test that should have caught it compares `contrast().sum()` at two
**interior** origins. It passed for the whole life of contrast coding.

## What changed

The Thalamus drives at unit strength; `project` has no magnitude argument and no encoder
takes one, so there is nowhere for a second code to hide. The form Space reads a padded
foreground mask instead of a contrast patch — a mask rather than colour indices, because
a raw index would drive one colour seven times harder than another and reintroduce the
same confusion. `World.contrast()` survives as analysis and nothing in the encoding path
calls it.

The invariance premise test is now per-Column, over **every** fitting origin, for every
figure in the confusion set.

## The baseline afterwards

Position variance is **exactly zero** — 1.1e-15, machine epsilon. ADR-0004 holds at the
boundary for the first time; the previous run's 0.64 position score was contrast, all of
it.

That broke the metric. Shape-versus-position selectivity is a variance ratio, and with
one factor at zero it reads 1.000 wherever a Column moves at all and 0.000 where it does
not. It cannot tell a Space that separates the confusion set from one that barely
twitches, so the run needed a number that still discriminates: **figure separation**, the
mean pairwise distance between the figures' responses over the population's own
magnitude.

| Level | separation (mean / max) | active |
| --- | --- | --- |
| colour.L1–L3 | 0.000 / 0.000 | 0 / 64 |
| form.L1 | **0.148 / 0.304** | 9 / 9 |
| form.L2 | 0.071 / 0.277 | 8 / 9 |
| form.L3 | 0.050 / 0.108 | 9 / 9 |
| convergence.L1 | 0.007 / 0.034 | 81 / 81 |
| convergence.L2 | 0.007 / 0.024 | 81 / 81 |

Schema path-consistency error 0.0 over 144 visited positions, all distinct. Index
completion 0.857.

Three things to carry forward.

**The local-feature shortcut survived, as ADR-0009 predicted it would.** The form Space
still separates the four figures best, and it does so at its *lowest* Level — 0.148 at
L1 falling to 0.050 by L3. Depth is losing the distinction, not building it. The shortcut
comes from locality, not from contrast: a 3×3 patch of a T's junction is oriented
differently from a ⊥'s whatever the patch is made of.

**The colour Space is now completely silent**, 0 of 192 Columns. Four figures of one
colour give it nothing to vary over, and the previous run's colour selectivity was
contrast-as-strength and nothing else. That is honest rather than broken, but it means
the confusion set exercises one Space and no more.

**Convergence still represents essentially nothing**, 0.007 against form's 0.148, with
every Column active. It is not dead; it is undifferentiated. That is the null a local
rule has to beat, and it is now a number that a rule could beat without the metric
flattering it.

## What this cost

The claim that CCF6 shows the network relations rather than things is relocated, not
abandoned: the Relation between two sampled World positions is now the only relational
quantity supplied at the boundary. Relations *within* a neighbourhood are no longer
supplied at all, and if they are wanted they must be learned — which is the right
position for a project whose next spec is a learning rule.

`docs/architecture.md` §8.3, on contrast coding yielding edges rather than regions, no
longer describes the boundary. Its open question about solid interiors is moot there and
returns untouched wherever local relations are later learned.
