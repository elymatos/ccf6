# CCF6 NCL Functional Web Specification

Status: **accepted target specification** · 2026-09-09

This document specifies the next implementation of CCF6. It derives from [`neurocognitive_linguistics_summary.md`](neurocognitive_linguistics_summary.md) and realizes the architecture in [`architecture.md`](architecture.md). The current runtime is a prototype and is not assumed to conform.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## 1. Objective

The first milestone MUST test whether local, success-gated learning can produce an overlapping Functional Web with an operational Cardinal Node from initially unlabelled Columns.

A successful implementation MUST demonstrate all of the following against matched controls:

1. category-sensitive convergence across varied grounded instances;
2. bidirectional access from visual properties and a learned pseudoword;
3. completion from either partial Entry Route;
4. ordered phonological reactivation from visual evidence alone;
5. causally detectable Functional Web membership;
6. a Cardinal Candidate whose stimulation and Lesion have the predicted distributed effects;
7. shared lower-level Columns across overlapping Functional Webs;
8. no material loss of held-out category separation.

The milestone MUST NOT claim natural-language competence, biological equivalence, episodic memory, symbolic reasoning, or a complete theory of cortical learning.

## 2. Normative domain model

The canonical meanings of Column, Population, Functional Web, Cardinal Node, Cardinal Candidate, Entry Route, Target Basin, Eligibility, Success Signal, Recruitment, Ignition, Pattern Completion, and Lesion are defined in [`../CONTEXT.md`](../CONTEXT.md).

The runtime MUST NOT store any of the following as intrinsic Column state:

- a category or concept identifier;
- Functional Web membership;
- Cardinal Candidate or Cardinal Node status;
- a semantic feature name;
- a pseudoword identity;
- a construction-specific instruction.

Functional Web and cardinal classifications are observer-level scientific results derived after activity has been measured.

## 3. Experimental domain

### 3.1 Categories and visual instances

The experiment MUST generate four synthetic categories. Each category MUST have:

- three visual property dimensions;
- one prototype;
- eight acquisition instances;
- four disjoint basin-estimation instances;
- four disjoint final held-out instances.

Properties MUST overlap across categories. The generator MUST satisfy these constraints before a run begins:

1. no single property uniquely identifies one category;
2. marginal property frequencies are balanced across categories;
3. every category shares at least one property with every other category;
4. at least one property is shared by exactly two categories, making overlap measurable;
5. held-out instances differ from every acquisition instance;
6. prototype distance varies across instances so graded category response can be measured.

A generated dataset that violates a constraint MUST be rejected rather than silently repaired during training.

### 3.2 Pseudowords

Each category MUST be paired with one three-segment pseudoword. A segment MUST be represented by a distributed pattern over reusable auditory features.

The pseudoword inventory MUST satisfy:

1. every segment occurs in more than one pseudoword;
2. every auditory feature occurs in more than one segment;
3. no feature or segment uniquely identifies a category;
4. complete pseudowords are distinguishable only through ordered conjunctions;
5. reversed, permuted, and repeated-segment controls exist for every pseudoword.

No one-hot pseudoword or category code may enter the Network.

### 3.3 Pairings and unsuccessful controls

Correct visual–pseudoword pairs and mismatched pairs MUST be balanced within each acquisition epoch. Correct pairs emit a Success Signal of `1.0` after settling. Mismatched pairs emit `0.0`.

The Success Signal is diffuse. It MUST NOT encode the category, pseudoword, Population, Column, or connection responsible for the outcome.

## 4. Network topology

### 4.1 Required Populations

The first milestone MUST contain this minimum topology:

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

There MUST be one visual-property Population per property dimension. Population names MAY describe source provenance and broad wiring role. They MUST NOT declare learned semantic content. In particular, a Population MUST NOT be configured as “concept,” “category,” or a category name.

All Populations MUST use the same Column mechanics. No cross-domain or phonological Population may receive a privileged processor type.

### 4.2 Connections

