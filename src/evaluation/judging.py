"""Structured contracts for independent automated RAG judges."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Verdict = Literal["accept", "reject", "abstain"]


class JudgeVerdict(BaseModel):
    answerable: bool
    evidence_supported: bool
    citation_valid: bool
    verdict: Verdict
    cited_evidence_unit_ids: list[str] = Field(default_factory=list)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_verdict(self) -> "JudgeVerdict":
        if self.verdict == "accept" and not (
            self.answerable and self.evidence_supported and self.citation_valid
        ):
            raise ValueError("accept requires answerable, supported, and valid citation")
        if self.verdict == "abstain" and self.answerable:
            raise ValueError("abstain requires an unanswerable question")
        return self


JUDGE_DIMENSIONS = (
    "answerable",
    "evidence_supported",
    "citation_valid",
    "verdict",
)
