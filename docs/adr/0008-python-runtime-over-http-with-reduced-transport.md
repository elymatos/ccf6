# 0008 — A Python runtime behind HTTP, with the smallest transport that works

Status: accepted · 2026-09-07

## Context

The mechanics are Python; the visualization testbed is Laravel. The seam between them is
the most consequential structural choice in the tooling. A reference integration path
was available and inspected: two Python containers, Redis pub/sub for streaming, SSE
relay, and a shared JSON Schema catalogue validated on both sides. Measured cost of that
path in the project inspected: about 1,460 lines existing solely to move messages.

## Decision

Keep the process boundary; drop the machinery. One Python container running an
installable `ccf6-runtime` package behind a plain HTTP+JSON endpoint. Laravel polls. No
Redis, no SSE, no schema catalogue, no second service.

## Alternatives considered

**The full reference path.** Rejected: Redis, streaming and schema validation answer
problems CCF6 does not have yet — there is nothing to stream and one message type does
not need a schema document to validate it.

**CLI plus artifacts, no server.** This was recommended, on the grounds that batch runs
match a look-then-proceed workflow and leave artifacts by default. The process boundary
was chosen instead.

## Consequences

The Python package is installable and testable on its own with no Laravel and no
container. Streaming can be added later alongside the artifact writer rather than in
place of it. Until then, live stepping means polling.
