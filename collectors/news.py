"""Ecosystem news, protocol governance and cluster status.

Three keyless streams:

* RSS/Atom feeds parsed with :mod:`xml.etree` from the standard library;
* the GitHub REST API (anonymous, 60 requests/hour) for open and recently
  merged SIMDs and for Agave / Firedancer releases;
* Solana's Statuspage summary for incident history.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree

from core import config
from core.net import FetchError, SourceResult, fetch_json, fetch_text, guarded

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SIMD_RE = re.compile(r"simd[\s\-_]?0*(\d{1,4})", re.IGNORECASE)

_DATE_FORMATS = (
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
)


def clean_text(value: str | None, limit: int = 260) -> str:
    """Strip HTML tags and collapse whitespace, then truncate."""
    if not value:
        return ""
    text = _WS_RE.sub(" ", _TAG_RE.sub(" ", value)).strip()
    return text[: limit - 1] + "…" if len(text) > limit else text


def parse_date(value: str | None) -> str | None:
    """Parse the several date formats feeds use into an ISO-8601 UTC string."""
    if not value:
        return None
    raw = value.strip().replace("GMT", "+0000")
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    try:  # ISO-8601 with fractional seconds or offsets stdlib handles natively
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def parse_feed(xml_text: str, source: str, limit: int = 8) -> list[dict[str, Any]]:
    """Parse an RSS 2.0 or Atom 1.0 document into normalised entries.

    Written against both dialects because Solana's own feed is RSS while
    GitHub's release feeds are Atom.
    """
    root = ElementTree.fromstring(xml_text.strip())
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    entries: list[dict[str, Any]] = []

    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        get = lambda name: item.find(name) if item.find(name) is not None else item.find(f"atom:{name}", ns)  # noqa: E731
        title_el = get("title")
        link_el = get("link")
        link = ""
        if link_el is not None:
            link = (link_el.text or "").strip() or link_el.attrib.get("href", "")
        date_el = None
        for candidate in ("pubDate", "published", "updated", "date"):
            date_el = get(candidate)
            if date_el is not None and (date_el.text or "").strip():
                break
        summary_el = None
        for candidate in ("description", "summary", "content"):
            summary_el = get(candidate)
            if summary_el is not None and (summary_el.text or "").strip():
                break
        entries.append({
            "source": source,
            "title": clean_text(title_el.text if title_el is not None else "", 180),
            "link": link,
            "published": parse_date(date_el.text if date_el is not None else None),
            "summary": clean_text(summary_el.text if summary_el is not None else "", 260),
        })
        if len(entries) >= limit:
            break
    return entries


def collect_news() -> SourceResult:
    """Merge every configured feed into one reverse-chronological list."""

    def run() -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        failures: list[str] = []
        for name, url in config.NEWS_FEEDS:
            try:
                items.extend(parse_feed(fetch_text(url, timeout=40.0), name))
            except Exception as exc:  # noqa: BLE001 - per-feed degradation
                failures.append(f"{name}: {type(exc).__name__} {str(exc)[:100]}")
        if not items:
            raise FetchError("every configured feed failed: " + "; ".join(failures))
        items.sort(key=lambda i: i["published"] or "", reverse=True)
        return {
            "items": items[:30],
            "feed_count": len(config.NEWS_FEEDS),
            "failed_feeds": failures,
            "x_accounts": [{"handle": h, "url": u} for h, u in config.X_ACCOUNTS],
        }

    return guarded(
        "Ecosystem news feeds",
        "RSS/Atom: " + ", ".join(n for n, _ in config.NEWS_FEEDS),
        run,
    )


def _simd_number(title: str) -> int | None:
    """Extract the SIMD number from a pull-request title, if it has one."""
    match = _SIMD_RE.search(title or "")
    return int(match.group(1)) if match else None


def parse_simd_pulls(open_pulls: list[dict[str, Any]], closed_pulls: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn GitHub pull-request payloads into a governance view.

    Pure function so the SIMD logic is unit-tested from a fixture.
    """
    def norm(pull: dict[str, Any], state: str) -> dict[str, Any]:
        title = pull.get("title") or ""
        labels = [lbl.get("name") for lbl in (pull.get("labels") or []) if lbl.get("name")]
        return {
            "number": pull.get("number"),
            "simd": _simd_number(title),
            "title": clean_text(title, 160),
            "state": "merged" if state == "closed" and pull.get("merged_at") else state,
            "url": pull.get("html_url"),
            "author": (pull.get("user") or {}).get("login"),
            "created_at": parse_date(pull.get("created_at")),
            "updated_at": parse_date(pull.get("updated_at")),
            "merged_at": parse_date(pull.get("merged_at")),
            "labels": labels,
            "highlight": any(k in title.lower() for k in config.HIGHLIGHT_SIMDS),
        }

    opened = [norm(p, "open") for p in open_pulls]
    closed = [norm(p, "closed") for p in closed_pulls]
    merged = [p for p in closed if p["state"] == "merged"]
    opened.sort(key=lambda p: p["updated_at"] or "", reverse=True)
    merged.sort(key=lambda p: p["merged_at"] or "", reverse=True)
    highlights = [p for p in opened + merged if p["highlight"]]
    return {
        "open_count": len(opened),
        "open": opened[:20],
        "recently_merged": merged[:12],
        "highlighted": highlights[:10],
        "highlight_keywords": list(config.HIGHLIGHT_SIMDS),
    }


