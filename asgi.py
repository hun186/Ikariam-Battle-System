from __future__ import annotations

from http import HTTPStatus
import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from web_simulator import run_battle
from ikariam_battle import ScenarioError, UnitRegistry

ROOT = Path(__file__).resolve().parent
INDEX_FILE = ROOT / "index.html"


async def _send_response(
    send,
    status: HTTPStatus,
    body: bytes = b"",
    headers: list[tuple[str, str]] | None = None,
) -> None:
    response_headers = [("content-length", str(len(body)))]
    if headers:
        response_headers.extend(headers)

    await send(
        {
            "type": "http.response.start",
            "status": status.value,
            "headers": [
                (name.encode("latin-1"), value.encode("latin-1"))
                for name, value in response_headers
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _json_response(send, status: HTTPStatus, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    await _send_response(
        send,
        status,
        body,
        [
            ("content-type", "application/json"),
            ("access-control-allow-origin", "*"),
        ],
    )


async def _text_response(send, status: HTTPStatus, message: str) -> None:
    await _send_response(
        send,
        status,
        message.encode("utf-8"),
        [
            ("content-type", "text/plain; charset=utf-8"),
            ("access-control-allow-origin", "*"),
        ],
    )


async def _read_request_body(receive) -> bytes:
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        event = await receive()
        if event["type"] != "http.request":
            continue
        chunks.append(event.get("body", b""))
        more_body = event.get("more_body", False)
    return b"".join(chunks)


async def _api_simulate(scope, receive, send) -> None:
    method = scope["method"].upper()
    if method == "OPTIONS":
        await _send_response(
            send,
            HTTPStatus.NO_CONTENT,
            headers=[
                ("access-control-allow-origin", "*"),
                ("access-control-allow-methods", "GET, POST, OPTIONS"),
                ("access-control-allow-headers", "Content-Type"),
            ],
        )
        return

    if method == "GET":
        await _json_response(
            send,
            HTTPStatus.OK,
            {
                "message": "Use POST /api/simulate to run battle simulation.",
                "docs": "Send a typed scenario with attacker.units and defender.units.",
                "units": UnitRegistry.load().public(),
            },
        )
        return

    if method != "POST":
        await _text_response(send, HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")
        return

    try:
        payload = json.loads((await _read_request_body(receive)).decode("utf-8"))
        await _json_response(send, HTTPStatus.OK, run_battle(payload))
    except (ScenarioError, ValueError, json.JSONDecodeError) as exc:
        await _json_response(send, HTTPStatus.BAD_REQUEST, {"error": str(exc)})


def _resolve_static_path(path: str) -> Path:
    if path == "/":
        return INDEX_FILE

    relative = unquote(path.lstrip("/"))
    candidate = (ROOT / relative).resolve()
    if ROOT not in candidate.parents and candidate != ROOT:
        return INDEX_FILE
    if candidate.is_file():
        return candidate
    return INDEX_FILE


async def _static_file_response(scope, send, file_path: Path) -> None:
    content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = file_path.read_bytes()
    if scope["method"].upper() == "HEAD":
        body = b""
    await _send_response(send, HTTPStatus.OK, body, [("content-type", content_type)])


async def _lifespan(receive, send) -> None:
    while True:
        event = await receive()
        if event["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif event["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def application(scope, receive, send) -> None:
    if scope["type"] == "lifespan":
        await _lifespan(receive, send)
        return

    if scope["type"] != "http":
        return

    path = scope.get("path", "/").rstrip("/") or "/"
    method = scope["method"].upper()

    if path == "/api/simulate":
        await _api_simulate(scope, receive, send)
        return

    if method not in {"GET", "HEAD"}:
        await _text_response(send, HTTPStatus.NOT_FOUND, "Not found")
        return

    await _static_file_response(scope, send, _resolve_static_path(path))
