#!/usr/bin/env python3
"""Create the disposable, loopback-only multi-behavior RideFlow reference project."""

from __future__ import annotations

import argparse
import json
import socket
import tempfile
from pathlib import Path

MARKER = {
    "schema": "mellowyak.phase12.reference.v1",
    "synthetic": True,
    "product": "RideFlow Reference",
    "fixture_scenario": "rideflow",
    "phase13_capabilities": [
        "request_nearest_ride",
        "driver_becomes_available",
        "cancel_ride",
        "fare_preview",
    ],
}


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _write(root: Path, relative: str, content: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content.rstrip() + "\n", encoding="utf-8")


def create(root: Path, web_port: int, api_port: int) -> dict[str, object]:
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise RuntimeError("REFERENCE_PROJECT_ROOT_NOT_EMPTY")
    _write(
        root, ".mellowyak-reference-project.json", json.dumps(MARKER, sort_keys=True)
    )
    _write(root, ".gitignore", "runtime/\n__pycache__/\n*.pyc\n")
    _write(
        root,
        "README.md",
        """
# RideFlow Reference

Synthetic, loopback-only Phase 12M/13M acceptance project. It contains no credentials,
external services, production data, maps provider, payment provider, or database.
""",
    )
    _write(
        root,
        "package.json",
        json.dumps(
            {
                "name": "rideflow-reference",
                "private": True,
                "version": "1.0.0",
                "engines": {"node": "22.x"},
                "scripts": {"start": "node web/server.js"},
            },
            indent=2,
            sort_keys=True,
        ),
    )
    _write(
        root,
        "package-lock.json",
        json.dumps(
            {
                "name": "rideflow-reference",
                "version": "1.0.0",
                "lockfileVersion": 3,
                "requires": True,
                "packages": {
                    "": {
                        "name": "rideflow-reference",
                        "version": "1.0.0",
                        "engines": {"node": "22.x"},
                    }
                },
            },
            indent=2,
            sort_keys=True,
        ),
    )
    _write(root, "api/selection_mode.txt", "nearest")
    _write(
        root,
        "api/domain.py",
        """from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Driver:
    driver_id: str
    x: float
    y: float
    available: bool


DRIVERS = (
    Driver("driver-near", 1.0, 1.0, True),
    Driver("driver-mid", 4.0, 3.0, True),
    Driver("driver-far", 9.0, 9.0, True),
    Driver("driver-offline", 0.1, 0.1, False),
)


def select_driver(pickup: tuple[float, float], mode_file: Path) -> Driver:
    eligible = [driver for driver in DRIVERS if driver.available]
    reverse = mode_file.read_text(encoding="utf-8").strip() == "farthest"
    return sorted(
        eligible,
        key=lambda driver: math.hypot(driver.x - pickup[0], driver.y - pickup[1]),
        reverse=reverse,
    )[0]


def distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    return round(math.hypot(end[0] - start[0], end[1] - start[1]), 3)


def fare_preview(pickup: tuple[float, float], destination: tuple[float, float]) -> dict:
    route_distance = distance(pickup, destination)
    return {
        "currency": "RFC",
        "distance": route_distance,
        "fare": round(4.0 + route_distance * 1.75, 2),
    }


def create_ride(pickup: tuple[float, float], destination: tuple[float, float], mode_file: Path):
    driver = select_driver(pickup, mode_file)
    return {
        "ride_id": "ride-reference-001",
        "driver_id": driver.driver_id,
        "pickup": list(pickup),
        "destination": list(destination),
        "status": "DRIVER_ON_THE_WAY",
        "fare_preview": fare_preview(pickup, destination),
    }


def available_driver(driver_id: str) -> dict:
    driver = next((item for item in DRIVERS if item.driver_id == driver_id), None)
    if driver is None:
        raise ValueError("DRIVER_NOT_FOUND")
    return {**driver.__dict__, "available": True}


def cancel_ride(ride: dict) -> dict:
    if ride.get("status") == "CANCELLED":
        return ride
    return {**ride, "status": "CANCELLED", "driver_available": True}
""",
    )
    _write(
        root,
        "api/server.py",
        """from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from domain import DRIVERS, available_driver, cancel_ride, create_ride, fare_preview

ROOT = Path(__file__).resolve().parents[1]
MODE = ROOT / "api" / "selection_mode.txt"
RIDES: dict[str, dict] = {}


def point(value):
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("POINT_INVALID")
    return float(value[0]), float(value[1])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def reply(self, status, payload):
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.reply(200, {"status": "ok", "service": "rideflow-api"})
        if path == "/drivers":
            return self.reply(200, {"drivers": [driver.__dict__ for driver in DRIVERS]})
        if path.startswith("/rides/"):
            ride = RIDES.get(path.rsplit("/", 1)[-1])
            return self.reply(200, ride) if ride else self.reply(404, {"error": "NOT_FOUND"})
        return self.reply(404, {"error": "NOT_FOUND"})

    def do_POST(self):
        path = urlparse(self.path).path
        length = min(int(self.headers.get("Content-Length", "0")), 16_384)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self.reply(400, {"error": "JSON_INVALID"})
        if path == "/drivers/position":
            return self.reply(200, {"status": "FAKE_GPS_ACCEPTED", "position": payload})
        if path == "/drivers/available":
            try:
                driver = available_driver(str(payload.get("driver_id", "")))
            except ValueError:
                return self.reply(404, {"error": "DRIVER_NOT_FOUND"})
            return self.reply(200, {"status": "AVAILABLE", "driver": driver})
        if path == "/fare-preview":
            try:
                preview = fare_preview(point(payload.get("pickup")), point(payload.get("destination")))
            except (TypeError, ValueError):
                return self.reply(400, {"error": "FARE_REQUEST_INVALID"})
            return self.reply(200, preview)
        if path == "/rides":
            try:
                ride = create_ride(point(payload.get("pickup")), point(payload.get("destination")), MODE)
            except (TypeError, ValueError):
                return self.reply(400, {"error": "RIDE_REQUEST_INVALID"})
            RIDES[ride["ride_id"]] = ride
            return self.reply(201, ride)
        if path.startswith("/rides/") and path.endswith("/cancel"):
            ride_id = path.split("/")[2]
            ride = RIDES.get(ride_id)
            if ride is None:
                return self.reply(404, {"error": "NOT_FOUND"})
            RIDES[ride_id] = cancel_ride(ride)
            return self.reply(200, RIDES[ride_id])
        return self.reply(404, {"error": "NOT_FOUND"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, type=int)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
""",
    )
    _write(
        root,
        "web/server.js",
        """import http from "node:http";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, item, index, all) => {
  if (item.startsWith("--")) pairs.push([item.slice(2), all[index + 1]]);
  return pairs;
}, []));
const port = Number(args.port);
const apiPort = Number(args["api-port"]);

const server = http.createServer(async (request, response) => {
  const url = new URL(request.url || "/", `http://127.0.0.1:${port}`);
  if (url.pathname.startsWith("/api/")) {
    const chunks = [];
    for await (const chunk of request) chunks.push(chunk);
    const body = Buffer.concat(chunks);
    const proxy = http.request({
      hostname: "127.0.0.1", port: apiPort,
      path: url.pathname.slice(4) + url.search,
      method: request.method,
      headers: {
        "content-type": "application/json",
        "content-length": String(body.length),
      },
    }, (upstream) => {
      response.writeHead(upstream.statusCode || 502, { "content-type": "application/json" });
      upstream.pipe(response);
    });
    proxy.on("error", () => {
      response.writeHead(502, { "content-type": "application/json" });
      response.end(JSON.stringify({ error: "API_UNAVAILABLE" }));
    });
    if (body.length) proxy.write(body);
    proxy.end();
    return;
  }
  const name = url.pathname === "/i18n.js" ? "i18n.js" : "index.html";
  const body = await readFile(join(here, name));
  response.writeHead(200, {
    "content-type": name.endsWith(".js") ? "text/javascript" : "text/html; charset=utf-8",
    "cache-control": "no-store",
  });
  response.end(body);
});
server.listen(port, "127.0.0.1");
""",
    )
    _write(
        root,
        "web/i18n.js",
        """export const messages = {
  en: {
    title: "RideFlow Reference", pickup: "Pickup", destination: "Destination",
    request: "Request ride", ready: "Ready", confirmed: "Driver is on the way",
    driver: "Selected driver", fare: "Preview fare", cancel: "Cancel ride",
    available: "Make driver available"
  },
  he: {
    title: "RideFlow לדוגמה", pickup: "נקודת איסוף", destination: "יעד",
    request: "בקשת נסיעה", ready: "מוכן", confirmed: "הנהג בדרך",
    driver: "נהג שנבחר", fare: "תצוגה מקדימה של המחיר", cancel: "ביטול נסיעה",
    available: "הפיכת נהג לזמין"
  }
};
""",
    )
    _write(
        root,
        "web/index.html",
        """<!doctype html>
<html lang="en" dir="ltr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>RideFlow Reference</title><style>
body{font:16px system-ui;background:#071925;color:#eefbff;margin:0;padding:48px}main{max-width:720px;margin:auto}
.card{border:1px solid #176271;border-radius:20px;padding:28px;background:#092330}label{display:grid;gap:7px;margin:15px 0}
input,button{font:inherit;padding:12px;border-radius:9px}button{background:#39d7cf;border:0;font-weight:700}#ride-status{margin-top:20px}
</style></head><body><main class="card"><h1 data-i18n="title"></h1>
<label><span data-i18n="pickup"></span><input data-testid="pickup" name="pickup" value="0,0"></label>
<label><span data-i18n="destination"></span><input data-testid="destination" name="destination" value="8,8"></label>
<button data-testid="request-ride" data-i18n="request"></button>
<button data-testid="fare-preview" data-i18n="fare"></button>
<button data-testid="cancel-ride" data-i18n="cancel"></button>
<button data-testid="driver-available" data-i18n="available"></button>
<p data-testid="ride-status" id="ride-status" aria-live="polite"></p></main>
<script type="module">import {messages} from './i18n.js';
const locale = new URL(location.href).searchParams.get('lang') === 'he' ? 'he' : 'en';
document.documentElement.lang=locale;document.documentElement.dir=locale==='he'?'rtl':'ltr';
for(const node of document.querySelectorAll('[data-i18n]')) node.textContent=messages[locale][node.dataset.i18n];
document.querySelector('[data-testid=request-ride]').addEventListener('click', async()=>{
  const parse=(value)=>value.split(',').map(Number);
  const result=await fetch('/api/rides',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({
    pickup:parse(document.querySelector('[data-testid=pickup]').value),destination:parse(document.querySelector('[data-testid=destination]').value)})});
  const ride=await result.json();const status=document.querySelector('[data-testid=ride-status]');
  status.textContent=`${messages[locale].confirmed} · ${messages[locale].driver}: ${ride.driver_id}`;
  status.dataset.driverId=ride.driver_id;status.dataset.httpStatus=String(result.status);
});
document.querySelector('[data-testid=fare-preview]').addEventListener('click', async()=>{
  const parse=(value)=>value.split(',').map(Number);const result=await fetch('/api/fare-preview',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({pickup:parse(document.querySelector('[data-testid=pickup]').value),destination:parse(document.querySelector('[data-testid=destination]').value)})});
  const preview=await result.json();document.querySelector('[data-testid=ride-status]').textContent=`${messages[locale].fare}: ${preview.fare} ${preview.currency}`;
});
document.querySelector('[data-testid=cancel-ride]').addEventListener('click',async()=>{const result=await fetch('/api/rides/ride-reference-001/cancel',{method:'POST'});document.querySelector('[data-testid=ride-status]').textContent=(await result.json()).status;});
document.querySelector('[data-testid=driver-available]').addEventListener('click',async()=>{const result=await fetch('/api/drivers/available',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({driver_id:'driver-offline'})});document.querySelector('[data-testid=ride-status]').textContent=(await result.json()).status;});
</script></body></html>
""",
    )
    _write(
        root,
        "cli/ride_status.py",
        """from __future__ import annotations

import argparse
import json
from urllib.request import urlopen

parser = argparse.ArgumentParser()
parser.add_argument("--api", required=True)
parser.add_argument("--ride", default="ride-reference-001")
args = parser.parse_args()
with urlopen(f"{args.api}/rides/{args.ride}", timeout=3) as response:
    payload = json.load(response)
print(f"{payload['ride_id']} {payload['status']} {payload['driver_id']}")
""",
    )
    _write(
        root,
        "tests/test_rides.py",
        """from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from domain import available_driver, cancel_ride, create_ride, fare_preview, select_driver  # noqa: E402


class RideFlowTests(unittest.TestCase):
    def test_nearest_eligible_driver(self):
        mode = ROOT / "api" / "selection_mode.txt"
        self.assertEqual(select_driver((0.0, 0.0), mode).driver_id, "driver-near")

    def test_ride_creation(self):
        mode = ROOT / "api" / "selection_mode.txt"
        ride = create_ride((0.0, 0.0), (8.0, 8.0), mode)
        self.assertEqual(ride["driver_id"], "driver-near")
        self.assertEqual(ride["status"], "DRIVER_ON_THE_WAY")

    def test_driver_becomes_available(self):
        self.assertTrue(available_driver("driver-offline")["available"])

    def test_cancel_ride_releases_driver(self):
        ride = {"ride_id": "ride-reference-001", "status": "DRIVER_ON_THE_WAY"}
        cancelled = cancel_ride(ride)
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertTrue(cancelled["driver_available"])

    def test_deterministic_fare_preview(self):
        self.assertEqual(fare_preview((0.0, 0.0), (3.0, 4.0))["fare"], 12.75)


if __name__ == "__main__":
    unittest.main()
""",
    )
    manifest = {
        "schema": "mellowyak.runtime-manifest.v1",
        "reference_marker": MARKER["schema"],
        "profiles": [
            {
                "display_name": "RideFlow Web frontend",
                "runtime_type": "NODE",
                "execution_mode": "MANAGED",
                "executable": "node",
                "argv": [
                    "server.js",
                    "--port",
                    str(web_port),
                    "--api-port",
                    str(api_port),
                ],
                "relative_working_directory": "web",
                "expected_ports": [web_port],
                "health_definition": {"url": f"http://127.0.0.1:{web_port}/"},
                "test_definitions": [],
            },
            {
                "display_name": "RideFlow Python API",
                "runtime_type": "PYTHON",
                "execution_mode": "MANAGED",
                "executable": "python3",
                "argv": ["server.py", "--port", str(api_port)],
                "relative_working_directory": "api",
                "expected_ports": [api_port],
                "health_definition": {"url": f"http://127.0.0.1:{api_port}/health"},
                "test_definitions": [],
            },
            {
                "display_name": "RideFlow deterministic tests",
                "runtime_type": "PYTHON",
                "execution_mode": "MANUAL",
                "executable": "python3",
                "argv": [
                    "-B",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_*.py",
                ],
                "relative_working_directory": ".",
                "expected_ports": [],
                "health_definition": {},
                "test_definitions": [{"type": "TEST", "expected_exit_code": 0}],
            },
            {
                "display_name": "RideFlow ride status CLI",
                "runtime_type": "PYTHON",
                "execution_mode": "MANUAL",
                "executable": "python3",
                "argv": ["ride_status.py", "--api", f"http://127.0.0.1:{api_port}"],
                "relative_working_directory": "cli",
                "expected_ports": [],
                "health_definition": {},
                "test_definitions": [
                    {"type": "CLI", "stdout_contains": "DRIVER_ON_THE_WAY"}
                ],
            },
        ],
    }
    _write(
        root, "mellowyak.runtime.json", json.dumps(manifest, indent=2, sort_keys=True)
    )
    return {
        "schema": MARKER["schema"],
        "root": str(root),
        "web_port": web_port,
        "api_port": api_port,
        "web_url": f"http://127.0.0.1:{web_port}/",
        "api_url": f"http://127.0.0.1:{api_port}",
        "runtime_profile_count": 4,
        "protected_behavior_count": 4,
        "protected_behaviors": list(MARKER["phase13_capabilities"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--web-port", type=int, default=0)
    parser.add_argument("--api-port", type=int, default=0)
    args = parser.parse_args()
    root = args.output or Path(tempfile.mkdtemp(prefix="mellowyak-phase12m-rideflow-"))
    result = create(root.resolve(), args.web_port or _port(), args.api_port or _port())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
