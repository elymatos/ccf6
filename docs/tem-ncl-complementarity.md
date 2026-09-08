# Are TEM and NCL complementary, and how do they fit together?

Status: **analysis, no decision taken** · 2026-09-08

Written in response to the question of whether the two source traditions should be
mixed, staged sequentially, or related some other way. Nothing here is settled: a term
belongs in CONTEXT.md once it has been agreed, and a decision belongs in an ADR once it
has been taken. This document is the argument that would precede either.

The two goals it is measured against:

- **(a)** represent cognitive structures that are recurrent and reusable in
  understanding and reasoning, including concept representations;
- **(b)** have a structure that can be trained to recognize, classify and represent new
  events and situations.

---

## Short answer

Yes, genuinely complementary — but not in the way the framing assumes, and the
complementarity is **asymmetric**. They are not two theories of the same thing at
different scales. They are the two halves of a well-known division: **complementary
learning systems**. TEM is the fast, sparse, separating, episodic half. NCL is the slow,
overlapping, converging, semantic half.

Once seen that way, most of the other questions answer themselves, and one problem in
CCF6 becomes visible.

---

## The decisive asymmetry: they push content in opposite directions

This is the sharpest point, and the reason the fit is real rather than rhetorical.

TEM's stated pressure on its codes:

> "Different locations need separate memories → **Distinct, sparse codes** → Avoid
> memory interference."

NCL's stated pressure:

> "If A and B repeatedly co-activate and jointly recruit C, C becomes a node for the
> conjunction AB."

**TEM separates. NCL converges.** These are opposite operations on the same material,
and both are necessary. Separation is what lets the system remember that *this* cat was
on *that* mat on Tuesday without it smearing into every other cat-on-mat. Convergence is
what lets CAT exist at all.

A system with only TEM's pressure remembers episodes and never forms concepts. A system
with only NCL's pressure forms concepts and cannot keep two episodes apart. That is the
classic argument for why brains have both a hippocampus and a neocortex — and it maps
onto the two frameworks almost exactly, including anatomically: TEM is
entorhinal–hippocampal by its own account; Lamb's entire theory is about cortical
columns.

So: complementary, and **not by accident**. They were developed to explain different
memory systems that are themselves complementary.

---

## Two kinds of generalization, and why each goal needs both

The frameworks also implement different generalizations.

- **TEM: structural generalization.** The same relational skeleton reused with new
  content. "This building has the same 3×3 layout, so I can infer the untraveled edge."
  Generalizes across *worlds*.
- **NCL: taxonomic generalization.** Different instances converge on a shared node.
  "These are all cats." Generalizes across *instances*.

**Neither produces the other.** TEM has no pressure to notice that cats resemble each
other — its objective is satisfied by *binding* content to a position, and its inductive
bias actively pushes contents apart to avoid interference. NCL has no path integration,
no composition of relations, and no transfer to a structurally identical new situation;
Lamb's "cognitive map" is topographic adjacency, which CONTEXT.md already records as a
distinct claim from TEM's.

Against the goals:

**(a) recurrent, reusable structures, *including concept representations*.** Two
requirements pulling opposite ways. "Reusable structure" is TEM — schemas,
SOURCE–PATH–GOAL, the relational skeleton. "Concept representations" is NCL —
addressable, nameable, ignitable. Goal (a) alone already requires both halves.

**(b) trained to recognize, classify and represent new events/situations.** Also two.
"Recognize/classify" is featural convergence; NCL's hierarchy is a classifier. But a
*situation* is entities standing in relations, i.e. a graph, and recognizing a **novel**
situation assembled from known parts is structural generalization, not classification. A
CNN will never get there by scaling.

Both goals independently require both frameworks. That is the strongest support the
complementarity claim has.

It also locates the work relative to deep learning. The pair maps onto the two classical
criticisms of connectionism: TEM answers **systematicity** (compositional
generalization — what LLMs get by brute scale and still fail at unevenly), NCL answers
**addressability and grounding** (how a symbol-like handle can exist without being a
symbol). Those are the two gaps worth targeting.

---

## What each gives the other

**TEM → NCL**

1. **A mechanism for relations.** NCL says a relation is "a learned condition on how
   activity is transformed" but never says how one composes or transfers. TEM's
   action-selected transformation is a concrete answer.
2. **Systematicity.** NCL webs cannot distinguish "A left-of B" from "B left-of A"
   without duplicating structure. Factorization handles it natively.
3. **A reason certain structures should appear at all**, plus a diagnostic readout —
   grid, band, border and object-vector tuning — showing whether the structure learned
   anything.
4. **Two explicit timescales.** NCL blurs entrenchment with episodic memory.

**NCL → TEM**

1. **Structured content.** The big one. TEM's `x` is atomic and arbitrary — cat, chair
   and banana are interchangeable tokens. Fine in a toy world, and precisely what stops
   TEM reaching cognition. If `x` is instead a *cardinal over a distributed feature
   web*, it gains internal structure, graded similarity, prototype effects, partial
   matching on novel instances, and cross-modal grounding.
