# Cortical Column Circuit (Dynamic) — Companion Reference

## Purpose
Companion map for `Cortical_Column_Circuit_Dynamic.html`, summarizing all modeled structures, pathways, and process presets used in the interactive SVG circuit.

## Circuit Architecture

### Core relays / state nodes
- **`thal`** – thalamic relay (sensory input, arousal gating, corticothalamic return).
- **`motor`** – subcortical output sink.
- **State drivers:** `attention`, `arousal`, `novelty`, `reward` (all feed state-dependent modulation).

### Low-order column A and B (mirror structure)
For each column (`A*`, `B*`):
- **Pyramidal excitatory populations**: `A4`, `B4` (L4), `A23`, `B23` (L2/3), `A5`, `B5` (L5), `A6`, `B6` (L6).
- **Interneurons**: `APV23`, `BPV23` (L2/3 PV), `APV5`, `BPV5` (L5 PV), `ASOM`, `BSOM` (L2/3 SOM), `ASOM5`, `BSOM5` (L5 SOM), `AVIP`, `BVIP` (VIP).
- **Apical targets**: `A1`,`B1` (L2/3 tuft) and `A5T`,`B5T` (L5 tuft).

### Higher-order cortical node set
- **`H23`** – higher L2/3 predictive population.
- **`H5`** – higher L5 predictive population.
- **`H4`** – higher input target for bottom-up residuals.

## Main route families (edges)

- **Input (thal →)**
  - `thal → A4`, `B4`, and PV in both columns.
  - Added **direct weak thalamic branches** to L6 (`A6`,`B6`) and L2/3 (`A23`,`B23`) for broader sensory context.

- **Feedforward flow (Intracolumnar)**
  - L4 → L2/3 (`A4→A23`, `B4→B23`).
  - L2/3 → L5 (`A23→A5`, `B23→B5`) and L5 → L6 output stream.
  - L5 output to `motor` and deep corticothalamic return (`A6/B6 → thal`).

- **Ascending/Residual channels**
  - Local L2/3 and L5 excitatory outputs send residual/representational updates to higher cortex: `A23/B23/H5` to `H4`, `A5/B5` to `H4`, plus L5→H23/L2/3→H23 residual branches.

- **Top-down prediction**
  - `H23/H5 → L1 tuft nodes` (`A1/B1`, `A5T/B5T`).
  - Added top-down to deeper targets (`H23/H5 → A6/B6`) and context-to-lower transfer (`A1/B1 → A23/B23`, tuft→soma links).

- **Lateral competition**
  - Horizontal L2/3 excitatory collaterals: `A23/B23` project to opposite-column PV/SOM and higher-layer inhibitory elements.
  - Adds cross-column SOM recruitment and inter-column inhibitory bias.

### Inhibitory microcircuits

- **PV+ fast gain motifs**
  - Thalamus excites PV in L4; PV inhibits local pyramidal (L4 L2/3 L5 somatic compartments).
  - PV→SOM and PV→VIP inhibitory motifs added for precision/priority control.
  - PV feedback is present both local and cross-layer (L2/3→L5).

- **SOM+ dendritic motifs**
  - SOM→tuft inhibition on L2/3 and L5 apical compartments (L1 and L5-targeted).
  - SOM receives local pyramidal recruitment and can suppress PV/VIP channels for routing control.

- **VIP+ disinhibitory motifs**
  - VIP receives top-down (H23, H5), attention, and reward/arousal/novelty-conditioned inputs (Vip route).
  - VIP inhibits SOM populations (L2/3 and L5-associated SOM), effectively releasing apical dendritic gating when behaviorally relevant.

## Behavioral modulatory influences

- **Attention**: strongly drives `AVIP/BVIP`, biases competition by weakening suppression of selected pathway; weakens unselected VIP gain.
- **Arousal**: raises thalamic gain and PV baseline via state routes.
- **Novelty**: boosts ascending residual drive and novelty/VIP-linked disinhibition channels.
- **Reward**: boosts top-down pathways and increases top-down gain via the simulated plasticity term.

## Preset process sets (`SCENARIO_ROUTES`)

- **All**: all route labels active.
- **Input**: thalamocortical + PV control.
- **Flow**: intracolumnar feedforward stream.
- **Ascend**: prediction-error forwarding.
- **Topdown**: corticocortical feedback routes.
- **Lateral**: competition across columns.
- **Pv**: perisomatic gain control.
- **Som**: dendritic gating and SOM recruitment.
- **Vip**: disinhibition motifs (with Som + Topdown context).
- **Integration / Predictive / Competition / Gain / Behavior / Attention / Arousal / Novelty / Reward / Sustained**: predefined higher-level process mixes used by control panel.

## Notes on logic fixes incorporated
1. **VIP circuits now have explicit afferents** from higher cortex and state nodes, not only implicit manual coupling.
2. **SOM→PV and SOM→VIP inhibitory motifs** are explicitly represented.
3. **PV↔SOM/VIP and cross-column inhibitory motifs** are represented to better match interneuron-circuit literature.
4. **Deep-layer feedback pathways** were added (top-down to L6 and L6→thal branches) to better reflect corticothalamic loops.