Connections MUST be sparse, directed, and bounded. Each inter-Population projection MUST declare its fan-in and initialization distribution.

Connected Populations MUST have reciprocal endpoint topology: if an ascending route joins two Columns, a descending route between those endpoints MUST exist. Ascending and descending routes MUST have separate weights and Eligibility traces. Their values MUST NOT be tied or inferred by transposition during execution.

The first milestone MUST use fixed latent topology. Learning MAY change existing weights but MUST NOT add, delete, or redirect connections.

### 4.3 Inhibition

Lateral inhibition MUST use fixed local topology and declared strengths during this milestone. Inhibitory learning is outside milestone scope. Inhibition MUST be bounded by neighborhoods or competition groups; global all-to-all inhibition is forbidden.

## 5. Column state and dynamics

### 5.1 State

Each Column `i` MUST hold only:

- Input activity `u_i ∈ [0,1]`;
- Integration activity `v_i ∈ [0,1]`;
- Output activity `o_i ∈ [0,1]`;
- response threshold `θ_i` within declared bounds;
- homeostatic activity average;
- entrenchment evidence;
- presentation IDs contributing to entrenchment.

Connections, rather than Columns, hold directional weights and Eligibility traces.

The functional compartments are named **Input**, **Integration**, and **Output**. Anatomical layer names MAY appear as explanatory aliases but MUST NOT define behavior.

### 5.2 Rest and reset

Resting Input, Integration, and Output MUST be zero. Numerical algorithms MAY use an epsilon when dividing, but MUST NOT inject a nonzero activation floor.

Activity and Eligibility MUST reset between independent Presentations. Activity and Eligibility MUST persist between Samples within one Presentation. Weights, thresholds, homeostatic averages, entrenchment, and topology MUST survive activity reset.

### 5.3 Helpers

For time step `dt` and time constant `τ`:

```text
leaky(current, target, τ)
  = current + (target − current) × (1 − exp(−dt / τ))
```

The graded response is:

```text
response(v, θ, temperature)
  = sigmoid((v − θ) / temperature)
```

All constants MUST be declared in the experiment definition. `temperature` and every `τ` MUST be positive.

### 5.4 Synchronous tick

Every value at tick `t+1` MUST be computed only from state at tick `t`.

For Column `i`:

```text
input_drive_i(t)
  = sensory_i(t)
  + Σ_j ascending_weight_ji × output_j(t)

u_i(t+1)
  = leaky(u_i(t), clamp01(input_drive_i(t)), tau_input)

integration_drive_i(t)
  = u_i(t)
  + recurrent_gain × v_i(t)
  + Σ_k descending_weight_ki × output_k(t)
  − Σ_l inhibition_li × output_l(t)

v_i(t+1)
  = leaky(v_i(t), clamp01(integration_drive_i(t)), tau_integration)

o_i(t+1)
  = leaky(
      o_i(t),
      response(v_i(t), θ_i, temperature),
      tau_output
    )
```

Broadcast activity is:

```text
broadcast_i = output_i if output_i ≥ transmission_cutoff else 0
```

The transmission cutoff MUST NOT alter stored Output activity.

### 5.5 Settling

A presented Sample or settling phase is stable when:

```text
max_i(abs(output_i(t) − output_i(t−1))) < epsilon
```

for `stable_ticks` consecutive ticks. The run MUST declare `epsilon`, `stable_ticks`, and `max_ticks`.

Reaching `max_ticks` without stability MUST be recorded as a settling failure. Recognition MUST NOT be inferred from a failed settling phase.

## 6. Connectivity initialization and normalization

For each projection:

1. each target samples its declared fan-in without replacement;
2. sampling is deterministic from the run seed;
3. initial directional weights are independently sampled from one declared small-positive distribution;
4. topology and initial weights are identical across paired experimental arms;
5. weights remain in `[0,1]`;
6. incoming excitatory weights are normalized per target and per projection to a declared norm.

