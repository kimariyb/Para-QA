"""QAC: publication-grade QA dataset construction from cleaned NMR literature.

Orchestration is built on LangChain (prompts, structured output) and LangGraph
(per-unit state graph: generate -> deterministic QC -> LLM verification ->
round-trip). Domain rules (evidence extraction, hygiene, grounding, dedup,
document-level splitting, reporting) are plain functions so they stay
testable and framework-agnostic.

Pipeline
--------
1. Evidence units: heading-aware sections from cleaned Markdown (verbatim text).
2. Candidate generation: LLM proposes typed, difficulty-labelled QA pairs that
   must include a verbatim ``evidence_span`` copied from the passage.
3. Deterministic QC: language, question/answer hygiene, and evidence grounding
   (the span must really occur in the passage).
4. LLM verification (independent calls): answerability + support + self-
   containment verdict, and a round-trip re-answering agreement check.
5. Deduplication: exact-normalized + near-duplicate token Jaccard.
6. Document-level train/dev/test split (no paper appears in two splits) with
   stratification and leakage report.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Literal, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, START, StateGraph
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    BadRequestError,
    InternalServerError,
    LengthFinishReasonError,
    RateLimitError,
)
from pydantic import BaseModel
from src.qac.llm import extract_json

# ---------------------------------------------------------------------------
# Schemas (structured LLM output)
# ---------------------------------------------------------------------------

QType = Literal["factoid", "reasoning", "comparison", "methodological", "quantitative"]
Difficulty = Literal["easy", "medium", "hard"]
QTYPES: tuple[str, ...] = QType.__args__  # type: ignore[attr-defined]
DIFFICULTIES: tuple[str, ...] = Difficulty.__args__  # type: ignore[attr-defined]


class QACandidate(BaseModel):
    question: str
    answer: str
    evidence_span: str
    qtype: QType
    difficulty: Difficulty


class QACandidateBatch(BaseModel):
    items: list[QACandidate]


class Verdict(BaseModel):
    answerable: bool
    supported: bool
    self_contained: bool
    reason: str


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class QACConfig:
    min_chars: int = 200
    max_chars: int = 1500
    candidates_per_unit: int = 3
    evidence_match_threshold: float = 0.85
    verify_with_llm: bool = True
    roundtrip_check: bool = True
    roundtrip_min_f1: float = 0.4
    jaccard_threshold: float = 0.8
    train_ratio: float = 0.7
    dev_ratio: float = 0.1
    seed: int = 42
    request_interval: float = 0.0  # seconds of pacing before each LLM call (rate limits)


# ---------------------------------------------------------------------------
# Evidence units
# ---------------------------------------------------------------------------

_HEADING = re.compile(r"^#{1,6}\s+(.*)$")

# Author/affiliation blocks: affiliation markers ([a], [ab], \*) and no sentence.
_AUTHOR_BLOCK = re.compile(r"(\[[a-z]{1,2}\]|\\\*)")


def _looks_like_author_block(paragraph: str) -> bool:
    markers = len(_AUTHOR_BLOCK.findall(paragraph))
    sentences = paragraph.count(". ") + paragraph.count(".\n")
    return markers >= 3 and sentences <= 1


@dataclass
class EvidenceUnit:
    doc_id: str
    section: str
    text: str
    unit_id: str = ""
    source_start: int = -1
    source_end: int = -1


def extract_evidence_units(
    md_text: str, doc_id: str, min_chars: int = 200, max_chars: int = 1500
) -> list[EvidenceUnit]:
    """Split a cleaned Markdown paper into heading-aware evidence units.

    Paragraphs are grouped under their nearest heading; oversized sections are
    split at paragraph boundaries, undersized trailing pieces are merged into
    the previous unit. Units always contain verbatim paper text.
    """
    sections: list[tuple[str, list[str]]] = []
    heading = "Front matter"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        if buf:
            sections.append((heading, buf))
            buf = []

    for block in re.split(r"\n\s*\n", md_text):
        block = block.strip()
        if not block:
            continue
        match = _HEADING.match(block)
        if match:
            flush()
            heading = match.group(1).strip() or "Untitled"
        elif not _looks_like_author_block(block):
            buf.append(block)
    flush()

    units: list[EvidenceUnit] = []
    for section, paragraphs in sections:
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para
            if current and len(candidate) > max_chars:
                units.append(EvidenceUnit(doc_id, section, current))
                current = para
            else:
                current = candidate
        if current:
            if (
                units
                and len(current) < min_chars
                and units[-1].doc_id == doc_id
                and units[-1].section == section
            ):
                units[-1].text = f"{units[-1].text}\n\n{current}"
            else:
                units.append(EvidenceUnit(doc_id, section, current))

    # Drop units that are still too short (e.g. title-only front matter).
    kept = [u for u in units if len(u.text) >= min_chars]
    resolved: list[EvidenceUnit] = []
    cursor = 0
    for unit in kept:
        start = md_text.find(unit.text, cursor)
        if start < 0:
            continue
        unit.unit_id = f"{doc_id}:unit:{len(resolved) + 1:04d}"
        unit.source_start = start
        unit.source_end = start + len(unit.text)
        cursor = unit.source_end
        resolved.append(unit)
    return resolved


# ---------------------------------------------------------------------------
# Prompts (LangChain templates)
# ---------------------------------------------------------------------------

GENERATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an expert annotator building a question-answering "
            "benchmark for nuclear magnetic resonance (NMR) research literature.",
        ),
        (
            "user",
            """Below is one evidence passage from an NMR research paper.

