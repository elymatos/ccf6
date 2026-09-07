"""`python -m ccf6 <experiment file>` — run an experiment, write an artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ccf6.experiment import execute, load


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m ccf6 <experiment.json> [artifact_root]", file=sys.stderr)
        return 2
    definition = load(argv[1])
    root = argv[2] if len(argv) > 2 else "artifacts"
    out = execute(definition, root)
    print(out)
    print(json.dumps(json.loads((Path(out) / "summary.json").read_text()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