Normalization MUST NOT combine unrelated source Populations. Any weight reduction caused by normalization is homeostatic competition for bounded incoming strength, not evidence-dependent weakening and MUST NOT be reported as anti-Hebbian learning.

## 7. Eligibility, learning, and Recruitment

### 7.1 Eligibility

Each plastic directional connection from `j` to `i` holds:

```text
eligibility_ji(t+1)
  = clamp01(
      eligibility_decay × eligibility_ji(t)
      + output_j(t) × integration_i(t)
    )
```

`eligibility_decay` MUST be in `[0,1]`. Eligibility persists within one Presentation and resets before the next.

### 7.2 Durable weight update

Learning occurs only after the Presentation has settled and its Success Signal is known:

```text
delta_weight_ji
  = learning_rate
    × success_signal
    × eligibility_ji
    × (1 − weight_ji)

weight_ji
  = normalize_projection_target(
      clamp01(weight_ji + delta_weight_ji)
    )
```

With `success_signal = 0`, Eligibility MUST NOT cause a durable evidence-dependent weight change. Milestone one has no negative Success Signal and no anti-Hebbian rule.

Ascending and descending connections update independently from their own local Eligibility.

### 7.3 Entrenchment and Recruitment

After a successful Presentation:

```text
confirmed_i
  = success_signal × max(incoming_eligibility_i)

entrenchment_i
  = entrenchment_i + confirmed_i
```

The run MUST record which distinct Presentations contributed. A Column becomes Recruited only when:

```text
entrenchment_i ≥ recruitment_threshold
and distinct_successful_presentations_i ≥ minimum_presentations
```

Ticks and Samples within one Presentation MUST NOT count as separate recurrence evidence.

Recruitment does not make a Column a Cardinal Candidate.

### 7.4 Homeostatic threshold adaptation

Once per acquisition Presentation:

```text
activity_average_i
  = moving_average(activity_average_i, settled_output_i)

threshold_i
  = clamp(
      threshold_i
      + threshold_rate × (activity_average_i − target_activity),
      threshold_min,
      threshold_max
    )
```

Threshold adaptation is local, receives no Success Signal, and MUST be frozen during basin estimation and evaluation.

## 8. Acquisition and evaluation protocol

### 8.1 Acquisition Presentation

A correct acquisition Presentation proceeds as follows:

1. reset activity and Eligibility;
2. present distributed visual properties;
3. retain visual activity through recurrent persistence;
4. present three distributed pseudoword segments in order;
5. allow joint activity to settle;
6. emit the diffuse Success Signal;
7. update eligible weights, entrenchment, and thresholds once.

A mismatched Presentation follows the same sequence but emits `0.0`.

### 8.2 Frozen evaluation

Durable learning, entrenchment, and threshold adaptation MUST be frozen during basin estimation and final evaluation.

Evaluation MUST include:

- full paired Presentation;
- visual-only cue;
- pseudoword-only cue;
- partial visual cue;
- atypical held-out visual instance;
- reversed pseudoword;
- permuted pseudoword;
- repeated-segment pseudoword;
- competing pseudowords;
- candidate stimulation;
- candidate Lesion;
- matched control stimulation and Lesion.

## 9. Target Basins and Pattern Completion

### 9.1 Basin estimation

A Target Basin is estimated from the four basin-estimation instances per category. It MUST NOT be one stored training vector.

For each category, record:

- centroid of settled activity;
- per-Column stability;
- within-category distance distribution;
- between-category distances;
- reliable-Column mask selected without held-out data.

The reliable mask MUST be frozen before final evaluation.

### 9.2 Distance

Primary basin distance MUST be standardized Euclidean distance over reliable Columns:

```text
distance(activity, centroid)
  = sqrt(mean(((activity − centroid) / pooled_scale)^2))
```

`pooled_scale` MUST be estimated from the basin-estimation split and bounded below by a declared `minimum_scale`. Cosine distance SHOULD be reported as a secondary diagnostic.

### 9.3 Correct-basin criterion