<passage>
{passage}
</passage>

Create up to {k} question-answer pairs about this passage. Rules:
1. Every question must be SELF-CONTAINED: understandable without the paper. \
Never mention "this paper", "this passage", "the authors", or figure/table/scheme numbers.
2. The answer must be fully supported by the passage alone. Do not use outside knowledge.
3. "evidence_span" must be copied VERBATIM (word for word) from the passage - \
the exact sentence(s) supporting the answer.
4. Vary the question type across: {types}. Pick what the passage naturally supports.
5. Label difficulty: easy = direct lookup of one fact; medium = requires \
understanding one concept or relationship; hard = requires connecting \
multiple facts from the passage.
6. Answers: concise (one phrase to three sentences). No yes/no-only answers.""",
        ),
    ]
)

VERIFICATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a strict QA-benchmark judge. Verify candidate "
            "question-answer pairs against an evidence passage.",
        ),
        (
            "user",
            """<passage>
{passage}
</passage>

Candidate:
Question: {question}
Answer: {answer}

Judge three things:
1. answerable - can the question be answered using ONLY the passage?
2. supported - is every factual claim in the answer entailed by the passage \
(no outside knowledge, no exaggeration)?
3. self_contained - is the question understandable without the source paper \
(no "this paper", no figure/table references)?""",
        ),
    ]
)

ROUNDTRIP_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer the question using only the provided passage. Be concise. "
            "If the passage does not contain the answer, reply exactly: UNANSWERABLE.",
        ),
        ("user", "<passage>\n{passage}\n</passage>\n\nQuestion: {question}"),
    ]
)


# ---------------------------------------------------------------------------
# Deterministic QC (pure functions)
# ---------------------------------------------------------------------------

_CJK = re.compile(r"[一-鿿㐀-䶿豈-﫿]")
_SELF_REFERENCE = re.compile(
    r"\b(this|the present|our)\s+(paper|study|work|article|review)\b"
    r"|\bthe authors\b|\bwe (present|report|describe|show)\b"
    r"|\bfigures?\s+s?\d|\btables?\s+s?\d|\bschemes?\s+\d|\beq\.?\s*\(",
    re.IGNORECASE,
)
_WORD = re.compile(r"[a-z0-9]+")

_STOPWORDS = frozenset(
    "a an the is are was were be been being of in on at to for with by from as "
    "and or but not no it its this that these those which what who whom when "
    "where why how do does did can could will would should may might than then "
    "so such into over under between about against during using used use via".split()
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _content_tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.lower()) if t not in _STOPWORDS}


def hygiene_errors(question: str, answer: str) -> list[str]:
    errors = []
    q_words = question.split()
    if not 5 <= len(q_words) <= 40:
        errors.append("question length")
    if not question.rstrip().endswith("?"):
        errors.append("question mark")
    if _SELF_REFERENCE.search(question):
        errors.append("self-reference")
    if not 1 <= len(answer.split()) <= 120:
        errors.append("answer length")
    if _CJK.search(question) or _CJK.search(answer):
        errors.append("non-English")
    if answer.strip().lower() in {"yes", "no", "yes.", "no.", "nan", "none", "n/a"}:
        errors.append("trivial answer")
    return errors


def grounding_ratio(evidence_span: str, passage: str) -> float:
    """Char-level ratio of the span that actually occurs in the passage."""
    span = _norm(evidence_span)
    text = _norm(passage)
    if not span:
        return 0.0
    if span in text:
        return 1.0
    matcher = SequenceMatcher(None, span, text, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(span)


def token_f1(a: str, b: str) -> float:
    ta, tb = _content_tokens(a), _content_tokens(b)
    if not ta or not tb:
        return 0.0
    overlap = len(ta & tb)
    if not overlap:
        return 0.0
    precision, recall = overlap / len(ta), overlap / len(tb)
    return 2 * precision * recall / (precision + recall)


# ---------------------------------------------------------------------------
# LangGraph orchestration
# ---------------------------------------------------------------------------


class UnitState(TypedDict, total=False):
    unit: EvidenceUnit
    candidates: list[dict[str, Any]]
    funnel: dict[str, int]


@dataclass
class Pipeline:
    """Per-document driver around a compiled per-unit LangGraph."""

    model: BaseChatModel | None
    config: QACConfig = field(default_factory=QACConfig)
    verifier: BaseChatModel | None = None
    callbacks: list[Any] = field(default_factory=list)
    provenance: dict[str, str] = field(default_factory=dict)
    funnel: Counter = field(default_factory=Counter)

    def __post_init__(self) -> None:
        if self.verifier is None:
            self.verifier = self.model
        self.graph = self._build_graph()

    # -- graph ---------------------------------------------------------------

    def _build_graph(self):
        graph = StateGraph(UnitState)
        graph.add_node("generate", self._generate_node)
        graph.add_node("det_qc", self._det_qc_node)
        graph.add_edge(START, "generate")
        graph.add_edge("generate", "det_qc")
        previous = "det_qc"
        if self.config.verify_with_llm:
            graph.add_node("verify", self._verify_node)
            graph.add_edge(previous, "verify")
            previous = "verify"
        if self.config.roundtrip_check:
            graph.add_node("roundtrip", self._roundtrip_node)
            graph.add_edge(previous, "roundtrip")
            previous = "roundtrip"
        graph.add_edge(previous, END)
        return graph.compile()

    # -- LLM robustness -----------------------------------------------------
    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(
            exc,
            (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError),
        ):
            return True
        if isinstance(exc, APIStatusError):
            return getattr(exc, "status_code", None) in (429, 500, 502, 503, 504)
        return False

    @staticmethod
    def _retry_delay(exc: Exception, attempt: int) -> float:
        resp = getattr(exc, "response", None)
        if resp is not None:
            ra = resp.headers.get("Retry-After")
            if ra and ra.isdigit():
                return float(ra) + 0.5
        return min(2.0 ** attempt, 30.0)

    def _invoke_with_retry(self, chain, inputs: dict, max_attempts: int = 6):
        if self.config.request_interval > 0:
            time.sleep(self.config.request_interval)
        last: Exception | None = None
        for attempt in range(max_attempts):
            try:
                return chain.invoke(inputs, config={"callbacks": self.callbacks})
            except Exception as exc:  # noqa: BLE001
                last = exc
                if not self._is_retryable(exc):
                    raise
                if attempt == max_attempts - 1:
                    raise
                time.sleep(self._retry_delay(exc, attempt))
        assert last is not None
        raise last

    def _call_structured(self, model, prompt, schema, inputs):
        """Portable structured-output call across OpenAI-compatible endpoints.

        Forces generic ``response_format={"type": "json_object"}`` via
        ``model.bind`` and parses the JSON ourselves with ``extract_json``
        plus Pydantic validation. This deliberately avoids LangChain's
        auto-selected OpenAI-only ``.parse()`` SDK path
        (``with_structured_output(method="json_mode")`` in some
        langchain-openai versions), which endpoints such as kimi-k2 do
        not support and which hangs. Works on OpenAI, DeepSeek, Qwen,
        vLLM, Ollama, Moonshot.
        """
        bound = model.bind(response_format={"type": "json_object"})
        chain = prompt | bound
        try:
            msg = self._invoke_with_retry(chain, inputs)
        except LengthFinishReasonError as exc:
            raise ValueError(
                "LLM output was truncated (LengthFinishReasonError). "
                "For reasoning models such as kimi-k2, raise the token "
                "budget (QAC_LLM_MAX_TOKENS). QAC generation defaults to "
                "QAC_LLM_REASONING_EFFORT=none to disable thinking mode."
            ) from exc
        data = extract_json(msg.content)
        return schema.model_validate(data)

    # -- graph nodes ---------------------------------------------------------
    def _generate_node(self, state: UnitState) -> dict[str, Any]:
        assert self.model is not None
        unit = state["unit"]
        batch = self._call_structured(
            self.model,
            GENERATION_PROMPT,
            QACandidateBatch,
            {
                "passage": unit.text,
                "k": self.config.candidates_per_unit,
                "types": ", ".join(QTYPES),
            },
        )
        items = [dict(c.model_dump(), _unit=unit) for c in batch.items]
        self.funnel["generated"] += len(items)
        return {"candidates": items}

    def _det_qc_node(self, state: UnitState) -> dict[str, Any]:
        kept: list[dict[str, Any]] = []
        for item in state["candidates"]:
            errors = hygiene_errors(item["question"], item["answer"])
            unit: EvidenceUnit = item["_unit"]
            ratio = grounding_ratio(item["evidence_span"], unit.text)
            if ratio < self.config.evidence_match_threshold:
                errors.append(f"grounding {ratio:.2f}")
            span_start = unit.text.find(item["evidence_span"])
            if span_start < 0:
                errors.append("evidence offset")
            if errors:
                self.funnel[f"drop_{errors[0].split()[0]}"] += 1
            else:
                item["_evidence_start"] = unit.source_start + span_start
                item["_evidence_end"] = item["_evidence_start"] + len(item["evidence_span"])
                kept.append(item)
        self.funnel["after_deterministic_qc"] += len(kept)
        return {"candidates": kept}

    def _verify_node(self, state: UnitState) -> dict[str, Any]:
        kept: list[dict[str, Any]] = []
        for item in state["candidates"]:
            unit: EvidenceUnit = item["_unit"]
            verdict: Verdict = self._call_structured(
                self.verifier,
                VERIFICATION_PROMPT,
                Verdict,
                {
                    "passage": unit.text,
                    "question": item["question"],
                    "answer": item["answer"],
                },
            )
            item["_verdict_reason"] = verdict.reason
            if verdict.answerable and verdict.supported and verdict.self_contained:
                kept.append(item)
            else:
                self.funnel["drop_verification"] += 1
        return {"candidates": kept}

    def _roundtrip_node(self, state: UnitState) -> dict[str, Any]:
        chain = ROUNDTRIP_PROMPT | self.verifier | StrOutputParser()
        kept: list[dict[str, Any]] = []
        for item in state["candidates"]:
            unit: EvidenceUnit = item["_unit"]
            reply = self._invoke_with_retry(
                chain, {"passage": unit.text, "question": item["question"]}
            )
            if "UNANSWERABLE" in reply:
                self.funnel["drop_roundtrip"] += 1
                continue
            f1 = token_f1(item["answer"], reply)
            if f1 >= self.config.roundtrip_min_f1:
                item["_roundtrip_f1"] = round(f1, 3)
                kept.append(item)
            else:
                self.funnel["drop_roundtrip"] += 1
        return {"candidates": kept}


    # -- dedup ------------------------------------------------------------------

    @staticmethod
    def _qkey(question: str) -> str:
        return hashlib.md5(_norm(question).encode()).hexdigest()

    def deduplicate(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        kept: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        seen_tokens: list[set[str]] = []
        for record in records:
            key = self._qkey(record["question"])
            if key in seen_keys:
                self.funnel["dedup_exact"] += 1
                continue
            tokens = _content_tokens(record["question"])
            is_dup = False
            for prev in seen_tokens:
                union = len(tokens | prev)
                if union and len(tokens & prev) / union >= self.config.jaccard_threshold:
                    self.funnel["dedup_near"] += 1
                    is_dup = True
                    break
            if is_dup:
                continue
            seen_keys.add(key)
            seen_tokens.append(tokens)
            kept.append(record)
        return kept

    # -- split -----------------------------------------------------------------

    def split_by_document(
        self, records: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Greedy document-level split: no paper appears in two splits."""
        rng = random.Random(self.config.seed)
        by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            by_doc[record["doc_id"]].append(record)

        docs = list(by_doc)
        rng.shuffle(docs)
        targets = {
            "train": self.config.train_ratio,
            "dev": self.config.dev_ratio,
            "test": 1 - self.config.train_ratio - self.config.dev_ratio,
        }
        splits: dict[str, list[dict[str, Any]]] = {"train": [], "dev": [], "test": []}
        total = len(records)
        for doc in sorted(docs, key=lambda d: -len(by_doc[d])):
            # Assign to the split furthest below its target share.
            name = min(
                targets,
                key=lambda n: (len(splits[n]) + len(by_doc[doc])) / max(total, 1) - targets[n],
            )
            splits[name].extend(by_doc[doc])
        return splits

    # -- driver -------------------------------------------------------------------

    def process_document(self, md_text: str, doc_id: str) -> list[dict[str, Any]]:
        units = extract_evidence_units(
            md_text, doc_id, self.config.min_chars, self.config.max_chars
        )
        self.funnel["evidence_units"] += len(units)
        source_sha256 = hashlib.sha256(md_text.encode("utf-8")).hexdigest()
        records = []
        for i, unit in enumerate(units, 1):
            state = self.graph.invoke({"unit": unit, "candidates": [], "funnel": {}})
            self.funnel.update(state.get("funnel", {}))
            recs = [self._to_record(item, source_sha256) for item in state.get("candidates", [])]
            records.extend(recs)
            print(
                f"  [{doc_id}] unit {i}/{len(units)} -> {len(recs)} recs "
                f"(total {len(records)})",
                flush=True,
            )
        return records

    def _to_record(self, item: dict[str, Any], source_sha256: str) -> dict[str, Any]:
        unit: EvidenceUnit = item["_unit"]
        record = {
            "question": item["question"].strip(),
            "answer": item["answer"].strip(),
            "context": unit.text,
            "evidence_unit_id": unit.unit_id,
            "context_start": unit.source_start,
            "context_end": unit.source_end,
            "evidence_span": item["evidence_span"].strip(),
            "evidence_start": item["_evidence_start"],
            "evidence_end": item["_evidence_end"],
            "source_sha256": source_sha256,
            "qtype": item["qtype"],
            "difficulty": item["difficulty"],
            "doc_id": unit.doc_id,
            "section": unit.section,
        }
        record.update(self.provenance)
        if "_verdict_reason" in item:
            record["verifier_reason"] = item["_verdict_reason"]
        if "_roundtrip_f1" in item:
            record["roundtrip_f1"] = item["_roundtrip_f1"]
        return record


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def leakage_report(splits: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    doc_sets = {name: {r["doc_id"] for r in recs} for name, recs in splits.items()}
    doc_overlap = {
        f"{a}∩{b}": len(doc_sets[a] & doc_sets[b])
        for i, a in enumerate(splits)
        for b in list(splits)[i + 1 :]
    }

    def trigrams(text: str) -> set[tuple[str, ...]]:
        tokens = _WORD.findall(text.lower())
        return {tuple(tokens[i : i + 3]) for i in range(len(tokens) - 2)}

    max_q_overlap = 0.0
    train_grams = [trigrams(r["question"]) for r in splits.get("train", [])]
    for split_name in ("dev", "test"):
        for record in splits.get(split_name, []):
            grams = trigrams(record["question"])
            if not grams:
                continue
            for other in train_grams:
                union = len(grams | other)
                if union:
                    max_q_overlap = max(max_q_overlap, len(grams & other) / union)
    return {"doc_overlap": doc_overlap, "max_train_test_question_trigram_jaccard": round(max_q_overlap, 4)}


def distribution_report(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(records),
        "by_qtype": dict(Counter(r["qtype"] for r in records)),
        "by_difficulty": dict(Counter(r["difficulty"] for r in records)),
        "docs": len({r["doc_id"] for r in records}),
        "question_words_mean": round(
            sum(len(r["question"].split()) for r in records) / max(len(records), 1), 1
        ),
        "answer_words_mean": round(
            sum(len(r["answer"].split()) for r in records) / max(len(records), 1), 1
        ),
    }


def build_report(
    splits: dict[str, list[dict[str, Any]]],
    funnel: Counter,
    generator_model: str,
    verifier_model: str,
    config: QACConfig,
) -> dict[str, Any]:
    return {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "generator_model": generator_model,
        "verifier_model": verifier_model,
        "config": vars(config),
        "funnel": dict(funnel),
        "splits": {name: distribution_report(recs) for name, recs in splits.items()},
        "leakage": leakage_report(splits),
    }


def write_splits(
    splits: dict[str, list[dict[str, Any]]], outdir: Path, prefix: str = "qac"
) -> dict[str, str]:
    outdir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, records in splits.items():
        path = outdir / f"{prefix}_{name}.jsonl"
        with path.open("w", encoding="utf-8") as fh:
            for i, record in enumerate(records):
                record = {"id": f"{prefix}-{name}-{i:05d}", **record}
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        paths[name] = str(path)
    all_path = outdir / f"{prefix}_all.jsonl"
    with all_path.open("w", encoding="utf-8") as fh:
        for name, records in splits.items():
            for record in records:
                fh.write(json.dumps({"split": name, **record}, ensure_ascii=False) + "\n")
    paths["all"] = str(all_path)
    return paths
