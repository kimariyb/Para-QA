"""Clean MinerU-generated Markdown files for downstream RAG/QAC pipelines.

Strategy (three heading levels + paragraph-level rules):

1. Terminal headings (References etc.) -> truncate the rest of the file.
2. Drop-section headings (Acknowledgements, author info, funding, ...) -> drop
   only that section, resuming at the next heading. This is safe for sidebar
   sections like ARTICLE INFO that appear at the *start* of Elsevier papers.
3. Drop-heading-only headings (ACCESS, Check for updates, ...) -> remove the
   heading itself but keep the content (rescues abstracts trapped under ACS
   web sidebars, e.g. CONSPECTUS paragraphs).
4. Paragraph rules: reference blobs without headings, keyword lines,
   received/accepted dates, DOI/URL lines, copyright lines, download
   watermarks, page artifacts, image embeds, journal-citation footers.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Heading rules (matched against the *normalized* heading text, fullmatch)
# ---------------------------------------------------------------------------

#: Headings after which nothing worth keeping exists -> stop processing.
TERMINAL_HEADINGS: frozenset[str] = frozenset(
    {
        "references",
        "bibliography",
        "notes and references",
        "references and notes",
        "literature cited",
    }
)

#: Sections whose whole content is metadata noise -> drop until next heading.
DROP_SECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern)
    for pattern in (
        r"acknowledg\w*",
        r"author information",
        r"author contributions?",
        r"author declarations?",
        r"credit authorship contribution statement",
        r"corresponding authors?",
        r"authors?",
        r"affiliations?",
        r"orcid",
        r"biographies",
        r"notes",
        r"associated content",
        r".*supporting information.*",
        r"supplementary\w*.*",
        r"appendix.*supplementar\w*.*",
        r"conflicts? of interests?( statement)?",
        r"competing interests?",
        r"declaration of competing interest",
        r"key references",
        r"data availability( statement)?",
        r"data and code availability",
        r"funding( information)?",
        r"keywords?",
        r"article ?info",
        r"articles? you may be interested in",
        r"article recommendations",
        r"(j )?recommended by acs",
        r"abbreviations?",
        r"correspondence",
        r"additional information",
        r"ethics( declarations?)?",
        r"peer review",
        r"publishers? note",
    )
)

#: Sidebar/running headings: drop the heading line only, keep the content.
DROP_HEADING_ONLY: frozenset[str] = frozenset(
    {
        "access",
        "check for updates",
        "read online",
        "contents",
        "metrics & more",
        "scientific reports",  # running header of the journal
        "download pdf",
    }
)

# ---------------------------------------------------------------------------
# Paragraph rules
# ---------------------------------------------------------------------------

# Citation shapes used to spot reference lists: "2009, 323, 1708" (year, vol,
# page) and "124, 201109 (2006)" (vol, page (year)).
_CITE_YEAR_FIRST = re.compile(r"(?:19|20)\d\d\s*,\s*\d{1,4}\s*,\s*\d+")
_CITE_YEAR_LAST = re.compile(r"\b\d{1,4}\s*,\s*\d[\d-]*\s*\((?:19|20)\d\d\)")
_REF_MARKER = re.compile(r"\[\d+\]")

_IMAGE_ONLY = re.compile(r"^!\[[^\]]*\]\([^)]*\)\s*$")
_KEYWORDS = re.compile(r"^keywords?\s*[:：]", re.IGNORECASE)
_RECEIVED = re.compile(
    r"^(received|revised|accepted|published( online)?|submitted|"
    r"manuscript received|first published)\b",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://")
_DOI = re.compile(r"doi\.org", re.IGNORECASE)
_COPYRIGHT = re.compile(
    r"(protected by copyright|all rights reserved|this journal is ©|"
    r"©\s*(?:19|20)\d\d|copyright\s*©|creativecommons\.org|"
    r"this is an open access article|distributed under the terms)",
    re.IGNORECASE,
)
_WATERMARK = re.compile(
    r"(downloaded (by|from|via)|ip address \d)", re.IGNORECASE
)
_PAGE_ARTIFACT = re.compile(
    r"^(\d{1,4}|page \d+ of \d+|\(\d+ of \d+\))$", re.IGNORECASE
)
_ABSTRACT_RESCUE = re.compile(r"^(conspectus|abstract)\s*[:：]", re.IGNORECASE)

#: Short label lines left behind by ACS web sidebars.
_JUNK_LABELS: frozenset[str] = frozenset(
    {
        "metrics & more",
        "article recommendations",
        "read online",
        "check for updates",
        "download pdf",
    }
)

_HEADING = re.compile(r"^#{1,6}\s*(.*)$")
_MATH = re.compile(r"\$[^$]*\$")
_NUM_PREFIX = re.compile(
    r"^\s*(?:\d+|[ivxlcdmIVXLCDM]{1,4})\s*[.):|\-–—]\s*"
    r"|^\s*(?:\d+|[ivxlcdmIVXLCDM]{1,4})\s+"
)


def normalize_heading(text: str) -> str:
    """Normalize a heading for rule matching.

    Strips markdown '#', LaTeX math junk (e.g. ``$\\bullet$``), and leading
    section numbering (``1.``, ``2.1.``, ``IV.``, ``1 |``).
    """
    text = _HEADING.match(text.strip()).group(1) if _HEADING.match(text.strip()) else text
    text = _MATH.sub(" ", text)
    text = re.sub(r"[^\w\s&'/\-]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    # Peel leading numbering tokens one by one: "2.1. X" -> "1. X" -> "X".
    while True:
        stripped = _NUM_PREFIX.sub("", text, count=1)
        if stripped == text or not stripped:
            break
        text = stripped.strip()
    return text.lower()


def _citation_hits(text: str) -> int:
    return len(_CITE_YEAR_FIRST.findall(text)) + len(_CITE_YEAR_LAST.findall(text))


def looks_like_reference_block(text: str) -> bool:
    """Detect reference-list paragraphs, including heading-less blobs."""
    hits = _citation_hits(text)
    if hits >= 3:
        return True
    markers = len(_REF_MARKER.findall(text))
    if hits >= 2 and markers >= 1:
        return True
    # "[12] Author, ... 2009, 323, 1708. [13] ..." with a single visible hit.
    if re.match(r"^\s*\[\d+\]", text) and markers >= 2 and hits >= 1:
        return True
    return False


def split_blocks(text: str) -> list[str]:
    """Split markdown into blocks: blank-line paragraphs + standalone headings."""
    blocks: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            blocks.append("\n".join(buf))
            buf.clear()

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            flush()
        elif line.lstrip().startswith("#"):
            flush()
            blocks.append(line.strip())
        else:
            buf.append(line)
    flush()
    return blocks


class MarkdownProcessor:
    """Remove metadata/reference noise from MinerU Markdown files."""

    def __init__(
        self,
        md_dir: str | Path,
        output_dir: str | Path,
        stop_headings: Iterable[str] | None = None,
    ) -> None:
        self.md_dir = Path(md_dir)
        self.output_dir = Path(output_dir)
        # Backward compatibility: caller-supplied headings become terminal.
        self.terminal_headings = set(TERMINAL_HEADINGS)
        if stop_headings:
            self.terminal_headings.update(
                normalize_heading(h) for h in stop_headings
            )
        self.stats: Counter[str] = Counter()

    # -- block classification ------------------------------------------------

    def _classify_heading(self, block: str, title_norm: str | None) -> str:
        norm = normalize_heading(block)
        if not norm:
            return "empty_heading"
        if norm in self.terminal_headings:
            return "terminal"
        # Copyright/license statements OCR'd as headings.
        if len(block) < 300 and _COPYRIGHT.search(block):
            return "copyright_heading"
        if any(p.fullmatch(norm) for p in DROP_SECTION_PATTERNS):
            return "drop_section"
        if norm in DROP_HEADING_ONLY:
            return "drop_heading"
        # Running header: repeats the paper title on later pages.
        if title_norm and norm == title_norm:
            return "drop_heading_title"
        return "keep"

    def _classify_paragraph(self, block: str) -> str:
        lines = block.splitlines()
        stripped = block.strip()
        if looks_like_reference_block(stripped):
            return "ref_blob"
        if _KEYWORDS.match(stripped):
            return "keywords"
        if len(stripped) < 300 and _RECEIVED.match(stripped):
            return "received"
        if len(stripped) < 200 and (_DOI.search(stripped) or _URL.match(stripped)):
            return "doi_url"
        if len(stripped) < 400 and _COPYRIGHT.search(stripped):
            return "copyright"
        if len(stripped) < 300 and _WATERMARK.search(stripped):
            return "watermark"
        if len(lines) == 1 and _PAGE_ARTIFACT.match(stripped):
            return "page_artifact"
        if len(lines) == 1 and normalize_heading(stripped) in _JUNK_LABELS:
            return "junk_label"
        # Single-line journal-citation footer, e.g. running page footers.
        if len(lines) == 1 and len(stripped) < 150 and _citation_hits(stripped) >= 1:
            return "footer_cite"
        return "keep"

    # -- public API ------------------------------------------------------------

    def clean_text(self, text: str) -> str:
        """Clean a single markdown document, returning the filtered text."""
        blocks = split_blocks(text)
        title_norm: str | None = None
        for block in blocks:
            if block.lstrip().startswith("#"):
                title_norm = normalize_heading(block)
                break

        kept: list[str] = []
        dropping = False
        title_seen = False
        for block in blocks:
            if block.lstrip().startswith("#"):
                # The first heading *is* the title; only later repeats are
                # running headers.
                is_first_heading = not title_seen
                title_seen = True
                action = self._classify_heading(
                    block, None if is_first_heading else title_norm
                )
                if action == "terminal":
                    self.stats["terminal_cut"] += 1
                    break
                if action == "drop_section":
                    self.stats["section_dropped"] += 1
                    dropping = True
                    continue
                dropping = False
                if action in (
                    "drop_heading",
                    "drop_heading_title",
                    "empty_heading",
                    "copyright_heading",
                ):
                    self.stats[action] += 1
                    continue
                kept.append(block)
                continue

            if dropping:
                # Rescue abstracts trapped inside metadata sidebars.
                if _ABSTRACT_RESCUE.match(block.strip()):
                    kept.append(block)
                    self.stats["abstract_rescued"] += 1
                else:
                    self.stats["paragraph_dropped_with_section"] += 1
                continue

            # Strip image-embed lines but keep captions living in the same
            # paragraph; a block of only images is dropped entirely.
            text_lines = [
                line for line in block.splitlines() if not _IMAGE_ONLY.match(line)
            ]
            self.stats["image_lines"] += len(block.splitlines()) - len(text_lines)
            if not text_lines:
                self.stats["image"] += 1
                continue
            block = "\n".join(text_lines)

            action = self._classify_paragraph(block)
            if action == "keep":
                kept.append(block)
            else:
                self.stats[action] += 1

        return "\n\n".join(kept).strip() + "\n"

    def process_md(
        self,
        md_file_name: str | Path,
        output_dir: str | Path | None = None,
    ) -> str:
        output_path_dir = Path(output_dir) if output_dir is not None else self.output_dir
        output_path_dir.mkdir(parents=True, exist_ok=True)

        md_file_path = Path(md_file_name)
        output_path = output_path_dir / f"{md_file_path.stem}_cleaned.md"

        text = md_file_path.read_text(encoding="utf-8")
        cleaned = self.clean_text(text)
        output_path.write_text(cleaned, encoding="utf-8")

        self.stats["files"] += 1
        self.stats["chars_in"] += len(text)
        self.stats["chars_out"] += len(cleaned)
        if len(cleaned) < 200:
            self.stats["suspiciously_short_files"] += 1

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


# Descriptive alias for new code.
MarkdownCleaner = MarkdownProcessor