The basin margin MUST be derived from the frozen training/basin-estimation within-category distance distribution. A partial cue succeeds only if:

```text
distance_to_correct + basin_margin
  < distance_to_every_competing_basin
```

It MUST also move closer to the correct basin after recurrent settling than it was at the initial partial state.

## 10. Ordered phonological reactivation

A visual-only cue MUST be evaluated against the full auditory/phonological Output trajectory, not only its final state.

The reinstated trajectory MUST be closer to the correct ordered pseudoword trajectory than to:

- every competing pseudoword;
- its reversed sequence;
- declared segment permutations;
- its repeated-segment control.

A system responding only to the unordered feature bag fails lexical Entry Route acquisition.

## 11. Functional Web detection

Functional Web detection is an offline observer operation and MUST use only acquisition and basin-estimation data.

A Column may be included only when converging evidence shows:

1. category-conditioned activation reliability above the 95th percentile of shuffled-label controls;
2. causal completion contribution above the 95th percentile of matched random-Column perturbations;
3. reciprocal effective connectivity above the 95th percentile of degree-matched random coalitions.

Multiple testing across Columns MUST use false-discovery-rate correction. Raw scores, control distributions, corrected values, and selected membership MUST be recorded.

A Column MAY belong to more than one Functional Web. The first milestone MUST demonstrate shared feature Columns between at least two category webs while higher association activity remains distinguishable.

A set of Columns selected only because their activation exceeds a threshold is not a Functional Web.

## 12. Cardinal lifecycle and causal tests

### 12.1 Cardinal Candidate

A Recruited Column or redundant population becomes a Cardinal Candidate in the observer report only if it:

1. activates from at least two independent Entry Routes;
2. remains stable across basin-estimation instances;
3. increases supporting-web activation when stimulated;
4. exceeds matched non-recruited controls on these measures.

Commitment, entrenchment, centrality, or high activation alone is insufficient.

### 12.2 Candidate stimulation

With sensory input absent, stimulation MUST clamp candidate Output to its median full-presentation activation for a declared pulse duration. It MUST NOT use maximal activation unless that median is maximal.

The report MUST compare resulting Subweb activation with degree-, activity-, Population-, Level-, and entrenchment-matched control stimulation.

### 12.3 Lesion

A Lesion clamps selected Output to zero while leaving incoming Input and Integration observable. Tests MUST include:

- each candidate individually;
- the candidate group;
- matched Recruited Columns;
- matched random Columns.

Controls MUST be matched on Population, Level, settled activation, incoming degree, outgoing degree, entrenchment, and baseline perturbation sensitivity.

Report separately:

- Ignition success;
- Pattern Completion;
- lower-level feature accessibility;
- ordered phonological reactivation;
- recovery through redundant candidates.

### 12.4 Cardinal Node classification

Cardinal Node classification is an observer result, never a runtime flag. A candidate qualifies only when:

1. its Lesion significantly impairs Ignition relative to matched controls;
2. lower-level feature activity remains partly accessible;
3. its stimulation reinstates multiple supporting Subwebs;
4. redundancy either preserves partial function or fragility is explicitly reported;
5. effects reproduce across seeds.

## 13. Controls and statistical inference

### 13.1 Required paired arms

Each seed MUST generate:

1. a trained network;
2. an identical untrained network;
3. a trained network with shuffled category–pseudoword pairing;
4. candidate Lesions and matched control Lesions.

Topology, initial directional weights, dataset partitions, and parameter declarations MUST match wherever the control permits.

### 13.2 Seeds

The primary experiment MUST use at least 20 deterministic paired seeds. Presentations are nested observations and MUST NOT be treated as independent experimental replicates.

### 13.3 Bootstrap

Aggregate effects MUST use paired seed-level differences and a deterministic bootstrap with at least 10,000 resamples. Report:

- every seed-level value;
- median paired effect;
- bootstrap 95% confidence interval;
- proportion of seeds in the expected direction;
- explicit failure count.

