# CCF6 NCL-only architecture

Status: **accepted target architecture** · 2026-09-09

This architecture implements only the commitments summarized in [`neurocognitive_linguistics_summary.md`](neurocognitive_linguistics_summary.md). The normative mechanics and acceptance criteria are in [`specification.md`](specification.md). The runtime and accepted milestone artifacts conform to that contract; the scientific milestone itself records a negative verdict.

## 1. Scientific commitments

The system preserves these Neurocognitive Linguistics premises:

1. linguistic and conceptual structure is relational network organization;
2. a local unit has no stored symbol and gets its function from connectivity;
3. learned functions are distributed, overlapping Functional Webs;
4. activation is graded, recurrent, competitive, and bidirectional;
5. learning is local, experience-dependent, and confirmed by successful activity;
6. compact convergence populations may provide addressability, but their uniqueness and necessity must be tested;
7. sensory, linguistic, conceptual, and motor Populations can be functionally distinct while belonging to one connected Network.

## 2. Deep runtime module

The runtime presents one primary interface:

```text
Network
  reset presentation activity
  present sensory Samples
  settle or report failure
  apply a diffuse Success Signal
  freeze or enable learning
  observe activity and connectivity
  stimulate or lesion selected Outputs
```

The implementation behind this interface contains ordinary Columns, sparse directed connections, local competition, recurrence, and plasticity. It contains no separate symbolic processor, relation engine, episodic binder, privileged concept store, Functional Web registry, or cardinal flag.

Target Basin estimation, Functional Web detection, Cardinal Node classification, controls, and statistical aggregation sit outside this seam as experiment-observer operations.

## 3. Column abstraction

A Column is the smallest addressable processing population. It has three functional compartments:

- **Input** integrates sensory and ascending activity;
- **Integration** combines Input, recurrent state, descending context, and inhibition;
- **Output** applies a graded threshold response and broadcasts activity.

Anatomical layer names explain the inspiration for these compartments but do not define their behavior. Resting activity is zero. Each Column also has a locally adapted threshold and evidence of entrenchment; directional connections hold their own weights and Eligibility traces.

A Column does not contain:

- a concept name or definition;
- a symbolic feature list;
- a construction-specific program;
- authored Functional Web membership;
- Cardinal Candidate or Cardinal Node status.

## 4. Populations and connectivity

A Population groups Columns by a shared source of evidence. Its declaration may state sensory provenance or broad wiring role, but not learned semantic content. Functional interpretation comes from response, connectivity, transfer, perturbation, and Lesion evidence.

Connections are sparse and directed. Connected Populations use reciprocal endpoint topology, but ascending and descending directions have independent weights and Eligibility. This allows recognition and reactivation to develop differently without losing reciprocal access.

The first milestone uses abundant fixed latent topology: learning changes existing strengths but does not grow or redirect connections. Lateral inhibition is local, fixed, and bounded. Several association Populations and convergence routes are permitted; no central Hub is required.

## 5. Functional Webs and cardinals

A Functional Web is an observed coalition, not a runtime container. Its membership requires converging evidence from reliable co-activation, reciprocal effective connectivity, partial-cue completion, independent Entry Routes, and causal perturbation. Webs may overlap through reusable feature and intermediate Columns.

Cardinality is an observer-level lifecycle:

```text
Available Column
  → Recruited Column
  → Cardinal Candidate
  → Cardinal Node classification
```

Recruitment requires successful participation across distinct Presentations. A candidate additionally requires convergence from independent Entry Routes and causal reactivation beyond matched controls. Cardinal Node classification additionally requires predicted stimulation, Lesion, and redundancy behavior across seeds.

No lifecycle stage turns a Column into a different processor type.

## 6. Learning

Co-active endpoints create temporary local Eligibility. Eligibility alone does not change durable connectivity. A diffuse Success Signal confirms eligible connections after a Presentation settles without identifying a category, Column, or connection.

The first milestone uses:

- success-gated strengthening of existing excitatory routes;
- independent learning in ascending and descending directions;
- local incoming-weight normalization;
- Presentation-level entrenchment;
- local homeostatic threshold adaptation;
- fixed inhibitory connectivity.

It deliberately excludes connection growth, inhibitory learning, negative Success Signals, and claims of a complete biological learning account.

## 7. First milestone topology

The minimum topology is:

```text
visual-property Populations
        ↕
visual-association Population
        ↕
cross-domain association Population
        ↕
phonological-association Population
        ↕
auditory-feature Population
```

Every Population uses the same Column mechanics. The topology supplies possible routes, not category identities.

## 8. First milestone experiment

Four synthetic categories are grounded in overlapping visual properties and paired with three-segment pseudowords assembled from shared auditory features. Acquisition, basin-estimation, and final held-out instances are disjoint.

Correct full pairings receive a diffuse positive Success Signal. Balanced mismatches receive none. Evaluation freezes all learning and tests:

- held-out graded category convergence;
- visual-only and pseudoword-only Entry Routes;
- partial-cue movement into the correct Target Basin;
- ordered phonological reactivation;
- reversed, permuted, repeated, and competing pseudoword controls;
- Functional Web overlap;
- candidate stimulation;
- individual and group Lesions;
- redundant recovery;
- matched untrained, shuffled-pairing, and perturbation controls.

At least 20 paired seeds determine the result. Seed-level effects, deterministic bootstrap intervals, direction counts, and failures are mandatory. Completion and reactivation must improve while held-out separation remains within a 5% relative non-inferiority margin. The accepted run preserves a failed milestone verdict: completion, reactivation, localization, overlap, and cardinal intervention criteria fail, while held-out separation non-inferiority passes.

## 9. Scientific boundary

Passing the milestone would show that this declared local mechanism can produce the tested Functional Web and cardinal roles in a synthetic domain. It would not establish that the abstraction is anatomically exact, that every concept has one cardinal, that the mechanism scales to natural language, or that unimplemented forms of memory and reasoning follow automatically.

Failure is also informative. Artifacts must distinguish failures of settling, recruitment, basin formation, sequence sensitivity, web detection, cardinal causality, redundancy, and statistical replication rather than collapsing them into one score.
