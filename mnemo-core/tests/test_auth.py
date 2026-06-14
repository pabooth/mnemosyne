import pytest

from mnemo_core.auth import auth_is_configured, bearer_token_is_valid
from mnemo_core.config import Settings


def test_auth_not_configured_when_token_empty():
    cfg = Settings(mnemo_api_token="")
    assert auth_is_configured(cfg) is False


def test_auth_configured_when_token_set():
    cfg = Settings(mnemo_api_token="secret")
    assert auth_is_configured(cfg) is True


def test_valid_bearer_token():
    cfg = Settings(mnemo_api_token="test-secret")
    assert bearer_token_is_valid("Bearer test-secret", cfg) is True


def test_invalid_bearer_token():
    cfg = Settings(mnemo_api_token="test-secret")
    assert bearer_token_is_valid("Bearer wrong", cfg) is False


def test_missing_authorization_header():
    cfg = Settings(mnemo_api_token="test-secret")
    assert bearer_token_is_valid(None, cfg) is False


def test_wrong_auth_scheme():
    cfg = Settings(mnemo_api_token="test-secret")
    assert bearer_token_is_valid("Basic test-secret", cfg) is False
