"""Static gates for a registered external-model experiment run."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping


REQUIRED_ROLES = ("QAC_LLM_MODEL", "QAC_LLM_VERIFIER_MODEL", "EVAL_LLM_MODEL", "JUDGE_LLM_MODEL")


def preflight(
    env: Mapping[str, str], qac_path: Path, corpus_path: Path, run_id: str, budget_usd: float | None
) -> list[str]:
    """Return all conditions that must be fixed before an external run starts."""
    errors: list[str] = []
    if not run_id.strip():
        errors.append("run_id is required")
    if budget_usd is None or budget_usd <= 0:
        errors.append("a positive external API budget (USD) is required")
    for prefix in ("QAC_LLM", "EVAL_LLM", "JUDGE_LLM"):
        if not env.get(f"{prefix}_BASE_URL", "").strip():
            errors.append(f"{prefix}_BASE_URL is required")
        if not env.get(f"{prefix}_API_KEY", "").strip():
            errors.append(f"{prefix}_API_KEY is required")
    for role in REQUIRED_ROLES:
        if not env.get(role, "").strip():
            errors.append(f"{role} is required")
    if env.get("QAC_LLM_REASONING_EFFORT", "none").strip().lower() != "none":
        errors.append("QAC_LLM_REASONING_EFFORT must be none for the registered study")
    if env.get("QAC_LLM_MODEL") == env.get("QAC_LLM_VERIFIER_MODEL"):
        errors.append("QAC generator and verifier models must be distinct")
    if env.get("QAC_LLM_MODEL") == env.get("JUDGE_LLM_MODEL"):
        errors.append("QAC generator and judge models must be distinct")
    if env.get("EVAL_LLM_MODEL") == env.get("JUDGE_LLM_MODEL"):
        errors.append("answer model and judge model must be distinct")
    if not qac_path.is_file():
        errors.append(f"QAC split does not exist: {qac_path}")
    if not corpus_path.is_file():
        errors.append(f"evidence corpus does not exist: {corpus_path}")
    return errors
