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

**Level** — One hierarchical stage within a Space. A Level is a Grid of Columns. Levels
are ordered: lower Levels are nearer the sensory boundary, higher Levels further from
it. *Avoid: layer.*

**Grid** — The two-dimensional arrangement of Columns making up one Level. Grid
position is mechanical, not decorative: lateral competition is defined over grid
neighbourhood. *Avoid: map, array.*

**Space** — A stack of Levels over one conceptual dimension: position, colour,
temperature. The dimension is what the Space's Columns can vary along, and it is the
Space's whole functional specialization — a Space does one job because it is a code for
one thing. Every Space declares which **Cortical Area** it sits in and which
**Modality** its content arrives through. A Space belongs to the **Web**; the Schema and
the Index are not Spaces.
*Avoid: area, module, region, network, dimension used alone.*

**Modality** — The channel through which a Space's content reaches the network:
**visual**, **auditory**, **tactile**, **motor**, **affective**. A Space has exactly one
Modality, or none — a Hub is fed by other Spaces rather than by the World, so no channel
is its own. Two Spaces sharing a Modality are still two Spaces: position and colour are
both visual and are not interchangeable.
*Avoid: sense, channel, feature type.*

**Cortical Area** — Where a Space sits: **frontal**, **parietal**, **temporal**. This is
an anatomical claim and nothing else — it says which region of cortex a Space is
proposed to correspond to, and never which job it does. Two Spaces may share a Cortical
Area. The word "area" is used in CCF6 in this sense only, always with its qualifier.
*Avoid: area used bare, lobe, brain region.*

**Convergence Node** — A Column at the top Level of a Space, where that Space's activity
converges. It is Space-specific: it sees only what its own Space carries, and therefore
only its own dimension.
*Avoid: cardinal node, apex, output unit.*

**Cardinal Node** — A Column whose inbound connectivity spans three or more distinct
Spaces and whose activation is stable across varied input contexts. A Cardinal Node is
an **entry point** to the set of Columns reachable through it, not a container of the
concept — the concept is that whole set. Cardinality is cross-Space by definition, so a
Cardinal Node cannot exist inside a single Space. Whether it must also be cross-Modality
is open; see *Collisions*.
*Avoid: grandmother cell, concept node, Convergence Node.*

**Hub** — A Space whose input is the output of several other Spaces, and the only place
Cardinal Nodes can form. Its dimension is not supplied by the World: it is whatever the
conjunction of its source Spaces constitutes. A Hub carries no Modality. A Web has at
most one, and it is where the Web's Spaces converge.
*Avoid: association area, integration layer, convergence Space.*

**Web** — The organization of Spaces that converges over **co-occurrence**. Features
drive conjunctions, conjunctions drive categories, and many different inputs come to
drive one shared response, which is what makes a category exist at all. A Web organizes
Spaces rather than replacing them, so Space, Modality, Cortical Area, Convergence Node,
Cardinal Node and Hub all keep their meanings inside it. The Web is slow and
overlapping. What it cannot do is keep two similar things apart.
*Avoid: hierarchy, semantic network, taxonomy.*

**Schema** — The structure that converges over **transitions**. It is a state advanced
by a Relation and nothing else, blind to what occupies a position, which is what lets one
skeleton transfer to new material. A Schema is not a Space. It is not a code for a
conceptual dimension, the Thalamus does not drive it, and it holds no Levels.
*Avoid: map, cognitive map, frame, grid.* See *Collisions*.

**Index** — The structure that **binds** a Content code to a Schema state, meaning *this
thing, here*, and completes the pair from either half. It is fast, sparse and separating,
written in one exposure, and it holds bindings rather than a hierarchy of Levels. Its
pressure runs opposite to the Web's. The Web must merge similar things; the Index must
keep them apart. *Avoid: memory, store, lookup table, Hub.* See *Collisions*.

**Presentation** — A figure as the sequence of stops that shows it. An arrangement is
only visible across more than one sample, so a Presentation, not a signal, is what the
network is shown. *Avoid: trial, stimulus, episode.*

