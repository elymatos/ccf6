# The first experiment, in plain English

This explains what experiment 001 does, what every term in the workbench means, and how
to read the result. No prior knowledge of the framework is assumed.

## The short version

We built a small network, showed it a single coloured dot in every possible place, and
measured what each part of the network responded to. **Nothing learned.** The connections
were fixed before the run and never changed. The point was to find out what the network
does *before* learning, so that when we add learning we can tell whether it helped.

## The pieces

### The World

An 8×8 grid of coloured cells — 64 cells in total. Every cell has a colour, and **white
is a colour, not an empty space**. This matters: a blank cell is a fact the network has
to represent, not a gap it can ignore.

For this experiment the World holds one coloured cell and 63 white ones. We do that 448
times: 7 colours × 64 positions.

### Contrast: what actually reaches the network

The network is never shown colours directly. It is shown **contrast** — how much each
cell differs from the eight cells around it.

- A red cell surrounded by eight white cells differs from all eight, so its contrast is
  **8/8 = 1.0**.
- A white cell in the middle of a white region differs from nothing, so its contrast is
  **0**.
- A red cell in the *corner* has only three neighbours inside the World, so its contrast
  is **3/8 = 0.375**.

This is deliberate. The framework is meant to record *relations between things* rather
than things themselves, so a region with nothing going on inside it should register as
empty. A completely uniform World produces no activity at all.

The corner case is not a bug but it does have consequences — see "What went wrong" below.

### The Column

The network's basic unit. Think of it as a tiny processor with **three internal stages**:

| Stage | Role |
|---|---|
| **L4** | Input. Receives from the Level below, or from the Thalamus. |
| **L2/3** | Processing. Combines L4, its own previous state, feedback from above, and inhibition from its neighbours. |
| **L5** | Output. What this Column sends to other Columns. |

The three stages are **private**: no other Column can see inside. Columns only ever see
each other's L5 output. This is why the workbench draws L5 and not the internals — the
internals are not what any other part of the network reacts to.

A Column holds no symbol, label or meaning. What it does is entirely a consequence of
what it is connected to.

### Level, Grid, Space

- A **Grid** is an 8×8 arrangement of Columns — 64 Columns.
- A **Level** is one Grid. Levels are stacked: Level 1 is nearest the input, Level 3 is
  furthest from it.
- A **Space** is a stack of Levels over one conceptual dimension — position, colour,
  temperature. The dimension is the job.

Each Space also declares two things that are not its job. Its **Modality** is the
channel its content arrives through — visual, auditory, tactile, motor, affective. Its
**Cortical Area** is where it sits — frontal, parietal, temporal — and that is an
anatomical claim and nothing more.

This experiment has three Spaces:

| Space | Levels | Dimension | Cortical Area | Modality |
| --- | --- | --- | --- | --- |
| **position** | 3 | *where* something is | parietal | visual |
| **colour** | 3 | *what* colour it is | temporal | visual |
| **hub** | 2 | the conjunction of the two | frontal | — |

Note that position and colour are **both visual**. They are two Spaces because they are
codes for two different dimensions, not because they arrive through two different
channels. The Hub receives from the tops of both and is the only place *what* and
*where* can meet; being fed by Spaces rather than by the World, it carries no Modality
of its own.

### The Thalamus

The structure between the World and the Spaces. It turns one World signal into activity
across Columns, and it is the only place the encoding decision lives.

In experiment 001 it uses a **localist** code: colour 3 becomes Column 3 firing, and
nothing else. Experiment 002 swaps this for a **population** code, where one colour
becomes a broad bump of activity across many Columns. That swap is one line in the
experiment file and touches nothing else — that is the entire reason the Thalamus is a
separate structure.

## Fan-in and fan-out

These are the terms the workbench's wiring table uses.

- **Fan-in** — how many Columns send *into* one Column. If a Column's fan-in is 18, then
  18 Columns from the Level below feed it.
- **Fan-out** — the reverse: how many Columns one Column sends *to*.

An analogy: in a company org chart, fan-in is how many people report to you, and fan-out
is how many managers you report to. Neither term says anything about *strength* — only
about *how many*.

**Why fan-in matters here.** A Column adds up everything arriving at it. If a Column's
fan-in is 18 and only one of those 18 is active, the signal has to survive being mixed
with 17 quiet ones. Get this wrong and either nothing propagates or everything saturates.
Both happened on the first attempt.

There is also a subtler trap. If a Column's fan-in is *as large as the Level below*, then
every Column at that Level receives from every Column below — so they all receive exactly
the same thing and become identical. A Level of identical Columns cannot distinguish
anything. This is exactly what happened to the colour Space in run 001.

## How Columns connect

Four kinds of connection, and every Column has all four.

