# CCF architecture: two abstractors and a binder

Status: **proposed architecture, open for discussion** · 2026-09-08

Derived from [`tem-ncl-complementarity.md`](tem-ncl-complementarity.md), which argues
that the two source traditions are complementary halves rather than rival accounts. That
document establishes *why*. This one proposes *what to build*.

This is an architecture, not a specification. It fixes the structures, what each is
responsible for, what each is forbidden to do, and how they exchange information. It
does not fix representations, parameters, update equations, or an order of work. Names
proposed here are candidates for discussion, not settled terms.

---

## 1. What the architecture has to deliver

Two goals, stated by the project owner:

- **(a)** represent cognitive structures that are recurrent and reusable in
  understanding and reasoning, including concept representations;
- **(b)** be trainable to recognize, classify and represent new events and situations.

Both are deliberately in the neighbourhood of what deep learning and language models do,
approached by other means and at smaller scale. That neighbourhood matters, because it
tells us which failures are interesting. A system that classifies well and composes
badly has reproduced a known result. The interesting target is the pair.

### Each goal decomposes into two different requirements

This is the first argument for a two-part architecture, and it comes from the goals
themselves rather than from either source tradition.

**Goal (a) splits.** "Recurrent and reusable structure" is a relational skeleton that
survives a change of content — the same arrangement recognized in new material.
"Concept representations" is something else entirely: an addressable, nameable,
ignitable unit that stands for a class of things. A skeleton is reusable because it is
*empty*. A concept is useful because it is *full*. One mechanism cannot maximize both.

**Goal (b) splits.** "Recognize and classify" is abstraction over instances: many
presentations converge on one response. "Represent new events and situations" is
composition: entities standing in relations, assembled in a configuration never seen
before. Classification discards the arrangement; situation representation *is* the
arrangement.

So before consulting either source theory, both goals have already asked for two
different things. That is the shape the architecture has to take.

---

## 2. Why one system cannot do it

Four arguments, from strongest to weakest.

### 2.1 The pressures on the code are opposite

To keep two episodes from blurring, their codes must be **separated** — sparse and
overlapping as little as possible. To form a category from many instances, their codes
must be **converged** — many inputs driving one shared response.

These are not two settings of one dial that could be tuned to a happy middle. They are
contradictory demands on the same population. A code sparse enough to keep every
Tuesday-cat-on-mat distinct from every Wednesday-cat-on-mat is, by construction, a code
in which no CAT response can form. A code in which all cats converge is one in which two
cat episodes are the same memory.

Any system that must both remember particulars and abstract generalities therefore needs
two populations under different pressure. This is the standing argument for why brains
separate a fast, sparse, binding structure from a slow, overlapping, abstracting one,
and it applies to CCF regardless of which literature it is drawn from.

### 2.2 New learning would destroy old structure

A single converging system that also has to store new episodes must adjust the same
weights that hold its categories. Each new particular perturbs the abstraction it is
supposed to be an instance of. The abstraction degrades in proportion to how much
specific experience the system has, which is exactly backwards.

Splitting the store lets particulars be written fast and cheap somewhere that does not
own the categories, and lets abstraction proceed slowly over many particulars. The cost
is that the two must be kept in correspondence, which is what §4 is about.

### 2.3 The two generalizations are different operations

- **Structural generalization:** the same relational skeleton reused with different
  content. Enter an unfamiliar building, recognize the layout, infer where the unvisited
  room is. Generalizes across *situations*.
- **Taxonomic generalization:** many different instances converge on a shared response.
  Generalizes across *members*.

Neither produces the other, and this is worth being precise about because it is easy to
assume that enough of one becomes the other.

Taxonomic machinery cannot yield structural generalization. A convergence hierarchy
abstracts over things that co-occur. It has no representation of *the same relation
holding elsewhere*, no composition of relations, and therefore no way to transfer an
arrangement to new material. Adding levels deepens the abstraction; it does not make it
relational.