**Stop** — One sample within a Presentation: a World position Ego looked from, what was
there, and the Relation by which it was reached. The first Stop has no Relation.
*Avoid: step, tick, fixation.*

**Thalamus** — The structure between World and Spaces. It converts one world signal into
activation across many Columns of Level 1, and it is the sole site of the encoding
decision. *Avoid: input layer, encoder used without qualification.*

**World** — The external arrangement CCF6 is shown. It is not part of the network and
holds no Columns. *Avoid: environment, input, stimulus.*

**Object** — A configuration of coloured cells in the World, defined by the relative
arrangement of its parts. The same arrangement at a different World position is the
same Object. *Avoid: shape, pattern, item.*

**Part** — One cell of an Object, held as an offset from the Object's own origin and a
colour. Parts carry no World coordinates, which is what makes an Object the same Object
wherever it is placed. **Figure** is the informal word for an Object being shown and
carries no separate meaning. *Avoid: element, component, feature.*

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

In CCF6 the **Schema**'s state carries `g`, the **Web**'s content carries `x`, and the
**Index** carries `p` and is the site of `M`. This maps the two vocabularies onto each
other without making them identical. `g`, `x` and `p` remain descriptions of population
activity, while Space, Column and Cardinal Node remain structure.

The mapping was once *position Space → g, colour Space → x, Hub → p*. It changed when the
Hub's two jobs were separated. A structural code must be **updated by Relations** or it
is not one, so a coordinate supplied by an encoder cannot carry `g` however position-like
it looks. And a conjunctive code must **separate** where the Hub's job is to **merge**.
The Hub keeps the convergence job; the Index takes the binding job.

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
Column, **Level** is a hierarchical stage inside a Space. See both entries above.

**area** — In neuroanatomy, a region of cortex. In CCF6 before this glossary was split,
"Area" also carried the functional load now held by **Space** and the channel load now
held by **Modality** — one word making three claims at once. Resolved rather than open:
"area" appears only as **Cortical Area**, always qualified, and never on its own.

**schema** — In symbolic AI and in parts of cognitive psychology, a relational template
supplied to the system in advance. One of CCF6's source traditions warns explicitly that
such structures must not be foundational objects. In CCF6 a Schema is a **recruitment
product**: whatever relational structure it holds was built from Relations the system was
shown, never installed. The word is kept because it is the ordinary term for a reusable
relational structure, and the collision is recorded rather than dodged.

**index** — In databases, a lookup structure over records. In CCF6, the structure that
binds a Content code to a Schema state and completes the pair from either half. Both
senses mean *a pointer into something larger*, which is why the word was chosen. A CCF6
Index stores bindings rather than addresses, and exposure writes it rather than
maintenance. It is also not TEM's `M`. `M` describes the connectivity at population
level; the Index is the structure holding it.

**web** — In the neurocognitive-linguistics tradition, the distributed subnetwork that
realizes one concept, roughly the set of Columns a Cardinal Node is an entry point to. In
CCF6, the whole slow co-occurrence-converging organization of Spaces, containing many
such subnetworks. Same word, two scales. CCF6 says **Web** for the organization only, and
*the Columns reachable through a Cardinal Node* for the other sense.

**learning** — Open, and mostly terminological. The foundation is described as having
**no learning**, meaning nothing in the Web or the Schema changes, nothing is recruited
and nothing is promoted. The Index nonetheless writes a binding on every exposure. Both
statements are true, because the word is doing two jobs: *slow structural change*, and
*any change to connectivity at all*. Whether the Index's one-shot write counts as
learning is not settled here.

**cardinal / multimodal** — Open. A Cardinal Node is defined by spanning three or more
**Spaces**. It was previously said to be multimodal by definition, but the split shows
those are not the same requirement: position and colour are both **visual**, so a
Column spanning them is cross-Space and single-Modality. Whether cardinality requires
crossing Modalities as well as Spaces — and so whether the first experiment can produce
a Cardinal Node at all — is not settled here.