### 1. Upward (feed-forward): L5 → L4 of the Level above

This is how information climbs the hierarchy. Two different rules are used, depending on
depth:

**Local pooling, at the lower Levels.** A Column draws from a 4×4 neighbourhood centred
on its own position in the Level below. Because the neighbourhoods overlap, the amount of
World each Column can see grows with depth:

| Level | Draws from | Fan-in | Receptive field |
|---|---|---|---|
| L1 | the Thalamus, one-to-one | 1 | 1 cell |
| L2 | L1, a 4×4 neighbourhood | ~18 | 4×4 cells |
| L3 | L2, 12 Columns from anywhere | 12 | the whole World |

**Sparse non-local, at the top Level.** Instead of a neighbourhood, each Column draws
from 12 Columns picked at random from anywhere in the Level below.

Why the change? Because local pooling has a ceiling. Receptive fields grow by 3 cells per
Level, so reaching the whole 8×8 World by local pooling alone would take several more
Levels than we have. Sparse non-local sampling reaches everything immediately, and gives
each Column a *different* random input set — which is what makes it possible for
different Columns to come to stand for different things.

### 2. Downward (feedback): L5 → L2/3 of the Level below

Whatever a Column draws from, it feeds back to. Feedback arrives at L2/3 rather than L4,
so it *biases* processing rather than acting as fresh input. Its gain is 0.35, roughly a
third the strength of the upward drive: context nudges, it does not dictate.

### 3. Sideways (competition): L2/3 → L2/3 within a Level

Inhibitory, so an active Column suppresses its competitors. Two rules:

- **Lower Levels: the 8 grid neighbours.** Columns near each other compete.
- **Top Level: every other Column.** Once Columns stop drawing from neighbourhoods, two
  Columns standing for different things have no reason to be adjacent, so competition
  cannot stay spatial either.

Inhibition is weighted **0.90** against excitation's **0.73**, so a strongly active
Column can push its competitors down to near-silence. This is what produces a winner
rather than a tie.

### 4. Inward (within a Column): L4 → L2/3 → L5

The internal circuit, described above.

## How the network runs

Time is discrete ticks. On every tick each Column computes what it *should* be from the
current state, then moves part of the way there — about 12% per tick. Everything updates
at once, so no Column ever sees a half-updated network.

The network is **12 stages deep** (3 stages × 3 Levels, plus the Hub), and each stage
needs time to settle. A stimulus is therefore held for **250 ticks**. The first attempt
used 30, and the signal was still climbing through Level 1 when the run ended.

## Reading the result

For every Column we build a table: its response to each colour, at each position. Then we
ask how much of its variation is explained by **which colour** was shown and how much by
**where** it was.

- A Column scoring **1.0 on colour** responds to yellow wherever yellow appears. It has
  abstracted away position.
- A Column scoring **1.0 on position** responds to one place, whatever colour is there.
- A Column scoring **0 on both** never changed and is telling us nothing.

The number that matters is **the Hub's colour score**, because the Hub is the only place
that receives both *what* and *where*. Everything else is predetermined by the wiring:
the position Space scores 1.0 on position because colour is never routed into it at all.
That is a fact about our wiring diagram, not a discovery about the network.

**The result: the Hub's maximum colour score is 0.000 with the localist colour code, and
0.007 with the population code.** Essentially nothing either way. That is the baseline.
When we add learning it has to beat that number, and if it does not, learning did
nothing.

## What went wrong, and why it is written down

Five problems surfaced. Four are fixed; one is open.

1. **Averaging destroyed the signal.** Columns originally averaged their inputs, so one
   active Column among 18 arrived at 1/18 strength. Nothing reached Level 3. Columns now
   add their inputs instead of averaging them.
2. **The run was too short.** 30 ticks against a 12-stage cascade. Now 250.
3. **Contrast was not the same everywhere.** Corner cells were originally scored against
   only the neighbours they had, which made them look *more* contrastive than middle
   cells — so the same object registered differently depending on where it sat. Now the
   divisor is always 8.
4. **The colour Space was too small for its fan-in.** With a localist code the colour
   Space is 8 Columns wide and the top Level's fan-in is 12, so every top Column drew from all
   8 and they became identical. Switching to the population code (64 Columns) raised
   colour selectivity at that Level from 0.001 to 0.213.
5. **Strength and identity are confused — still open.** Contrast is used as *how hard*
   the Thalamus drives, while colour determines *which* Column it drives. But Columns add
   up their inputs, so they are sensitive to strength — and strength carries position.
   By the top of the colour Space, position explains 99% of the variance. The colour
   pathway has been taken over by position information, and the Hub then receives
   position from both sides.

Problem 5 is why the Hub scores essentially zero on colour. It is architectural rather
than a coding mistake, and it needs a decision rather than a patch.