def collect_simds() -> SourceResult:
    """Open and recently merged Solana Improvement Documents."""

    def run() -> dict[str, Any]:
        open_pulls = fetch_json(config.GITHUB_SIMD_OPEN, timeout=40.0)
        try:
            closed_pulls = fetch_json(config.GITHUB_SIMD_CLOSED, timeout=40.0)
        except Exception:  # noqa: BLE001 - open PRs alone are still useful
            closed_pulls = []
        return parse_simd_pulls(open_pulls, closed_pulls)

    return guarded("GitHub: SIMD proposals", config.GITHUB_SIMD_OPEN, run)


def parse_proposal_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn the proposals directory listing into an accepted-SIMD view.

    Answers a question the pull-request list cannot: which proposals have
    actually been accepted, and where do the named upgrades everyone is
    waiting on currently stand.
    """
    documents = []
    for entry in entries:
        name = entry.get("name") or ""
        if not name.endswith(".md") or entry.get("type") != "file":
            continue
        number, _, stem = name[:-3].partition("-")
        documents.append({
            "file": name,
            "stem": stem,
            "simd": int(number) if number.isdigit() else None,
            "title": stem.replace("-", " ").replace("_", " ").strip().capitalize(),
            "url": entry.get("html_url"),
            "size_bytes": entry.get("size"),
        })
    documents.sort(key=lambda d: d["simd"] if d["simd"] is not None else -1, reverse=True)

    tracked = []
    for label, needle, why in config.TRACKED_UPGRADES:
        # Exact stem match first; a substring match is only a fallback, so
        # "alpenglow" resolves to 0326-alpenglow and never to a longer name
        # that merely contains it.
        match = (next((d for d in documents if d["stem"].lower() == needle), None)
                 or next((d for d in documents if needle in d["stem"].lower()), None))
        tracked.append({
            "label": label,
            "why": why,
            "accepted": match is not None,
            "simd": match["simd"] if match else None,
            "url": match["url"] if match else None,
            "file": match["file"] if match else None,
        })
    return {
        "accepted_count": len(documents),
        "accepted_recent": documents[:12],
        "tracked_upgrades": tracked,
    }


def collect_accepted_simds() -> SourceResult:
    """Accepted SIMD documents and the status of the named upgrades."""

    def run() -> dict[str, Any]:
        return parse_proposal_index(fetch_json(config.GITHUB_SIMD_PROPOSALS, timeout=40.0))

    return guarded("GitHub: accepted SIMDs", config.GITHUB_SIMD_PROPOSALS, run)


def collect_client_releases() -> SourceResult:
    """Latest published releases for each validator client implementation."""

    def run() -> dict[str, Any]:
        repos: list[dict[str, Any]] = []
        failures: list[str] = []
        for label, url in config.GITHUB_RELEASES:
            try:
                releases = fetch_json(url, timeout=40.0)
                rows = [{
                    "tag": r.get("tag_name"),
                    "name": clean_text(r.get("name"), 120),
                    "published": parse_date(r.get("published_at")),
                    "prerelease": bool(r.get("prerelease")),
                    "url": r.get("html_url"),
                } for r in (releases or [])[:5]]
                stable = next((r for r in rows if not r["prerelease"]), rows[0] if rows else None)
                repos.append({"client": label, "latest_stable": stable, "releases": rows})
            except Exception as exc:  # noqa: BLE001 - per-repo degradation
                failures.append(f"{label}: {type(exc).__name__} {str(exc)[:100]}")
        if not repos:
            raise FetchError("no release feeds reachable: " + "; ".join(failures))
        return {"clients": repos, "failed": failures}

    return guarded("GitHub: client releases", config.GITHUB_RELEASES[0][1], run)


def collect_status() -> SourceResult:
    """Solana Statuspage: component states and recent incidents."""

    def run() -> dict[str, Any]:
        payload = fetch_json(config.STATUS_PAGE, timeout=30.0)
        components = [
            {"name": c.get("name"), "status": c.get("status")}
            for c in (payload.get("components") or [])
            if not c.get("group")
        ]
        incidents = [{
            "name": clean_text(i.get("name"), 140),
            "status": i.get("status"),
            "impact": i.get("impact"),
            "created_at": parse_date(i.get("created_at")),
            "url": i.get("shortlink"),
        } for i in (payload.get("incidents") or [])[:5]]
        overall = payload.get("status") or {}
        return {
            "indicator": overall.get("indicator"),
            "description": overall.get("description"),
            "components": components[:12],
            "degraded_components": [c for c in components if c["status"] != "operational"],
            "incidents": incidents,
            "updated_at": parse_date((payload.get("page") or {}).get("updated_at")),
        }

    return guarded("Solana Statuspage", config.STATUS_PAGE, run)
