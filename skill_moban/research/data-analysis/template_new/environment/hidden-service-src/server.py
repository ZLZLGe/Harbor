#!/usr/bin/env python3
from __future__ import annotations

import base64
import importlib.machinery
import importlib.util
import json
import marshal
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from types import ModuleType

import requests


PORT = int(os.environ.get("BOARD_AUDIT_PORT", "8321"))
INTERNAL_URL = os.environ.get("BOARD_AUDIT_INTERNAL_URL", "http://127.0.0.1:8322")
EMBEDDED_IMPL_B64 = "__BOARD_AUDIT_EMBEDDED_IMPL_B64__"
FALLBACK_IMPL_PATH = Path(
    os.environ.get("BOARD_AUDIT_FALLBACK_IMPL_PATH", "/opt/board-audit-private/.board-audit-impl.dat")
)
LOCAL_IMPL_PATH = Path(__file__).with_name("audit_impl.py")


def _load_impl_from_path(path: Path, *, unlink_after_load: bool = False) -> Any:
    if path.suffix == ".py":
        spec = importlib.util.spec_from_file_location("board_audit_local_impl", path)
    else:
        loader = importlib.machinery.SourcelessFileLoader("board_audit_hidden_impl", str(path))
        spec = importlib.util.spec_from_loader("board_audit_hidden_impl", loader)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load local audit implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if unlink_after_load:
        path.unlink(missing_ok=True)
    return module


def _load_embedded_impl() -> ModuleType | None:
    if not EMBEDDED_IMPL_B64 or EMBEDDED_IMPL_B64.startswith("__BOARD_AUDIT_"):
        return None
    code = marshal.loads(base64.b64decode(EMBEDDED_IMPL_B64.encode("ascii")))
    module = ModuleType("board_audit_hidden_impl")
    module.__file__ = "<embedded_board_audit_impl>"
    exec(code, module.__dict__)
    return module


class ProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _relay(self, method: str) -> None:
        try:
            if method == "GET":
                response = requests.get(
                    f"{INTERNAL_URL}{self.path}",
                    timeout=30,
                )
            else:
                content_length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(content_length) if content_length else b""
                response = requests.post(
                    f"{INTERNAL_URL}{self.path}",
                    data=body,
                    headers={"Content-Type": self.headers.get("Content-Type", "application/json")},
                    timeout=60,
                )
        except requests.RequestException as exc:
            self._send_json(
                {"error": "board-audit internal service unavailable", "detail": str(exc)},
                status=502,
            )
            return

        payload = response.content
        self.send_response(response.status_code)
        self.send_header(
            "Content-Type",
            response.headers.get("Content-Type", "application/json"),
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._relay("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._relay("POST")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    if LOCAL_IMPL_PATH.exists():
        module = _load_impl_from_path(LOCAL_IMPL_PATH)
        module.PORT = PORT
        module.main()
        return

    embedded_module = _load_embedded_impl()
    if embedded_module is not None:
        embedded_module.PORT = PORT
        embedded_module.main()
        return

    if FALLBACK_IMPL_PATH.exists():
        module = _load_impl_from_path(FALLBACK_IMPL_PATH)
        module.PORT = PORT
        module.main()
        return

    server = ThreadingHTTPServer(("0.0.0.0", PORT), ProxyHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
