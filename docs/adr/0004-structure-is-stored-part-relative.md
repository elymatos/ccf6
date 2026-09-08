# 0004 — Structure is stored part-relative; sampling is egocentric

Status: accepted · 2026-09-07

## Context

If the framework is to recognize the same Object at a different World position, the
stored structure must not depend on where the Object was. Three coordinate frames were
available: allocentric (absolute World coordinates), egocentric (offsets from Ego), and
part-relative (offsets between the Object's own parts, with no origin).

## Decision

**Sampling is egocentric** — one always looks from somewhere — but **what is stored is
part-relative**: the set of offsets among an Object's parts, carrying no origin.

## Alternatives considered

**Allocentric.** Rejected: the same Object at a different position produces a different
representation, so translation invariance would have to be learned rather than being a
property of the frame.

**Egocentric storage.** Rejected: the representation then changes whenever Ego moves, so
a stable Object identity requires path integration to compensate — a real mechanism we
do not yet need.

## Consequences

Translation invariance is a property of the representation rather than of the coordinate
system, and is immediately testable: present one Object at several World positions and
ask whether the stored structure is identical. Ego exists as a sampling pointer only; it
is not yet a tracked, path-integrated Space. Scale and rotation invariance do *not* follow
and would need additional mechanism.