### 13.4 Acceptance criteria

Milestone one succeeds only if all conditions hold:

1. completion improvement over untrained control has a 95% interval excluding zero;
2. cross-route reactivation improvement has a 95% interval excluding zero;
3. correct Target Basin beats every competitor by the frozen margin;
4. ordered pseudoword trajectory beats reversed, permuted, repeated, and competing controls;
5. learned effects are localized to correct pairings relative to shuffled pairing;
6. Functional Web overlap is demonstrated;
7. candidate stimulation and Lesion outperform matched controls;
8. the lower confidence bound for held-out category-separation change is above the `−5%` relative non-inferiority margin;
9. settling failures and seed failures are reported rather than discarded.

No result from one seed is sufficient.

## 14. Artifact contract

The implementation MUST emit artifact contract `ncl-functional-web-v1`.

Every run set MUST contain:

| File | Required contents |
|---|---|
| `definition.json` | Exact user-supplied experiment definition. |
| `manifest.json` | Contract, software version, digest, timestamps, arm, seed, status, and file inventory. |
| `dataset.json` | Generated properties, pseudowords, pairings, constraints, and immutable split membership. |
| `topology.npz` | Directed endpoints, initial weights, projection identity, and inhibition topology. |
| `presentations.jsonl` | Presentation identity, Samples, Success Signal, settling duration, and settling status. |
| `learning.npz` | Eligibility summaries, pre/post weights, thresholds, entrenchment, and recruitment evidence. |
| `activity.npz` | Per-presentation initial and settled activity plus required phonological trajectories. |
| `basins.json` | Centroids, scales, margins, reliable masks, and distance distributions. |
| `webs.json` | Raw detector evidence, control distributions, corrected values, and overlapping memberships. |
| `cardinals.json` | Candidate evidence, stimulation, Lesion, redundancy, and final observer classifications. |
| `metrics.json` | Per-condition and per-seed measurements. |
| `aggregate.json` | Paired effects, bootstrap intervals, direction counts, failures, and acceptance verdict. |

Tick-by-tick activity MAY be emitted as an optional diagnostic. It is not mandatory unless required to diagnose settling or sequence behavior.

A digest MUST change when any definition, generated dataset, topology, parameter, or software version affecting results changes.

## 15. Runtime module interface

The runtime MUST expose one deep `Network` module whose interface supports:

```text
construct from declared topology and parameters
reset presentation activity
present one sensory Sample
settle or report failure
emit a diffuse Success Signal
freeze or enable durable learning
observe activity without semantic interpretation
stimulate selected Outputs
lesion selected Outputs
snapshot topology and learned state
```

Functional Web detection, Target Basin estimation, Cardinal classification, controls, and statistical aggregation belong to the experiment observer. They MUST NOT become hidden behavior inside the `Network` interface.

Sensory adapters MUST remain stateless and replaceable. They MAY encode distributed physical features but MUST NOT carry category identity, presentation history, or learned outcomes.

## 16. Validation and implementing tests

Tests MUST target observable contracts and scientific prohibitions. At minimum, implementation must include tests proving:

- rest is exactly zero;
- synchronous updates are order-independent;
- output is graded around per-Column thresholds;
- reciprocal topology does not tie directional weights;
- Eligibility decays and resets at Presentation boundaries;
- no Success Signal means no evidence-dependent durable update;
- one Presentation cannot satisfy recurrence by repeated ticks;
- homeostatic thresholds update independently of success;
- evaluation freezes every durable state;
- no input feature uniquely identifies a category or pseudoword;
- reversed and permuted pseudowords remain distinct;
- held-out data cannot affect basin or web selection;
- Lesion suppresses Output but preserves incoming observability;
- matched controls satisfy all matching constraints;
- paired arms share initial conditions;
- aggregate inference operates over seeds rather than Presentations;
- every required artifact can be read without rerunning the experiment.

## 17. Conformance matrix

The table describes the repository at the time this specification was accepted.

