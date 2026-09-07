# 0001 — CCF6 is a parallel instrument, derived blind of CCF7

Status: accepted · 2026-09-07

## Context

A more complete framework, CCF7, already exists and implements much of what CCF6
discusses. Its scope made it impossible to understand the basis of the framework or to
test basic premises, which is why CCF6 exists. The obvious move — start from CCF7 and
remove things — was rejected.

## Decision

CCF6 is a permanent minimal reference implementation that lives alongside CCF7, not a
scratchpad and not a replacement. It is derived **blind**: CCF7's designs are not
consulted while designing CCF6, and none of its structure is imported. Where CCF6
arrives at something CCF7 also has, that is an observation to record after the fact,
never a reason to go there.

## Alternatives considered

**Scratchpad.** Disposable, knowledge migrates to CCF7, code thrown away. Rejected: a
diagnostic instrument earns its keep by staying available, and the pain being solved
here is recurring, not one-off.

**Restart.** CCF7 frozen, CCF6 grows back to its scope. Rejected: it would recreate the
pull toward completeness that made CCF7 unusable.

**Derive, then contrast.** Design independently but consult CCF7's results as evidence.
Rejected by the project owner in favour of full blindness, on the grounds that the point
is to reach the same destination by other means.

## Consequences

We forfeit CCF7's negative results as evidence and may spend effort rediscovering them.
Accepted deliberately. Convergence with CCF7, when it happens, is then genuine
independent arrival rather than reconstruction, which makes it worth more.