Structural machinery cannot yield taxonomic generalization either, and the reason is
sharper. A structural system's pressure on content is to keep contents **distinct**, so
that what was stored at one position does not contaminate another. Nothing in it rewards
noticing that two contents resemble each other. Its generalization is transfer of the
*arrangement*, never abstraction over the *material*.

### 2.4 They fail in complementary places, and the failures are the known ones

Each tradition has a characteristic poverty, and the other tradition is a direct answer
to it.

A purely structural account treats content as arbitrary and atomic — the item at a
position is a token, and any token would do. That assumption is what makes the
factorization work, and it is also what stops the account from reaching cognition: with
atomic content there is no similarity, no graded membership, no prototype, no partial
match on something never seen, and no grounding in more than one modality.

A purely convergent account has no mechanism for composition. It can represent that A
and B are both present. It cannot represent that A stands in a particular relation to B
without duplicating structure for each ordering, which does not scale and does not
transfer.

These are the two classical criticisms of connectionist accounts — **systematicity** and
**addressable grounding** — and the architecture below is a bet that they are answered by
different structures rather than by one better one.

---

## 3. The architecture

Three structures. Two of them abstract slowly over different data; the third binds
quickly and separates.

```text
                      World
                        │
                   (encoding)
                        │
                        ▼
   ┌───────────────────────────────────────────┐
   │  WEB — slow, converging over co-occurrence│
   │  features → conjunctions → categories     │
   │  access points: Cardinal Nodes            │
   └───────────────┬───────────────────────────┘
                   │ content            ▲
                   ▼                    │ reactivation
   ┌───────────────────────────┐        │
   │  INDEX — fast, separating │◄───────┘
   │  binds content to position│
   └───────┬───────────▲───────┘
           │           │
   position│           │retrieval
           ▼           │
   ┌───────────────────┴───────────────────────┐
   │  SCHEMA — slow, converging over transitions│
   │  state updated by Relations; reusable      │
   └────────────────────────────────────────────┘

   RECRUITMENT: a recurring INDEX entry is promoted
   into the WEB (as a concept) or into the SCHEMA
   (as reusable structure).
```

### 3.1 The Web — what things are

Slow. Overlapping. Converges over **co-occurrence**.

The Web is a hierarchy of convergence: sensory features feed conjunctions, conjunctions
feed categories, and the whole organization is entered at any level. Its characteristic
operation is that many different inputs come to drive one shared response, which is what
makes a category exist at all.

Properties the architecture requires of it:

- **Graded, not criterial.** A category's response follows weighted convergence, so
  typicality, partial match and fuzzy boundaries are consequences of the mechanism
  rather than features added to it.
- **Overlapping.** A component participates in many categories. BLACK belongs to
  charcoal, night, ink and cats. Nothing is copied into each; membership is shared
  connectivity. This is where the architecture's compression lives, and it is how a
  subordinate inherits from a superordinate without a copy operation.
- **Bidirectional.** A category, once active, reactivates the features that usually
  accompany it. This single property is doing a great deal of work: it supplies
  expectation, imagery, pattern completion from a partial cue, and production.
- **Addressable.** Somewhere in the hierarchy are convergence points compact enough to
  be pointed at, activated, and lesioned. These are the **Cardinal Nodes**. A Cardinal is
  not where the concept is stored — the concept is the whole reachable web — it is where
  the concept can be *entered*.

The Web is the architecture's answer to "classify" in goal (b) and to "concept" in goal (a).

### 3.2 The Schema — how things change

Slow. Converges over **transitions**.

The Schema holds a state that is updated by a **Relation**, and whose value is that the
same relation transforms it the same way wherever it applies. It is the reusable
skeleton: what stays constant when the material changes.

Properties the architecture requires:

- **Separation of states.** Two distinct positions must have distinct states, or nothing
  bound at one can be retrieved without contaminating the other.
- **Path consistency.** Reaching one position by two different routes must produce the
  same state, or a memory stored there becomes unreachable from a new direction.
- **Composition.** A sequence of Relations must arrive where the structure implies,
  including along routes never taken. This is what buys inference: if composition holds,
  the system can arrive at a position it has never approached this way and still query
  what is there.
