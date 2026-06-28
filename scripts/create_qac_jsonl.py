"""Merge Dify-generated QAC JSONL shards into one cleaned dataset."""

import argparse
import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

CHINESE_PATTERN = re.compile(
    r"["
    r"\u4e00-\u9fff"
    r"\u3400-\u4dbf"
    r"\U00020000-\U0002a6df"
    r"\U0002a700-\U0002b73f"
    r"\U0002b740-\U0002b81f"
    r"\U0002b820-\U0002ceaf"
    r"\uf900-\ufaff"
    r"]"
)

INVALID_TEXT_MARKERS = ("NaN", "None")


def contains_chinese_deep(
    data: Any,
    chinese_pattern: re.Pattern[str] = CHINESE_PATTERN,
) -> bool:
    """Recursively check whether any nested value contains Chinese characters."""
    if isinstance(data, str):
        return chinese_pattern.search(data) is not None

    if isinstance(data, dict):
        return any(contains_chinese_deep(value, chinese_pattern) for value in data.values())

    if isinstance(data, (list, tuple)):
        return any(contains_chinese_deep(item, chinese_pattern) for item in data)

    return False


def iter_jsonl_data(file_path: str | Path) -> Iterator[dict[str, Any]]:
    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped_line = line.strip()
            if not stripped_line:
                continue
            if any(marker in stripped_line for marker in INVALID_TEXT_MARKERS):
                continue

            try:
                json_obj = json.loads(stripped_line)
            except json.JSONDecodeError as exc:
                print(f"Skipping invalid JSON in {path}:{line_number}: {exc}")
                continue

            if contains_chinese_deep(json_obj):
                continue

            yield json_obj


def get_jsonl_data(file_path: str | Path) -> list[dict[str, Any]]:
    return list(iter_jsonl_data(file_path))


def merge_jsonl_data(file_paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    paths = [Path(file_path) for file_path in file_paths]
    for file_path in paths:
        data.extend(iter_jsonl_data(file_path))
    print(f"Merged {len(paths)} JSONL files with {len(data)} valid records.")
    return data


def collect_jsonl_files(input_dir: str | Path) -> list[Path]:
    path = Path(input_dir)
    if not path.exists():
        raise FileNotFoundError(f"Input directory not found: {path}")
    if not path.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {path}")

    files = sorted(path.glob("*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No .jsonl files found in: {path}")
    return files


def write_jsonl(records: Iterable[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge cleaned QAC JSONL shards into a single JSONL dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-i",
        "--input",
        default="qac_jsonls",
        help="Directory containing JSONL shards.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="qac.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    if output_path.exists() and not args.overwrite:
        print(f"{output_path} already exists. Use --overwrite to regenerate it.")
        return 0

    files = collect_jsonl_files(args.input)
    records = merge_jsonl_data(files)
    write_jsonl(records, output_path)
    print(f"Wrote {len(records)} records to {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
