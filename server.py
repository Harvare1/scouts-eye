"""Dependency-free HTTP entry point for the Scout's Eye demo and its API."""
import dataclasses
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from agents.pipeline import ScoutsEyePipeline
from core.match_generator import TEAM_NAMES, generate_match

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
PLAYERS, EVENTS = generate_match(seed=3)
PIPELINE = ScoutsEyePipeline()
PLAYERS_BY_ID = {p.id: p for p in PLAYERS}


def _json(value):
    return json.dumps(value, separators=(",", ":")).encode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = urlparse(self.path)
        query = parse_qs(route.query)

        if route.path == "/api/match":
            return self._send(200, _json({
                "teams": TEAM_NAMES,
                "players": [dataclasses.asdict(p) for p in PLAYERS],
                "events": [dataclasses.asdict(e) for e in EVENTS],
            }), "application/json")

        if route.path == "/api/dossier":
            player_id = query.get("player", [""])[0]
            if player_id not in PLAYERS_BY_ID:
                return self.send_error(404, "unknown player")
            try:
                minute = int(query.get("minute", ["90"])[0])
                if not 0 <= minute <= 90:
                    raise ValueError
            except (TypeError, ValueError):
                return self.send_error(400, "minute must be between 0 and 90")
            metrics, entries = PIPELINE.run_for_player(EVENTS, player_id, minute)
            return self._send(200, _json({
                "player": dataclasses.asdict(PLAYERS_BY_ID[player_id]),
                "metrics": dataclasses.asdict(metrics),
                "entries": [dataclasses.asdict(e) for e in entries],
            }), "application/json")

        if route.path == "/health":
            return self._send(200, b'{"status":"ok"}', "application/json")

        relative = "index.html" if route.path == "/" else route.path.lstrip("/")
        target = (STATIC / relative).resolve()
        if STATIC.resolve() not in target.parents or not target.is_file():
            return self.send_error(404)
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/javascript":
            content_type += "; charset=utf-8"
        self._send(200, target.read_bytes(), content_type)

    def log_message(self, fmt, *args):
        if os.getenv("QUIET") != "1":
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8090"))
    print(f"Scout's Eye · http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
