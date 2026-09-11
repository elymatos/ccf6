# CCF6 — Connectionist Cognitive Framework, version 6

A minimal, inspectable framework for testing computational consequences of Neurocognitive Linguistics. Network mechanics are implemented in Python; a Laravel workbench renders experiment artifacts.

CCF6 is a reference instrument rather than a product. Its current architecture is intentionally small enough for every connection rule, activation path, learning event, and measurement to remain inspectable.

## Reading order

- [`docs/neurocognitive_linguistics_summary.md`](docs/neurocognitive_linguistics_summary.md) — theoretical source and scientific cautions.
- [`CONTEXT.md`](CONTEXT.md) — settled project language.
- [`docs/architecture.md`](docs/architecture.md) — the NCL-only module structure and scientific boundaries.
- [`docs/specification.md`](docs/specification.md) — normative mechanics, experiment protocol, evidence, and conformance status.
- [`docs/adr/`](docs/adr) — hard-to-reverse project decisions.

## Setup

```bash
cp .env.example .env
composer install
touch database/database.sqlite
docker compose run --rm --no-deps php php artisan key:generate
docker compose run --rm --no-deps php php artisan migrate
```

## Running

```bash
docker compose up -d
```

The workbench is available on port 8002 and the Python runtime on port 8933.

Run the complete paired-seed Functional Web milestone directly:

```bash
PYTHONPATH=ccf6-runtime/src python3 -m ccf6 \
  experiments/011-replicated-milestone.json artifacts
```

Or through the runtime service:

```bash
curl -X POST http://localhost:8933/run \
  -H 'Content-Type: application/json' \
  --data-binary @experiments/011-replicated-milestone.json
```

The milestone writes one complete `ncl-functional-web-v1` artifact containing the exact definition and software identity, generated datasets and topology, Presentation records, learning and activity arrays, frozen Target Basins, Functional Web and cardinal evidence, seed-level metrics, aggregate intervals, failures, and verdict. The workbench reads these files without rerunning or recomputing the experiment.

Validate every required file independently of the experiment runner:

```bash
PYTHONPATH=ccf6-runtime/src python3 -m ccf6 --validate artifacts/<run-directory>
```

## Tests

```bash
PYTHONPATH=ccf6-runtime/src python3 -m pytest ccf6-runtime/tests -q
php artisan test --compact
```

## Current scientific question

Can repeated co-activation, local competition, reciprocal connectivity, and Recruitment produce stable Target Basins that recognize partial Presentations and reactivate their supporting Functional Webs? The accepted 20-seed milestone answers **no** for the declared apparatus: the negative verdict and all failures remain part of the durable artifact contract.
