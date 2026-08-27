"""Number and date formatting shared by every renderer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

DASH = "—"


def num(value: Any, decimals: int = 0, suffix: str = "") -> str:
    """Thousands-separated number, or an em dash when the value is missing."""
    if not isinstance(value, (int, float)):
        return DASH
    return f"{value:,.{decimals}f}{suffix}"


def usd(value: Any, decimals: int = 2) -> str:
    """Compact USD: $1.23B / $45.6M / $789.01."""
    if not isinstance(value, (int, float)):
        return DASH
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    for divisor, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= divisor:
            return f"{sign}${magnitude / divisor:,.2f}{unit}"
    return f"{sign}${magnitude:,.{decimals}f}"


def pct(value: Any, decimals: int = 2, signed: bool = False) -> str:
    """Percentage with an optional explicit sign."""
    if not isinstance(value, (int, float)):
        return DASH
    return f"{value:{'+' if signed else ''}.{decimals}f}%"


def sol(value: Any, decimals: int = 0) -> str:
    """SOL amount, abbreviated above a million."""
    if not isinstance(value, (int, float)):
        return DASH
    if abs(value) >= 1e6:
        return f"{value / 1e6:,.2f}M SOL"
    return f"{value:,.{decimals}f} SOL"


def ago(iso_ts: str | None, now: datetime | None = None) -> str:
    """Human relative time such as '4 min ago'."""
    if not iso_ts:
        return DASH
    try:
        moment = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return iso_ts
    delta = ((now or datetime.now(timezone.utc)) - moment).total_seconds()
    if delta < 0:
        return "just now"
    for limit, divisor, unit in ((90, 1, "sec"), (5400, 60, "min"), (172800, 3600, "hr")):
        if delta < limit:
            return f"{int(delta / divisor)} {unit} ago"
    return f"{int(delta / 86400)} d ago"


def short_date(iso_ts: str | None) -> str:
    """Date portion of an ISO timestamp."""
    return iso_ts.split("T")[0] if iso_ts else DASH


def truncate(text: str | None, limit: int) -> str:
    """Truncate with an ellipsis."""
    if not text:
        return ""
    return text if len(text) <= limit else text[: limit - 1] + "…"
