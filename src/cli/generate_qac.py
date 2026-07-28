"""CLI for the QAC dataset construction pipeline (LangChain + LangGraph).

Examples
--------
Dry-run (offline, deterministic fake model, validates the full pipeline):

    python scripts/generate_qac.py --dry-run --limit 5

Real run (requires QAC_LLM_BASE_URL / QAC_LLM_API_KEY / QAC_LLM_MODEL):

    python scripts/generate_qac.py --limit 100
"""

import argparse
import json
import os
import hashlib
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from dotenv import load_dotenv

from src.qac.llm import PassageFakeChatModel, UsageTracker, build_chat_model, reasoning_options
from src.qac.generation import (
    GENERATION_PROMPT,
    Pipeline,
    QACConfig,
    build_report,
    write_splits,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a publication-grade QAC dataset from cleaned Markdown.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-i", "--input", default="data/cleaned",
                        help="Directory of cleaned Markdown files.")
    parser.add_argument("-o", "--outdir", default="outputs/qac",
                        help="Output directory for JSONL splits and report.")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only the first N documents.")
    parser.add_argument("--per-unit", type=int, default=3,
                        help="Candidate QA pairs requested per evidence unit.")
    parser.add_argument("--min-chars", type=int, default=200)
    parser.add_argument("--max-chars", type=int, default=1500)
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip the independent LLM verification call.")
    parser.add_argument("--no-roundtrip", action="store_true",
                        help="Skip the round-trip re-answering check.")
    parser.add_argument("--verifier-model", default=None,
                        help="Use a different model for verification "
                             "(defaults to the generator model).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--pace", type=float, default=0.0,
                        help="Seconds to wait before each LLM call (pace under "
                             "provider rate limits, e.g. Moonshot free tier: 1.2).")
    parser.add_argument("--temperature", type=float, default=None,
                        help="Override generation/verifier temperature (some "
                             "models, e.g. kimi-k2, only allow 1).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use the deterministic fake model (offline, for testing).")
    parser.add_argument("--run-id", default=None,
                        help="Stable identifier recorded in every generated QAC item.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_dotenv(PROJECT_ROOT / ".env")

    # --temperature overrides the per-endpoint env so generator and verifier agree.
    if args.temperature is not None:
        os.environ["QAC_LLM_TEMPERATURE"] = str(args.temperature)
    # QAC labels must be generated without a hidden reasoning budget so the
    # recorded answer is the complete model output available to the evaluator.
    os.environ["QAC_LLM_REASONING_EFFORT"] = "none"

    usage = UsageTracker()
    if args.dry_run:
        generator = verifier = PassageFakeChatModel()
        generator_name = verifier_name = "passage-fake"
    else:
        generator = build_chat_model(env_prefix="QAC_LLM", temperature=0.7)
        generator_name = getattr(generator, "model_name", None) or os.environ.get(
            "QAC_LLM_MODEL", "unknown"
        )
        # Verifier: --verifier-model flag > QAC_LLM_VERIFIER_MODEL env > generator.
        verifier_model_name = args.verifier_model or os.environ.get(
            "QAC_LLM_VERIFIER_MODEL"
        )
        if verifier_model_name:
            verifier = build_chat_model(
                model=verifier_model_name, env_prefix="QAC_LLM", temperature=0.0
            )
            verifier_name = verifier_model_name
        else:
            verifier = generator
            verifier_name = generator_name

    config = QACConfig(
        min_chars=args.min_chars,
        max_chars=args.max_chars,
        candidates_per_unit=args.per_unit,
        verify_with_llm=not args.no_verify,
        roundtrip_check=not args.no_roundtrip,
        seed=args.seed,
        request_interval=args.pace,
    )
    config_hash = hashlib.sha256(
        json.dumps(vars(config), sort_keys=True).encode("utf-8")
    ).hexdigest()
    prompt_hash = hashlib.sha256(
        str(GENERATION_PROMPT.messages).encode("utf-8")
    ).hexdigest()
    run_id = args.run_id or time.strftime("qac-%Y%m%d-%H%M%S")
    pipeline = Pipeline(
        model=generator,
        verifier=verifier,
        config=config,
        callbacks=[usage],
        provenance={
            "run_id": run_id,
            "generator_model": str(generator_name),
            "verifier_model": str(verifier_name),
            "config_sha256": config_hash,
            "generation_prompt_sha256": prompt_hash,
            "reasoning_effort": reasoning_options()["reasoning_effort"],
            "extra_body_sha256": hashlib.sha256(
                json.dumps(reasoning_options(), sort_keys=True).encode("utf-8")
            ).hexdigest(),
        },
    )

    md_dir = Path(args.input)
    md_files = sorted(md_dir.glob("*.md"))
    if args.limit:
        md_files = md_files[: args.limit]
    if not md_files:
        print(f"No markdown files found in {md_dir}")
        return 1

    all_records: list[dict] = []
    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = out_dir / "qac_raw.jsonl"
    # Incremental checkpoint: even if the run is killed (rate limits / timeout),
    # the raw records produced so far are preserved.
    with raw_path.open("w", encoding="utf-8") as raw_fh:
        for md_file in md_files:
            doc_id = md_file.stem.replace("_cleaned", "")
            records = pipeline.process_document(
                md_file.read_text(encoding="utf-8"), doc_id
            )
            for record in records:
                raw_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            raw_fh.flush()
            all_records.extend(records)
            print(f"{doc_id}: {len(records)} records (total {len(all_records)})")

    kept = pipeline.deduplicate(all_records)
    splits = pipeline.split_by_document(kept)
    paths = write_splits(splits, Path(args.outdir))

    report = build_report(splits, pipeline.funnel, generator_name, verifier_name, config)
    report_path = Path(args.outdir) / "qac_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nKept {len(kept)}/{len(all_records)} records after dedup.")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    print(f"Report: {report_path}")
    print(f"LLM calls: {usage.calls} (tokens in/out: "
          f"{usage.input_tokens}/{usage.output_tokens})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
