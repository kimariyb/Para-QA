"""Tests for static external-experiment gates."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.preflight import preflight


def test_preflight_accepts_distinct_registered_models(tmp_path: Path) -> None:
    qac, corpus = tmp_path / "qac.jsonl", tmp_path / "corpus.jsonl"
    qac.touch()
    corpus.touch()
    env = {
        "QAC_LLM_BASE_URL": "https://generator.example/v1",
        "QAC_LLM_API_KEY": "generator-key",
        "QAC_LLM_MODEL": "generator",
        "QAC_LLM_VERIFIER_MODEL": "verifier",
        "EVAL_LLM_BASE_URL": "https://answer.example/v1",
        "EVAL_LLM_API_KEY": "answer-key",
        "EVAL_LLM_MODEL": "answerer",
        "JUDGE_LLM_BASE_URL": "https://judge.example/v1",
        "JUDGE_LLM_API_KEY": "judge-key",
        "JUDGE_LLM_MODEL": "judge",
    }
    assert preflight(env, qac, corpus, "study-v1", 20.0) == []


def test_preflight_rejects_missing_budget_and_role_separation(tmp_path: Path) -> None:
    qac, corpus = tmp_path / "qac.jsonl", tmp_path / "corpus.jsonl"
    qac.touch()
    corpus.touch()
    env = {name: "same" for name in (
        "QAC_LLM_BASE_URL", "QAC_LLM_API_KEY", "QAC_LLM_MODEL", "QAC_LLM_VERIFIER_MODEL",
        "EVAL_LLM_BASE_URL", "EVAL_LLM_API_KEY", "EVAL_LLM_MODEL",
        "JUDGE_LLM_BASE_URL", "JUDGE_LLM_API_KEY", "JUDGE_LLM_MODEL",
    )}
    errors = preflight(env, qac, corpus, "study-v1", None)
    assert "a positive external API budget (USD) is required" in errors
    assert "QAC generator and verifier models must be distinct" in errors
    assert "answer model and judge model must be distinct" in errors


def test_preflight_rejects_qac_reasoning_mode(tmp_path: Path) -> None:
    qac, corpus = tmp_path / "qac.jsonl", tmp_path / "corpus.jsonl"
    qac.touch()
    corpus.touch()
    env = {
        "QAC_LLM_BASE_URL": "x", "QAC_LLM_API_KEY": "x", "QAC_LLM_MODEL": "generator",
        "QAC_LLM_VERIFIER_MODEL": "verifier", "EVAL_LLM_BASE_URL": "x",
        "EVAL_LLM_API_KEY": "x", "EVAL_LLM_MODEL": "answerer", "JUDGE_LLM_BASE_URL": "x",
        "JUDGE_LLM_API_KEY": "x", "JUDGE_LLM_MODEL": "judge", "QAC_LLM_REASONING_EFFORT": "low",
    }
    assert "QAC_LLM_REASONING_EFFORT must be none for the registered study" in preflight(
        env, qac, corpus, "study-v1", 20.0
    )


if __name__ == "__main__":
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp_dir:
        test_preflight_accepts_distinct_registered_models(Path(temp_dir))
    print("PASS test_preflight_accepts_distinct_registered_models")
    with TemporaryDirectory() as temp_dir:
        test_preflight_rejects_missing_budget_and_role_separation(Path(temp_dir))
    print("PASS test_preflight_rejects_missing_budget_and_role_separation")
    with TemporaryDirectory() as temp_dir:
        test_preflight_rejects_qac_reasoning_mode(Path(temp_dir))
    print("PASS test_preflight_rejects_qac_reasoning_mode")
