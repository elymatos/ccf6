# CCF6 — Connectionist Cognitive Framework, version 6

A minimal, inspectable framework for defining and testing basic premises of a
connectionist account of cognition. Mechanics in Python; a Laravel workbench for
looking at what they do.

CCF6 is a **reference instrument**, not a product and not a cut-down CCF7. It is
derived blind of CCF7 by design — see [ADR-0001](docs/adr/0001-ccf6-is-a-blind-parallel-instrument.md).

## Reading order

- [`CONTEXT.md`](CONTEXT.md) — the glossary. Start here; the two source traditions use
  the same words for different things and this file keeps them apart.
- [`docs/adr/`](docs/adr) — why each hard-to-reverse decision went the way it did.
- [`docs/journal/`](docs/journal) — what happened in each working session.

## First run

A fresh clone needs three things before the stack will come up. Skipping any of
them leaves containers that start and then exit.

```bash
cp .env.example .env                            # if you don't have one yet
composer install
touch database/database.sqlite                  # DB_CONNECTION=sqlite; the file is not in the repo
docker compose run --rm --no-deps php php artisan key:generate
docker compose run --rm --no-deps php php artisan migrate
```

The last two run inside the php container so they don't depend on the host PHP
having every extension the project needs (`ext-iconv`, in particular).

Why each matters: `QUEUE_CONNECTION` and `CACHE_STORE` are both `database`, so
without the sqlite file the `queue` container exits 1 on boot. Without `APP_KEY`
every request 500s — and the error renderer then throws `Cannot modify header
information`, which is what you'll see at the end of the log; that second error
is noise, the missing key is the cause.

## Running

```bash
docker compose up -d                 # workbench :8002, runtime :8933, redis :6380
docker compose ps                    # all six services should read "Up"
```

Health checks:

```bash
curl -s http://localhost:8933/health # {"status": "ok", ...}
curl -sI http://localhost:8002/      # 200
```

Run an experiment, on the host:

```bash
PYTHONPATH=ccf6-runtime/src python3 -m ccf6 experiments/001-colour-selectivity-baseline.json artifacts
```

…or through the runtime service:

```bash
curl -X POST http://localhost:8933/run -H 'Content-Type: application/json' \
     --data-binary @experiments/001-colour-selectivity-baseline.json
```

Either way the run writes an artifact directory, and the workbench at
<http://localhost:8002> lists it. Results live on disk; the database holds only a
catalogue ([ADR-0007](docs/adr/0007-results-are-artifacts-the-database-is-a-catalogue.md)).

## Tests

```bash
PYTHONPATH=ccf6-runtime/src python3 -m pytest ccf6-runtime/tests -q
docker compose exec php php artisan test
```

## Sources

Two traditions, kept separate rather than merged: neurocognitive linguistics
(`docs/ncl/`) and the Tolman–Eichenbaum Machine (`docs/tem/`). TEM is an inspiration for
mechanism, not a reproduction target.