2. **Addressability.** A g-state cannot be called. Cardinals give entry points — needed
   for naming, ignition from a partial cue, and reasoning.
3. **Overlap and reuse.** TEM's memories are separate conjunctions; NCL webs share
   components (BLACK participates in charcoal, night, ink). That is compression, and
   inheritance without copying.
4. **Bidirectionality.** TEM predicts; it does not produce, imagine, or monitor. NCL's
   reciprocal architecture gives imagery, expectation and production monitoring.
5. **An abstraction hierarchy over content:** ANIMAL → MAMMAL → CAT → TOM. TEM has one
   flat level of `x`.

---

## Three real tensions

**1. The learning signal — already decided against TEM.** ADR-0005 rejects gradient
descent; TEM learns its transition weights by backpropagation through time, on the order
of 50,000 updates. CCF6 has therefore *already* adopted NCL's learning account and
rejected TEM's, and that ADR names the consequence as the project's central scientific
question. This reframes the whole discussion: the live issue is not "mix or sequence,"
it is **can a local rule produce the representational structure TEM gets by gradient?**
TEM's *claims about representation* are kept; its *method* is discarded. Coherent, but
it means TEM can only ever be a target here, never an imported mechanism.

**2. Emergence versus recruitment.** TEM insists nothing is templated — cell types are
observed afterward, never supplied. NCL's recruitment is a *discrete structural event*:
a latent column is claimed for a conjunction. Smooth optimization and discrete
recruitment are not obviously the same kind of learning. Unresolved in both literatures.

**3. Is a concept a position or a convergence?** The deepest one. TEM: identity is
position in the transition structure. NCL: identity is what converges on you. For a
situation, TEM is right. For an object, NCL is right.

---

## The conflation currently sitting in CCF6

The practical consequence, and the same error just removed from the glossary.

CONTEXT.md says the Hub is "the only place Cardinal Nodes can form" *and* that "the Hub
carries `p`". Those are two different systems in the source theories. The hub-and-spoke
hub in `initial.txt` §7 is the **ATL** — neocortical, taxonomic, slow, stable, destroyed
in semantic dementia. TEM's `p` is **hippocampal** — fast, sparse, remapping, episodic.

The Hub is currently standing in for both: the semantic convergence site *and* the
episodic binding site. Under the separation/convergence asymmetry above those structures
need **opposite** coding properties — sparse and separating versus overlapping and
converging. They cannot be the same Space.

That is the answer to "how exactly do they fit together": **as two memory systems with
different coding regimes and different learning rates, exchanging content in both
directions.** CCF6 has structural vocabulary for one of them.

---

## What this does to the sequential proposal

It dissolves it, usefully. The relation is not sequential in either direction — it is a
**loop**:

```text
featural convergence yields content units
→ those get bound to structural positions
→ recurring conjunctions get recruited as units in their own right
→ those become content for the next cycle
```

A situation that recurs *becomes* a concept. A concept placed in a situation *becomes*
content. That loop is precisely what goal (a) asks for — structures that are recurrent
and reusable — and neither framework produces it alone.

This contradicts the proposed ordering at the bottom of the stack. TEM-first cannot bind
content that does not yet exist; the first cycle has to be convergence on sensory input.
TEM's papers dodge this by *handing* the model a one-hot `x` from the environment, and
that shortcut is exactly what breaks when concepts are the goal. **TEM-first works for
the toy case and fails precisely where goal (a) lives.**

The NCL summary's §14.5 sketch has the same gap: it begins "TEM-like populations learn
structural and content codes," quietly assuming the content code is already available.

---

## The prediction worth testing

If the synthesis is right, it predicts that **concepts come in at least two kinds**:
those whose identity is featural convergence (RED, CAT, chair) and those whose identity
is relational position (GIVE, BETWEEN, CAUSE, before). Not a spectrum — two different
mechanisms of individuation.

This is independently attested in the linguistics: content words versus relational
markers, and the agrammatism dissociation in the NCL summary §9.4, where relational
markers are selectively lost. If CCF6 built both halves and found relational concepts
living in the structural code while object concepts live in convergence hierarchies,
that would be a real result — and a genuinely *derived* prediction rather than an
assumption imported from either source.

---

## Open questions this leaves

1. Does CCF6 split the Hub into two structures, and what are they called? "Map" is
   ruled out by the Collisions entry in CONTEXT.md.
2. `g`, `x` and `p` are currently mapped onto the position Space, the colour Space and
   the Hub. The position Space is a supplied coordinate, not a path-integrated
   structural code, so that mapping does not hold as written.
3. Whether the two coding regimes — separating and converging — are two structures, two
   parameter settings of one structure, or two learning rates.
4. Whether recruitment (discrete) and the local rule of ADR-0005 can together reach what
   TEM reaches by gradient. ADR-0005 already names this as the central question; the
   analysis above says it is also the seam between the two traditions.
