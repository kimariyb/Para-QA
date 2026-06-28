from collections.abc import Iterable
from pathlib import Path

from tqdm import tqdm


DEFAULT_STOP_HEADINGS = (
    "# AUTHOR INFORMATION",
    "# Supporting Information",
    "# A. Supplementary data",
    "# Appendix A. Supplementary data",
    "# Appendix A. Supplementary material",
    "# Supplementary materials",
    "# ASSOCIATED CONTENT",
    "# ACKNOWLEDGMENTS",
    "# Acknowledgements",
    "# Conflict of Interest",
    "# Author Contributions",
    "# Data Availability Statement",
    "# Data Availability",
    "# ORCID",
    "# References",
    "# REFERENCES",
    "# Notes and references",
    "# Funding",
    "# Declaration of competing interest",
)


class MarkdownProcessor:
    """Remove trailing metadata/reference sections from MinerU Markdown files."""

    def __init__(
        self,
        md_dir: str | Path,
        output_dir: str | Path,
        stop_headings: Iterable[str] | None = None,
    ) -> None:
        self.md_dir = Path(md_dir)
        self.output_dir = Path(output_dir)
        headings = stop_headings if stop_headings is not None else DEFAULT_STOP_HEADINGS
        self.noise_set = {self._normalize_heading(heading) for heading in headings}

    @staticmethod
    def _normalize_heading(line: str) -> str:
        return line.strip().lower()

    def process_md(
        self,
        md_file_name: str | Path,
        output_dir: str | Path | None = None,
    ) -> str:
        output_path_dir = Path(output_dir) if output_dir is not None else self.output_dir
        output_path_dir.mkdir(parents=True, exist_ok=True)

        md_file_path = Path(md_file_name)
        output_path = output_path_dir / f"{md_file_path.stem}_cleaned.md"

        with md_file_path.open("r", encoding="utf-8") as infile, output_path.open(
            "w",
            encoding="utf-8",
        ) as outfile:
            for line in infile:
                if self._normalize_heading(line) in self.noise_set:
                    break
                outfile.write(line)

        return str(output_path)

    def process_md_dir(self) -> list[str]:
        if not self.md_dir.exists():
            raise FileNotFoundError(f"Markdown directory not found: {self.md_dir}")
        if not self.md_dir.is_dir():
            raise NotADirectoryError(f"Markdown input path is not a directory: {self.md_dir}")

        cleaned_md_paths: list[str] = []
        md_files = sorted(self.md_dir.glob("*.md"))
        for md_file_path in tqdm(md_files, desc="Processing MD files"):
            cleaned_md_paths.append(self.process_md(md_file_path, self.output_dir))

        return cleaned_md_paths
