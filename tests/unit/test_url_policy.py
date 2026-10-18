import pytest

from studio.url_policy import UrlPolicyError, accept_base_url


def test_loopback_accepts_without_confirm_and_adds_v1():
    assert accept_base_url("http://127.0.0.1:11434", confirmed=False) == "http://127.0.0.1:11434/v1"


def test_loopback_keeps_a_single_v1_suffix():
    assert accept_base_url("http://127.0.0.1:11434/v1/", confirmed=False) == "http://127.0.0.1:11434/v1"


def test_localhost_is_loopback():
    assert accept_base_url("http://localhost:11434/v1", confirmed=False) == "http://localhost:11434/v1"


def test_private_network_requires_confirm():
    raw = "http://192.168.1.20:11434/v1"
    with pytest.raises(UrlPolicyError):
        accept_base_url(raw, confirmed=False)
    assert accept_base_url(raw, confirmed=True) == raw


def test_openai_cloud_is_rejected_even_when_confirmed():
    with pytest.raises(UrlPolicyError):
        accept_base_url("https://api.openai.com/v1", confirmed=True)