| Requirement | Scientific rationale | Required evidence | Current status | Implementing test |
|---|---|---|---|---|
| One Network of ordinary Columns | Function comes from connectivity | Same mechanics in every Population | Conforming in Functional Web contract | `test_every_population_uses_the_same_column_mechanics` |
| Neutral Population roles | Configured names must not assign meaning | No semantic Population declarations | Partial: Functional Web declarations conform; prototype retirement pending | `test_semantic_and_cardinal_population_flags_are_refused` |
| Three functional compartments | Preserve route-sensitive integration | Input/Integration/Output traces | Conforming in Functional Web contract | `test_compartments_follow_normative_equations_synchronously` |
| Zero resting activity | Avoid artificial similarity and background propagation | Exact zero after reset | Conforming in Functional Web contract | `test_reset_has_zero_activity` |
| Logistic graded Output | Support thresholds and prototypes | Threshold response curve | Conforming | `test_output_is_graded_around_threshold` |
| Operational settling | Recognition requires stable activity | Duration and failure status | Conforming | `test_settling_requires_stable_output` |
| Separate reciprocal weights | Recognition and reactivation need not be symmetric | Same endpoints, independent values | Conforming in Functional Web contract | `test_reciprocal_routes_have_independent_weights` |
| Eligibility traces | Separate local credit from outcome | Trace evolution and reset | Conforming | `test_eligibility_follows_bounded_decay_and_endpoint_coactivity` |
| Diffuse Success Signal | Confirm outcomes without per-weight labels | Correct/mismatch durable changes | Conforming | `test_only_success_confirms_eligible_connections` |
| Presentation-level Recruitment | Repetition means distinct experiences | Contributing Presentation IDs | Conforming in Functional Web contract; prototype retirement pending | `test_one_presentation_cannot_recruit_by_itself` |
| Homeostatic thresholds | Prevent monopolies without semantic supervision | Local threshold histories | Conforming | `test_homeostasis_is_local_and_independent_of_success` |
| Frozen evaluation | Prevent evaluation from becoming further training | Exact durable pre/post state | Conforming | `test_evaluation_freezes_every_durable_adaptation` |
| Structured synthetic domain | Test grounding and lexical routes | Validated dataset artifact | Conforming | `test_generated_domain_satisfies_constraints` |
| Ordered pseudowords | Lexical form is relational and sequential | Sequence-control distances | Conforming | `test_presentations_preserve_order_and_reject_unordered_feature_bags` |
| Target Basin distributions | Completion is attraction, not vector lookup | Frozen centroids, scales, margins | Unsupported | `test_held_out_data_cannot_shape_basins` |
| Functional Web detector | Webs require convergent causal evidence | Reliability, perturbation, connectivity controls | Unsupported | `test_web_membership_requires_all_evidence` |
| Overlapping webs | Reusable structure must be shared | Shared feature membership | Unsupported | `test_detected_webs_can_overlap` |
| Cardinal lifecycle | Addressability is earned behavior | Route, stimulation, Lesion, redundancy evidence | Nonconforming: commitment creates candidates | `test_commitment_alone_is_not_a_candidate` |
| Lesion and stimulation | Establish causal role | Matched intervention effects | Unsupported | `test_lesion_preserves_incoming_activity` |
| Paired controls and 20 seeds | Separate learning from arbitrary wiring | Per-seed paired metrics | Unsupported | `test_arms_share_initial_conditions` |
| Seed-level bootstrap | Avoid pseudoreplication | Deterministic paired intervals | Unsupported | `test_bootstrap_resamples_seed_effects` |
| `ncl-functional-web-v1` artifacts | Make claims reproducible and inspectable | Complete file inventory | Partial: dataset, topology, Presentations, learning, Recruitment, homeostasis, and activity slices exist | `test_recruitment_requires_distinct_presentations_and_evaluation_is_frozen` |

The implementation MUST update this matrix as requirements become conforming. A requirement may be marked conforming only when its implementing test and required artifact evidence both exist.
