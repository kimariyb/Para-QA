"""CLI for cleaning MinerU-generated Markdown files."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.parser import MarkdownProcessor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean Markdown files by truncating reference and metadata sections.",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processor = MarkdownProcessor(md_dir=args.input, output_dir=args.output)
    cleaned_paths = processor.process_md_dir()
    print(f"Processed {len(cleaned_paths)} Markdown files into {Path(args.output).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
