"""HTTP with bounded retries. Retries only on configured statuses and timeouts."""
import logging
import time
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

import requests

log = logging.getLogger("http")


class RetriesExhausted(RuntimeError):
    pass


def _retry_after_seconds(value):
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        try:
            return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return None


def get_json(session, url, params, http_cfg, sleep=time.sleep):
    """GET url and return (parsed JSON, raw bytes). Raises RetriesExhausted or RuntimeError."""
    retries = http_cfg["max_retries"]
    retry_statuses = set(http_cfg["retry_statuses"])
    timeout = (http_cfg["timeout_connect_s"], http_cfg["timeout_read_s"])
    for attempt in range(retries + 1):
        reason = None
        try:
            resp = session.get(url, params=params, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError) as exc:
            reason, resp = f"{type(exc).__name__}: {exc}", None
        if resp is not None:
            if resp.status_code in retry_statuses:
                reason = f"HTTP {resp.status_code}"
            elif resp.status_code >= 400:
                raise RuntimeError(f"HTTP {resp.status_code} (not retryable) for {url} params={params}: {resp.text[:500]}")
            else:
                return resp.json(), resp.content
        if attempt == retries:
            raise RetriesExhausted(f"gave up after {retries} retries: {reason} url={url} params={params}")
        delay = http_cfg["backoff_base_s"] * (2 ** attempt)
        server_hint = _retry_after_seconds(resp.headers.get("Retry-After")) if resp is not None else None
        if server_hint is not None:
            delay = max(delay, server_hint)
        log.warning("retry %d/%d in %.1fs: %s", attempt + 1, retries, delay, reason)
        sleep(delay)
