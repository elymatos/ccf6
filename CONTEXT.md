# CCF6 — Domain glossary

The vocabulary of the Connectionist Cognitive Framework, version 6. This file is a
glossary and nothing else: no implementation detail, no specification, no notes.
A term belongs here once it has been settled in discussion, not before.

CCF6 draws on two independent research traditions, and they are **not translated into
each other**. Each keeps its own words in its own layer. Where they collide, the
collision is recorded rather than resolved by picking a winner. See *Collisions*.

---

## Structural vocabulary

These are CCF6's own terms. They name things that exist in the network and can be
pointed at, drawn, and lesioned.

**Column** — The primitive element of the network. A stateful unit holding three
private activations, one per Layer. Its function comes from what it connects to, not
from anything stored inside it. A Column carries no label and no semantic type.
*Avoid: node, neuron, cell, unit.*

**Layer** — One of the three internal compartments of a Column: **L4** (input), **L2/3**
(processing and competition), **L5** (output). Layers are private: no Column can read
another Column's Layers except through the connections declared between them.
*Avoid: level, stage, lamina used loosely.*

**Level** — One hierarchical stage within an Area. A Level is a Grid of Columns. Levels
are ordered: lower Levels are nearer the sensory boundary, higher Levels further from
it. *Avoid: layer.*

**Grid** — The two-dimensional arrangement of Columns making up one Level. Grid
position is mechanical, not decorative: lateral competition is defined over grid
neighbourhood. *Avoid: map, array.*

**Area** — A stack of Levels forming one functional specialization. The first
experiment declares three: a position Area, a colour Area, and a Hub.
*Avoid: module, region, network.*

**Convergence Node** — A Column at the top Level of an Area, where that Area's activity
converges. It is modality-specific: it sees only what its own Area carries.
*Avoid: cardinal node, apex, output unit.*

**Cardinal Node** — A Column whose inbound connectivity spans three or more distinct
Areas and whose activation is stable across varied input contexts. A Cardinal Node is
an **entry point** to the set of Columns reachable through it, not a container of the
concept — the concept is that whole set. Cardinality is multimodal by definition, so a
Cardinal Node cannot exist inside a single Area.
*Avoid: grandmother cell, concept node, Convergence Node.*

**Hub** — An Area whose input is the output of several other Areas, and the only place
Cardinal Nodes can form. *Avoid: association area, integration layer.*

**Thalamus** — The structure between World and Areas. It converts one world signal into
activation across many Columns of Level 1, and it is the sole site of the encoding
decision. *Avoid: input layer, encoder used without qualification.*

**World** — The external arrangement CCF6 is shown. It is not part of the network and
holds no Columns. *Avoid: environment, input, stimulus.*

**Object** — A configuration of coloured cells in the World, defined by the relative
arrangement of its parts. The same arrangement at a different World position is the
same Object. *Avoid: shape, pattern, item.*

**Ego** — The position in the World from which sampling occurs. Sampling is egocentric;
what gets stored is not. *Avoid: agent, observer, viewpoint.*

**Relation** — The offset between two sampled World positions. A Relation may be
**given** (two positions sampled together, geometry supplies the offset) or **enacted**
(Ego moves, the movement supplies the offset). Both yield the same thing.
*Avoid: action, movement, edge.*

**Convergence Node** and **Cardinal Node** are both Columns. Nothing about a Column's
storage or behaviour differs; only its connectivity does.

---

## Population vocabulary

Borrowed from TEM. These name **descriptions of activity across many Columns**, never
a field stored inside one. They are observer-level handles.

**g — Structural code** — Distributed activity representing position in a relational
structure, updated by Relations. *Avoid: coordinate, location value.*

**x — Content code** — Distributed activity representing what is currently observed.
*Avoid: feature vector, symbol.*

**p — Conjunctive code** — Distributed activity binding a Content code to a Structural
code: this content, at this structural position. *Avoid: binding tuple, pair.*

**M — Associative memory** — Fast-changing connectivity supporting storage, retrieval,
and pattern completion from a partial cue. *Avoid: database, store.*

In CCF6 the position Area carries `g`, the colour Area carries `x`, and the Hub carries
`p`. This is a mapping between the two vocabularies, not an identity: `g`, `x` and `p`
remain descriptions of population activity, while Area, Column and Cardinal Node remain
structure.

---

## Collisions

Recorded, not resolved.

**map** — In the neurocognitive-linguistics tradition, a topographic property of cortex:
nearby locations have related functions. In TEM, a latent transition structure. These
are different claims about different things. CCF6 uses **Grid** for the first sense and
**Structural code** for the second, and uses "map" for neither.

**node** — In TEM, a vertex of the World graph. In CCF6, a Column. The World's
arrangement and the network's Columns are different populations and must not share a
word. CCF6 says **Column** for the network and **World position** for the World.

**conjunction** — TEM's `p` is a conjunction of structure and content. The
neurocognitive-linguistics tradition describes recruitment of a higher node for a
conjunction of co-active inputs. Whether these are the same mechanism arriving from two
directions is an open question, and CCF6 does not assume they are.

**layer / level** — Resolved rather than open: **Layer** is a compartment inside a
Column, **Level** is a hierarchical stage inside an Area. See both entries above.