- **Content-blindness.** The Schema must not know what occupies a position. The moment it
  does, the skeleton stops transferring, which is the only thing it was for.

Non-commutativity has to be learnable, not assumed away. Two spatial translations
commute; *father-of* then *brother-of* need not equal *brother-of* then *father-of*. The
Schema learns the composition rules that actually hold, rather than inheriting the
algebra of physical space.

The Schema is the architecture's answer to "reusable structure" in goal (a) and to
"new situations" in goal (b).

### 3.3 The Index — what happened where

Fast. Sparse. Separates.

The Index binds a content unit to a Schema position: *this thing, at this place in this
arrangement*. It is written quickly, it is sparse enough that entries do not interfere,
and it supports completion — a partial cue settles onto a stored entry and reinstates the
rest.

Properties the architecture requires:

- **Fast write.** An entry after one exposure. Nothing that requires many repetitions can
  serve as episodic memory.
- **Sparse and separating.** Two similar episodes must not merge. This is the pressure
  that is the exact opposite of the Web's, and it is why the Index is a separate
  structure.
- **Completion from either side.** Given a position, what was there. Given a content,
  where it was. Both directions are needed: the first is retrieval, the second is
  relocalization when the Schema's estimate has drifted.
- **No abstraction.** The Index must not generalize. An index that starts merging similar
  entries has become a slow Web with the wrong parameters.

The Index is not the memory. It is the binding that lets a Schema position and a Web
content be recovered together.

### 3.4 Recruitment — the operation that closes the loop

This is the architecture's central mechanism, and the one that neither source tradition
supplies on its own.

**A binding that keeps recurring is promoted into a structure that abstracts.** An Index
entry that is written again and again is no longer a particular; it is a regularity, and
it should be moved out of the fast store into a slow one.

Promotion has two destinations, and which one applies depends on what recurred:

- A recurring **conjunction of content** — the same things appearing together — is
  promoted into the **Web** as a new convergence point. A situation that keeps happening
  becomes a concept. This is how kitchens, faces, and four-lap cycles become things.
- A recurring **sequence of transitions** — the same relational arrangement holding over
  different material — is promoted into the **Schema** as reusable structure. This is how
  a schema is *learned* rather than preloaded, which matters: an architecture that ships
  with a library of image schemas has assumed the thing it should explain.

The loop then closes, because a promoted Web unit is content, and content can be bound
at a Schema position:

```text
convergence yields content units
  → content is bound at structural positions
    → recurring bindings are promoted
      → promotions become content units, or become structure
        → …
```

That loop is the direct answer to goal (a). A structure is "recurrent and reusable"
precisely by having been recruited as a unit, and a system that can do this repeatedly
climbs from features to objects to events to schemas without a different mechanism at
each step.

It also settles a question the source traditions leave ambiguous. Neither is "first."
The bottom of the stack is convergence, because a binder cannot bind content that does
not yet exist; but above that first cycle the two alternate indefinitely.

---

## 4. Mapping the borrowed vocabulary

The population-level terms borrowed from the structural tradition describe activity
across many units. They are observer-level handles, not fields stored anywhere. Against
this architecture they land as:

| Borrowed term | Where it lives here |
| --- | --- |
| **Structural code** | The Schema's state: position in a relational arrangement, updated by Relations. |
| **Content code** | A Cardinal Node's activation in the Web — *not* a raw sensory vector. |
| **Conjunctive code** | An Index entry: one content bound at one Schema position. |
| **Associative memory** | The Index's connectivity, together with its completion dynamics. |

The second row is the substantive change, and it is the point where this architecture
departs from the structural tradition rather than merely implementing it. In that
tradition the content code is an arbitrary token supplied by the environment — the whole
factorization argument depends on content being interchangeable. Here the content code is
the apex of a convergence hierarchy, which means it arrives with internal structure,
graded similarity, prototype effects, partial activation on novel material, and grounding
across several modalities.

