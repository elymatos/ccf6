# 0007 — Results are on-disk artifacts; the database holds only a catalogue

Status: accepted · 2026-09-07

## Context

Experiment runs produce numerical arrays — activations per Column per Layer per Level
per tick. These have to live somewhere that supports comparison, archiving and
re-rendering without re-running.

## Decision

Numerical results are written to disk as run artifacts. SQLite holds only a catalogue of
runs: id, experiment file hash, timestamp, status, artifact path. No numerical array is
ever stored in the database.

## Alternatives considered

**Results in the database.** Rejected: numerical arrays in a relational store are slow to
write, awkward to query and painful to migrate.

**No database at all.** Rejected: the catalogue is what makes runs findable months later.

## Consequences

The Python runtime has no database dependency at all, so it stays testable in isolation.
Every run leaves a file that can be diffed, archived and re-rendered. Laravel reads
artifacts; it does not own them.
