"""The Cognitive runtime behind HTTP.

The smallest transport that works (ADR-0008): plain JSON over stdlib HTTP, no schema
catalogue, no streaming, no second service. Laravel posts an experiment definition and
gets back the artifact it produced.

A run is synchronous. That is honest rather than lazy — the caller learns the run
finished because the response arrived, and there is no queue to be wrong about.
"""

from __future__ import annotations

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ccf6 import __version__
from ccf6.experiment import KINDS, execute

ARTIFACT_ROOT = Path(os.environ.get("CCF6_ARTIFACT_ROOT", "artifacts"))


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "version": __version__, "kinds": sorted(KINDS)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/run":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            definition = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as malformed:
            self._send(400, {"error": f"malformed request: {malformed}"})
            return

        try:
            out = execute(definition, ARTIFACT_ROOT)
        except KeyError as unknown:
            self._send(400, {"error": str(unknown)})
        except Exception:  # a failed run is a result, not a crash
            self._send(500, {"error": "run failed", "traceback": traceback.format_exc()})
        else:
            self._send(
                200,
                {
                    "run": out.name,
                    "artifact": str(out),
                    "summary": json.loads((out / "summary.json").read_text()),
                },
            )

    def log_message(self, fmt: str, *args) -> None:
        print(f"[ccf6] {fmt % args}", flush=True)


def main() -> None:
    port = int(os.environ.get("CCF6_PORT", "8931"))
    ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"[ccf6] runtime {__version__} on :{port}, artifacts -> {ARTIFACT_ROOT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
