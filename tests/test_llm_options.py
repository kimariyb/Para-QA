"""Tests for provider-neutral reasoning-mode configuration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.qac.llm import reasoning_options


def test_reasoning_defaults_to_none() -> None:
    assert reasoning_options("TEST_REASONING") == {"reasoning_effort": "none"}


def test_reasoning_accepts_provider_specific_disable_body() -> None:
    import os

    os.environ["TEST_REASONING_REASONING_EFFORT"] = "none"
    os.environ["TEST_REASONING_EXTRA_BODY_JSON"] = '{"thinking":{"type":"disabled"}}'
    try:
        assert reasoning_options("TEST_REASONING")["extra_body"] == {"thinking": {"type": "disabled"}}
    finally:
        del os.environ["TEST_REASONING_REASONING_EFFORT"]
        del os.environ["TEST_REASONING_EXTRA_BODY_JSON"]


def test_reasoning_rejects_unknown_mode() -> None:
    import os

    os.environ["TEST_REASONING_REASONING_EFFORT"] = "off"
    try:
        reasoning_options("TEST_REASONING")
        raise AssertionError("expected invalid reasoning mode")
    except ValueError as exc:
        assert "TEST_REASONING_REASONING_EFFORT" in str(exc)
    finally:
        del os.environ["TEST_REASONING_REASONING_EFFORT"]


if __name__ == "__main__":
    test_reasoning_defaults_to_none()
    test_reasoning_accepts_provider_specific_disable_body()
    test_reasoning_rejects_unknown_mode()
    print("PASS test_llm_options")