That is not a detail. It is what lets the architecture bind *concepts* into arrangements
rather than binding tokens, and it is the difference between a model that navigates a
toy world and one that could represent a situation.

---

## 5. Information flow

Four paths the architecture must support. They use the same structures in different
directions.

**Recognition.** Sensory activation ascends the Web; convergence sharpens under
competition; a Cardinal becomes active. If a Schema position is also current, an Index
entry is written or completed. Recognition is not finished when the Cardinal fires — the
Cardinal reactivates expected features downward, and the settled state is the recognition.

**Situation representation.** Relations — whether supplied by geometry or produced by
movement — advance the Schema state. Each sampled content is bound at the position
current when it was sampled. A situation is not a list of contents; it is a set of Index
entries over one Schema traversal.

**Inference.** Compose Relations to arrive at a position never approached this way. Query
the Index at that position. If composition holds, an unvisited part of an arrangement can
be reported without having been observed. This is the architecture's zero-shot claim and
its clearest falsifier.

**Production and imagery.** Activate a Cardinal without sensory input. It reactivates its
features downward and can supply content to be bound at a Schema position. The same
machinery that recognizes runs backwards, which is why the Web must be bidirectional
rather than a feedforward classifier.

---

## 6. What each structure is forbidden to do

Boundary conditions. These are the claims that make the architecture falsifiable, since
each one predicts a specific failure if violated.

| Structure | Must not |
| --- | --- |
| **Web** | Store particulars. Hold the arrangement of a situation. Contain a symbol, definition or property list. |
| **Schema** | Know what occupies a position. Hold content. Ship with preloaded structures. |
| **Index** | Generalize or merge similar entries. Persist indefinitely without promotion or decay. |
| **Cardinal Node** | Contain the concept. Be assumed unique. Be a different kind of unit from any other. |
| **Encoding boundary** | Carry state across samples, or make any decision that belongs to a learning structure. |

The last row is worth stating explicitly. The conversion of a world signal into
activation is a **transduction** decision and nothing else. If it acquires memory of the
trajectory, it has quietly become the Schema, and the ability to change the encoding
independently of everything downstream is lost.

---

## 7. Trying answers to the open questions

The predecessor document left four open. Positions, not decisions.

### 7.1 Names

The framework already uses **map** for nothing, deliberately, because it names two
incompatible things across the traditions. New words are needed rather than a winner
chosen.

| Structure | Proposed | Alternatives | Note |
| --- | --- | --- | --- |
| Slow, converging over co-occurrence | **Web** | Fabric, Mesh | Already the structural tradition's word for a distributed subnetwork realizing a concept; carries the right sense. |
| Slow, converging over transitions | **Schema** | Armature, Scaffold, Chart, Frame | Recommended with a recorded collision — see below. |
| Fast, sparse, binding | **Index** | Trace, Register, Ledger | Has precedent for a pointer into a distributed pattern, which is exactly the role. |

**Schema** is the recommendation and the one to argue about. In its favour: it is the
ordinary term for a reusable relational structure, and goal (a) is a description of one.
Against: it carries symbolic-AI and preloaded-primitive baggage, and one of the source
traditions explicitly warns that such structures must not be foundational objects. That
warning is a reason to *record the collision*, not to avoid the word — the architecture's
position is that a Schema is a recruitment product, never a preloaded primitive, and
saying so in the glossary is stronger than dodging the term.

**Frame** should probably be rejected outright: it collides with two large existing
literatures at once and would import more than it names.

### 7.2 Where the population-level codes attach

Answered in §4. The substantive commitment is that the content code is a Cardinal's
activation rather than a sensory vector. A structural code supplied by an encoder — a
coordinate handed over rather than integrated over a trajectory — is not a structural
code at all, and it passes the path-consistency test vacuously, which means the test
cannot discriminate. Whatever carries the structural code must be *updated by Relations*
or it is not doing the job.

### 7.3 Two structures, two settings, or two rates?

