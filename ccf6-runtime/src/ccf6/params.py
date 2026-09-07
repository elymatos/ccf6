"""The declared numerical defaults.

Every constant the mechanics use lives here and is overridable from an experiment
file. None has a default inside the module that uses it, so a run cannot quietly
depend on a number nobody declared.

Provenance: ADR-0006. These come from an unfitted conceptual demonstration and carry
no empirical authority. They are a working set we own, not evidence about cortex.
"""

from __future__ import annotations

#: Route weights. Inhibition outweighs excitation, which is what makes competition
#: competitive without needing divisive normalization.
EXCITATORY = 0.73
MODULATORY = 0.48
INHIBITORY = 0.90

#: The target is clamped before relaxation, so activation stays in range by
#: construction. The floor is not zero: no Column is ever perfectly silent, so the
#: network cannot get stuck dead.
ACTIVATION_FLOOR = 0.018
ACTIVATION_CEILING = 1.0

#: Relaxation time constants, in the same units as `dt`. Only the pyramidal constant
#: is used today; the interneuron constants are recorded because the source
#: distinguishes them and we will want them when inhibitory populations exist as
#: Columns rather than as a weighted route.
TAU_PYRAMIDAL = 0.13
TAU_PV_FAST_INHIBITORY = 0.075
TAU_SOM_SLOW_INHIBITORY = 0.22
TAU_VIP = 0.14

#: One tick. With tau = 0.13 this moves activation about 12% of the way to target per
#: tick, so a stimulus needs a few dozen ticks to settle.
DT = 1.0 / 60.0

DEFAULTS: dict[str, float] = {
    "excitatory": EXCITATORY,
    "modulatory": MODULATORY,
    "inhibitory": INHIBITORY,
    "activation_floor": ACTIVATION_FLOOR,
    "activation_ceiling": ACTIVATION_CEILING,
    "tau_l4": TAU_PYRAMIDAL,
    "tau_l23": TAU_PYRAMIDAL,
    "tau_l5": TAU_PYRAMIDAL,
    "dt": DT,
    # Gain on L2/3's recurrent self-drive. This is what "keeps the circuit activated
    # until inhibited"; above 1/excitatory it would self-sustain without input.
    # Gain on L2/3's recurrent self-drive. This is what "keeps the circuit activated
    # until inhibited"; above 1/excitatory it would self-sustain without input.
    "recurrent_gain": 0.55,
    # Feedback from the Level above, onto L2/3 rather than onto L4.
    "feedback_gain": 0.35,
    "lateral_gain": 1.0,
    "thalamic_gain": 1.0,
    # What a Column must exceed before it transmits anything. Taken from the same
    # source as the route weights, where it gates the displayed signal.
    "transmission_threshold": 0.055,
}


def resolve(overrides: dict | None = None) -> dict[str, float]:
    """Declared defaults with an experiment's overrides applied.

    An unknown key is an error rather than a silent no-op: a misspelled parameter
    that did nothing would look exactly like a parameter that had no effect.
    """
    values = dict(DEFAULTS)
    for key, value in (overrides or {}).items():
        if key not in values:
            raise KeyError(f"unknown parameter {key!r}; declared: {sorted(values)}")
        values[key] = float(value)
    return values
