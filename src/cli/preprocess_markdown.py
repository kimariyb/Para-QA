"""CLI for cleaning MinerU-generated Markdown files."""

import argparse
import json
from pathlib import Path

from src.ingestion.markdown import MarkdownProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Clean Markdown files: truncate reference sections, drop metadata "
            "sections (acknowledgements, author info, funding, conflicts, "
            "data availability, supporting info, ...), and remove reference "
            "blobs, keyword/received/copyright/watermark lines and page artifacts."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        default="data/markdown",
        help="Directory containing raw Markdown files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="data/cleaned",
        help="Directory for cleaned Markdown files.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional path to write a JSON cleaning report (per-rule counts).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processor = MarkdownProcessor(md_dir=args.input, output_dir=args.output)
    cleaned_paths = processor.process_md_dir()

    stats = dict(processor.stats)
    chars_in = stats.get("chars_in", 0)
    chars_out = stats.get("chars_out", 0)
    reduction = (1 - chars_out / chars_in) * 100 if chars_in else 0.0

    print(f"Processed {len(cleaned_paths)} Markdown files into {Path(args.output).resolve()}")
    print(f"Size: {chars_in:,} -> {chars_out:,} chars ({reduction:.1f}% removed)")
    print("Rule counts:")
    for key, value in sorted(stats.items(), key=lambda item: -item[1]):
        if key.startswith("chars_") or key == "files":
            continue
        print(f"  {key:<28} {value}")

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"files": len(cleaned_paths), "reduction_pct": reduction, **stats}, indent=2),
            encoding="utf-8",
        )
        print(f"Report written to {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
