import pytest
import requests

from pipeline.http import RetriesExhausted, get_json

HTTP = {"timeout_connect_s": 1, "timeout_read_s": 1, "max_retries": 3, "backoff_base_s": 2, "retry_statuses": [429, 500]}


class Resp:
    def __init__(self, code, body=b"[]", headers=None):
        self.status_code, self.content, self.headers, self.text = code, body, headers or {}, body.decode()

    def json(self):
        import json
        return json.loads(self.content)


class Session:
    def __init__(self, script):
        self.script, self.calls = list(script), 0

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_retries_429_and_500_then_succeeds():
    sleeps = []
    s = Session([Resp(429, headers={"Retry-After": "5"}), Resp(500), Resp(200, b'[{"a": 1}]')])
    data, raw = get_json(s, "u", {}, HTTP, sleep=sleeps.append)
    assert data == [{"a": 1}] and raw == b'[{"a": 1}]'
    assert sleeps == [5.0, 4]          # Retry-After honoured, then exponential backoff
    assert s.calls == 3


def test_timeout_is_retried():
    s = Session([requests.Timeout("slow"), Resp(200, b"[]")])
    assert get_json(s, "u", {}, HTTP, sleep=lambda _: None)[0] == []


def test_gives_up_after_budget():
    s = Session([Resp(500)] * 4)
    with pytest.raises(RetriesExhausted):
        get_json(s, "u", {}, HTTP, sleep=lambda _: None)
    assert s.calls == 4                # 1 try + 3 retries, bounded


def test_client_error_is_not_retried():
    s = Session([Resp(400, b'{"message": "bad column"}')])
    with pytest.raises(RuntimeError, match="not retryable"):
        get_json(s, "u", {}, HTTP, sleep=lambda _: None)
    assert s.calls == 1
