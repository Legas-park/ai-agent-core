"""웹훅 게이트웨이 — GitHub HMAC 서명 검증."""
import hashlib
import hmac
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from core.plugin_manager import PluginManager
from routers import webhook


def _github_signature(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def _mock_request(headers: dict):
    request = MagicMock()
    request.headers.get = lambda key, default="": headers.get(key, default)
    return request


@pytest.fixture
def webhook_secret(monkeypatch):
    monkeypatch.setattr(webhook.settings, "webhook_secret", "test-webhook-secret")


def test_github_hmac_valid(webhook_secret):
    body = b'{"action":"opened","pull_request":{"number":1}}'
    sig = _github_signature(body, "test-webhook-secret")
    request = _mock_request({"X-Hub-Signature-256": sig})
    webhook._verify_signature(request, body)


def test_github_hmac_invalid(webhook_secret):
    body = b'{"action":"opened"}'
    request = _mock_request({"X-Hub-Signature-256": "sha256=deadbeef"})
    with pytest.raises(HTTPException) as exc:
        webhook._verify_signature(request, body)
    assert exc.value.status_code == 401


def test_gitlab_token_header_valid(webhook_secret):
    body = b'{"object_kind":"merge_request"}'
    request = _mock_request({"X-Gitlab-Token": "test-webhook-secret"})
    webhook._verify_signature(request, body)


def test_skips_verification_when_secret_empty(monkeypatch):
    monkeypatch.setattr(webhook.settings, "webhook_secret", "")
    body = b'{"action":"opened"}'
    request = _mock_request({})
    webhook._verify_signature(request, body)


def test_github_pr_payload_routes_to_code_review():
    manager = PluginManager()
    manager.load_plugins()
    payload = {
        "action": "opened",
        "pull_request": {"number": 99, "title": "t", "head": {"ref": "feat/x"}},
        "repository": {"full_name": "Legas-park/ai-agent-core"},
    }
    plugin = manager.get_handler_for_payload(payload)
    assert plugin is not None
    assert plugin.name == "code_review_service"
