# 2026-09-08 — The foundation of the two-abstractors architecture

Replaced the runtime and the workbench with the architecture's foundation: a boundary
that presents multi-part figures, sparse connectivity, and the Web, Schema and Index
wired but not learning. Issue #1. Nothing learns, and the deliverable is the baseline
that a local rule will have to beat.

## What now exists

A presentation is a **sequence**. Ego visits a figure's parts in a declared order, the
Thalamus encodes what is at each stop, and the offset to the next stop is the given
Relation (ADR-0003). Before this, only one World position could be shown per tick, so
no arrangement could reach the network at all.

Connections are stored as triplets, so memory scales with the number of connections
rather than the square of the population: the wiring that would have cost 134 MB dense
costs under a megabyte. Fan-in is declared per connection class, and a configuration
where a Column could see everything below it is refused at construction.

## The baseline

Four figures — T, ⊥, ⊢, ⊣ — at 64 World positions, 150 ticks per stop.

| Level | shape | position | active |
| --- | --- | --- | --- |
| colour.L1–L3 | 0.47 → 0.23 | 0.67 | 44 → 63 / 64 |
| form.L1–L3 | **0.85 → 0.87** | 0.58 | 9 / 9 |
| convergence.L1 | 0.20 | 0.65 | 81 / 81 |
| convergence.L2 | **0.008** | 0.64 | 81 / 81 |

Two things to carry forward.

**The convergence Space carries position, not shape.** 0.008 on shape against 0.64 on
position. This is the same shape the previous substrate's baseline had, arrived at
through different wiring, and it is the number a learning rule has to beat.

**The form Space separates the figures without learning anything**, at 0.905. This is
the local-feature shortcut the architecture warned about (§6.5): averaging a 3×3
contrast patch over a figure's stops already distinguishes a T from a ⊥, because the
junction patch is oriented differently. It is not a defect in the run — it is the trap
being real and measurable, and it means a later claim of relational learning must beat
0.905 rather than zero, and must be made at a Level where no single patch could do the
work.

## Five things found by building it

**An unordered bag of offsets cannot separate the confusion set.** `Object.relations()`
stores every pairwise offset as an unordered multiset, and that multiset is closed under
reflection whenever the figure's bar is symmetric. So T and ⊥ store *identically*, as do
⊢ and ⊣. The bag keeps which offsets occur and discards how they were traversed. The
ordered walk of Relations separates all four. This is why the Schema is advanced by a
sequence rather than handed a set, and it sharpens ADR-0004: part-relative structure is
necessary for translation invariance but is not by itself sufficient to identify a
figure. Recorded as two premise tests, one for each half.

**Contrast cannot segment figure from ground.** For a thin-stroke figure the figure's
own cells score 0.5–0.875 and the background cells hugging it score 0.125–0.5. The
ranges overlap exactly, so no threshold separates them. Segmentation is a separate hard
problem and is not claimed here: an experiment presents a known Object and Ego visits
its parts. The contrast-driven constructor survives for the case where the question
really is "look wherever there is structure", and it takes its threshold explicitly so
nobody acquires a segmenter by accident.

**Local pooling assumes a Grid's neighbourhood means something.** For a Space over
colour or local form it does not — adjacency there is an artefact of laying a
one-dimensional dimension out on a square. Pooling is off by default and waits for a
Space with a real neighbourhood.

**Fan-in has to be declared per connection class, not once.** A convergence Space draws
from the tops of every Space at once. With the fan-in sized for a narrow spoke (4 of 73
sources, only 32 of them non-zero), its Level-1 output averaged 0.047 against a
transmission threshold of 0.055 — so almost nothing reached its own top and the Index
had no content to bind. A declared convergence fan-in of 12 fixed it.

**A closure over the contrast field is a trap.** The signal function read
`World.contrast()` once, before any figure was placed, so the form Space was handed an
empty patch for the whole run and sat at the activation floor. It looked exactly like a
wiring problem. The field is a property of the World as it stands, and is now rebuilt
after every placement.

## Deliberately not done

No learning, no recruitment, no promotion. Enacted Relations remain a later addition to
be measured against the given-Relation baseline. Scale and rotation are untouched, and
rotation is excluded by the signed-invariance rule rather than postponed: ⊥ is a T
rotated 180°, so a rotation-invariant system could not tell them apart.

Web, Schema and Index are the architecture's candidate names and are not in CONTEXT.md.
A rename is expected and will touch the runtime, the artifact contract and the workbench
together.
