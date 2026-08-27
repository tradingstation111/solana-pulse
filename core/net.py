"""Keyless HTTP access layer built entirely on the Python standard library.

Every outbound request in Solana Pulse goes through :func:`fetch_json`,
:func:`fetch_text` or :func:`rpc_call`.  Those helpers share one policy:

* no API keys, no third-party packages, no persistent credentials;
* bounded retries with exponential backoff on transient failures
  (HTTP 429/5xx, socket timeouts, DNS hiccups);
* a hard byte ceiling so a pathological response cannot exhaust memory;
* structured failures -- a collector never sees an exception it did not ask
  for, it sees a :class:`SourceResult` whose ``ok`` flag is ``False``.

The last point is what makes the report degrade instead of crash.
"""

from __future__ import annotations

import gzip
import json
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

USER_AGENT = "solana-pulse/1.0 (+https://github.com/tradingstation111/solana-pulse)"
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3
MAX_BYTES = 24 * 1024 * 1024  # 24 MiB: a full Solana block with accounts is ~6 MiB

_SSL_CONTEXT = ssl.create_default_context()


def utc_now() -> datetime:
    """Return the current time as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def iso(ts: datetime | None = None) -> str:
    """Format ``ts`` (default: now) as a second-resolution ISO-8601 UTC string."""
    return (ts or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class SourceResult:
    """Outcome of a single data-source fetch.

    ``ok`` False means the section that depends on this source renders a
    visible "source unavailable" note carrying ``error``, rather than
    disappearing or taking the whole run down.
    """

    name: str
    url: str
    ok: bool
    data: Any = None
    error: str | None = None
    elapsed_ms: int = 0
    fetched_at: str = field(default_factory=iso)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the result *without* its payload (payloads go elsewhere)."""
        return {
            "name": self.name,
            "url": self.url,
            "ok": self.ok,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
            "fetched_at": self.fetched_at,
            "notes": self.notes,
        }


class FetchError(RuntimeError):
    """Raised internally when every retry of a request has been exhausted."""


def _read_body(response: Any) -> bytes:
    """Read a response body, transparently gunzipping and capping its size."""
    raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise FetchError(f"response exceeded {MAX_BYTES} byte ceiling")
    if response.headers.get("Content-Encoding", "").lower() == "gzip":
        raw = gzip.decompress(raw)
    return raw


def _request(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> bytes:
    """Perform one HTTP(S) request with retry/backoff. Raises :class:`FetchError`."""
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/xml, application/xml, text/html;q=0.8, */*;q=0.5",
        "Accept-Encoding": "gzip",
    }
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})

    last: Exception | None = None
    for attempt in range(retries):
        if attempt:
            # 0.8s, 2.4s, 7.2s -- long enough for CoinGecko's per-minute bucket
            # to refill without stalling the whole run.
            time.sleep(0.8 * (3**(attempt - 1)))
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs)
            with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
                return _read_body(resp)
        except urllib.error.HTTPError as exc:  # noqa: PERF203 - retry policy differs per class
            detail = ""
            try:
                detail = exc.read(400).decode("utf-8", "replace").strip().replace("\n", " ")
            except Exception:  # pragma: no cover - body already consumed
                pass
            last = FetchError(f"HTTP {exc.code} {exc.reason}{': ' + detail if detail else ''}")
            if exc.code in (429, 500, 502, 503, 504, 522, 524):
                continue
            break  # 4xx other than 429 will not fix itself
        except (urllib.error.URLError, socket.timeout, ssl.SSLError, OSError) as exc:
            last = FetchError(f"{type(exc).__name__}: {exc}")
            continue
        except FetchError as exc:
            last = exc
            break
    raise last if isinstance(last, FetchError) else FetchError(str(last))


def guarded(name: str, url: str, fn: Callable[[], Any], notes: list[str] | None = None) -> SourceResult:
    """Run ``fn`` and wrap its outcome in a :class:`SourceResult`.

    This is the single choke point for source-level fault isolation: any
    exception raised while fetching *or parsing* a source is converted into a
    failed result, so one broken upstream degrades exactly one section.
    """
    start = time.time()
    try:
        data = fn()
        return SourceResult(
            name=name, url=url, ok=True, data=data,
            elapsed_ms=int((time.time() - start) * 1000), notes=list(notes or []),
        )
    except Exception as exc:  # noqa: BLE001 - deliberate catch-all at the boundary
        message = f"{type(exc).__name__}: {exc}"
        return SourceResult(
            name=name, url=url, ok=False, error=message[:400],
            elapsed_ms=int((time.time() - start) * 1000), notes=list(notes or []),
        )


def fetch_json(url: str, *, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> Any:
    """GET ``url`` and decode the body as JSON."""
    return json.loads(_request(url, timeout=timeout, retries=retries))


def fetch_text(url: str, *, timeout: float = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES) -> str:
    """GET ``url`` and decode the body as UTF-8 text (lenient)."""
    return _request(url, timeout=timeout, retries=retries).decode("utf-8", "replace")


def rpc_post(endpoint: str, method: str, params: list[Any] | None = None,
             *, timeout: float = DEFAULT_TIMEOUT, retries: int = 2) -> Any:
    """Send one JSON-RPC 2.0 call to ``endpoint`` and return its ``result``."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}).encode()
    payload = json.loads(_request(endpoint, data=body, timeout=timeout, retries=retries))
    if isinstance(payload, dict) and payload.get("error"):
        err = payload["error"]
        raise FetchError(f"rpc error {err.get('code')}: {err.get('message')}")
    return payload.get("result") if isinstance(payload, dict) else payload
