"""`python -m ccf6 <experiment file>` — run an experiment, write an artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from ccf6.artifacts import (
    validate_cortical_circuit_artifact,
    validate_functional_web_artifact,
)
from ccf6.experiment import execute, load


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: python -m ccf6 <experiment.json> [artifact_root] | "
            "--validate <artifact_directory>",
            file=sys.stderr,
        )
        return 2
    if argv[1] == "--validate":
        if len(argv) != 3:
            print("usage: python -m ccf6 --validate <artifact_directory>", file=sys.stderr)
            return 2
        artifact = Path(argv[2])
        manifest = json.loads((artifact / "manifest.json").read_text())
        validator = (
            validate_cortical_circuit_artifact
            if manifest.get("contract") == "ncl-cortical-circuit-v1"
            else validate_functional_web_artifact
        )
        print(json.dumps(validator(artifact), indent=2))
        return 0
    definition = load(argv[1])
    root = argv[2] if len(argv) > 2 else "artifacts"
    out = execute(definition, root)
    print(out)
    print(json.dumps(json.loads((Path(out) / "summary.json").read_text()), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
