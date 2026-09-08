# 2026-09-07 — Sigmoid removed, and experiment 003

> **Written before the vocabulary split.** "Area" throughout this entry means what
> CCF6 now calls a **Space** — a stack of Levels over one conceptual dimension. "Area"
> now survives only as **Cortical Area** (frontal, parietal, temporal), and **Modality**
> (visual, auditory, tactile, motor, affective) names the channel that was never named
> before. The entry is left in its original wording as the record of what was said at
> the time; see CONTEXT.md for the current terms.

## The sigmoid is gone

Removed from `params.py`, `area.py`, `network.py`, the tests,
`docs/first-experiment.md` and the ADR-0006 annotation. `recurrent_gain` reverted to
**0.55**, since the drop to 0.30 existed only to keep the sigmoid's loop sub-critical.
`grep -ri sigmoid` over the source and docs comes back empty.

The one place it survives is [`2026-09-07-graded-threshold.md`](2026-09-07-graded-threshold.md),
now headed with a reversion note saying it made things worse and was removed. Deleting
it would falsify the record of what was tried — but it no longer describes the system.

## Experiment 003 — position representation

Position Area only. One Level. No colour Area, no Hub. `Architecture` now takes an
`areas` list, so an experiment asking about one Area does not have to run the others
and watch their activity clutter the picture.

**Level 1 holds all 64 positions apart with no duplication.**

| | |
|---|---|
| Positions presented | 64 |
| Distinct activation patterns | **64** |
| Distinct peak Columns | **64** |
| One peak Column per position | **yes — a bijection** |
| Duplicate pairs | **0** |
| Silent positions | 0 |
| Most similar two positions (cosine) | 0.3989 |
| Average similarity | 0.1507 |

The tensor framing is exactly right: the Level's output *is* a 64-element vector per
position, and the 64 vectors form a 64×64 matrix. The peak Column equals the position
index for **all 64** positions, so it is a clean permutation.

One thing the numbers show that is worth noticing: peak values range **0.224 to 0.630**,
and the weakest is (0,0) with contrast 0.375. Border positions fire less hard because
they have fewer neighbours to differ from. That is amplitude, not identity — cosine
similarity ignores magnitude, so the code stays unambiguous — but it means a downstream
Level summing these inputs sees corner positions as weaker. That is the same
strength-versus-identity confusion as finding 5, showing up in the position pathway.

## The new page

Because the question is different, this run gets its own view, chosen by experiment kind:

- **A verdict line** stating the answer, green or red.
- **All 64 positions side by side** — an 8×8 arrangement of tiles, each with the World
  on the left (colour at that position, real palette colours) and `position.L1`'s output
  on the right, on the same 8×8 Grid. Each Level thumbnail is scaled to its own peak so
  a weak border pattern stays readable.
- **A 64×64 similarity matrix.** Dark is alike, pale is different, diagonal always 1.
  Any dark cell off the diagonal would be a duplicate — there are none, and the panel
  beside it lists duplicate pairs when there are any.
- The wiring table for the single Level.

10 Python tests and 2 PHP tests pass; experiments 001 and 003 both render.