**Two structures.** The argument in §2.1 is that the pressures are contradictory rather
than merely different, so a single population under a compromise setting fails both
demands rather than partly satisfying each. Sparsity and learning rate then differ
between the structures *as a consequence* of their roles, not as the definition of them.

A weaker version is worth keeping available for testing: one population with two rates
and a sparsity schedule. If that turns out to work, the architecture is wrong in an
interesting way, and it is cheap to find out.

### 7.4 Recruitment versus gradient

The framework's standing commitment is to local learning rules. The structural tradition
reaches its representations by global optimization over many environments. The gap
between those is the project's central question, and the architecture takes a position on
what closes it.

**Recruitment is the local system's substitute for credit assignment.** A global gradient
assigns credit by propagating error backwards to every weight that contributed.
Recruitment assigns credit *structurally*: the unit that became active for a conjunction
is the unit that owns it, and the promotion is the assignment. No error has to travel.

Whether that is enough is genuinely unknown, and the honest formulation is a comparison
rather than a claim:

> Can convergence, competition and recruitment under local rules produce structural
> generalization — transfer of an arrangement to new material, and inference along an
> untraveled route — at all, and how far short of the optimized version does it fall?

A negative result is ambiguous between "the rule is inadequate" and "the task needs more
than the architecture supplies", so any test needs a measured baseline from unlearned
connectivity to be interpretable at all.

---

## 8. Predictions

If the architecture is right, these should hold. They are listed because they are the
places it can be caught being wrong.

1. **Two kinds of concept.** Concepts should divide by mechanism of individuation:
   those identified by featural convergence (RED, CAT, chair) and those identified by
   relational position (GIVE, BETWEEN, CAUSE, before). Not a spectrum — two mechanisms.
   This is independently attested in the linguistic distinction between content words and
   relational markers, and in the selective loss of relational markers under damage.
   Finding relational concepts living in the Schema and object concepts in the Web would
   be a derived result rather than an imported assumption.
2. **Damage dissociates.** Removing an access point should impair naming, cross-modal
   access and ignition while leaving feature-level knowledge reachable by other routes.
   Damaging the Index should impair particulars while leaving categories intact.
   Damaging the Schema should impair novel arrangements while leaving classification
   intact.
3. **Inference precedes exposure.** Composition should let the system report an
   unvisited part of a known arrangement. This is the clearest single falsifier.
4. **Promotion is visible.** A unit recruited from a recurring binding should be
   identifiable as such, and should thereafter behave as content — bindable at a
   position, not merely retrievable from one.
5. **Structural transfer.** Performance in a new situation sharing an old arrangement
   should exceed performance in one that does not, and the gap should widen with the
   number of arrangements experienced.

---

## 9. What the specification must settle

Points to carry forward. The architecture deliberately leaves all of these open.

**Structures and representations**
1. Whether the Web, Schema and Index are built from one kind of unit or several.
2. What a Schema position *is* as activity, and how a Relation is applied to it.
3. Sparsity and capacity for the Index, and what happens when it is full.
4. Whether the Web's hierarchy is fixed in depth or grows by recruitment.

**Learning**
5. The local rule, and what makes a co-activation "successful" enough to strengthen.
6. What triggers recruitment: a recurrence count, a stability criterion, a competition
   outcome, or a combination.
7. How promotion decides between the Web and the Schema.
8. Whether Index entries decay, and whether promotion consumes or copies them.
9. How competition is itself learned, which both traditions leave incomplete.

**Interfaces**
10. How Relations are supplied — given by geometry before enacted by movement — and how
    the two are kept measurably comparable.
11. How the Schema's state is corrected when it drifts, and how retrieval evidence and
    transition evidence are combined.
12. What the encoding boundary produces, and how a change there is shown to leave
    everything downstream untouched.

**Measurement**
13. The unlearned baseline each learning claim must beat.
14. Readouts that distinguish the two generalizations, so structural transfer is not
    reported when only taxonomic abstraction occurred.
15. Lesion protocol for prediction 2.
16. The smallest experiment that discriminates this architecture from a single-system
    alternative — which, given §7.3, is the first thing worth building.
