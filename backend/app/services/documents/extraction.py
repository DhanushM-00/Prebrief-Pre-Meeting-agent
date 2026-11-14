"""Extract text and structure from PDF, DOCX, TXT, CSV, PPTX.

OCR for scanned PDFs is optional and only runs when enable_ocr=True and
pytesseract/pdf2image are available.
"""
from __future__ import annotations

import csv
import io
import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

log = logging.getLogger("prebrief.documents")


@dataclass
class ExtractedBlock:
    text: str
    location_type: str | None = None  # page | slide | sheet | section
    location_label: str | None = None
    heading: str | None = None


@dataclass
class ExtractionResult:
    blocks: list[ExtractedBlock] = field(default_factory=list)
    page_count: int | None = None
    metadata: dict = field(default_factory=dict)
    ocr_used: bool = False
    error: str | None = None

    @property
    def full_text(self) -> str:
        parts = []
        for b in self.blocks:
            if b.heading:
                parts.append(b.heading)
            if b.text:
                parts.append(b.text)
        return "\n\n".join(parts)


def extract_document(path: Path, extension: str, *, enable_ocr: bool = False) -> ExtractionResult:
    ext = extension.lower().lstrip(".")
    try:
        if ext == "pdf":
            return _extract_pdf(path, enable_ocr=enable_ocr)
        if ext == "docx":
            return _extract_docx(path)
        if ext == "pptx":
            return _extract_pptx(path)
        if ext == "txt":
            return _extract_txt(path)
        if ext == "csv":
            return _extract_csv(path)
        return ExtractionResult(error=f"No extractor for .{ext}")
    except Exception as e:
        log.exception("extraction failed for %s", path)
        return ExtractionResult(error=str(e))


def _extract_txt(path: Path) -> ExtractionResult:
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            text = ""
    else:
        text = raw.decode("utf-8", errors="replace")
    blocks = [ExtractedBlock(text=text.strip(), location_type="section", location_label="Document")]
    return ExtractionResult(blocks=blocks, page_count=1, metadata={"encoding": "detected"})


def _extract_csv(path: Path) -> ExtractionResult:
    raw = path.read_text(encoding="utf-8", errors="replace")
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        return ExtractionResult(blocks=[], page_count=0)
    # Render as markdown-ish table for the first sheet
    lines = []
    header = rows[0]
    lines.append(" | ".join(header))
    lines.append(" | ".join("---" for _ in header))
    for row in rows[1:5000]:  # cap rows
        lines.append(" | ".join(row))
    text = "\n".join(lines)
    blocks = [
        ExtractedBlock(
            text=text,
            location_type="sheet",
            location_label="Sheet 1",
            heading="Spreadsheet",
        )
    ]
    return ExtractionResult(
        blocks=blocks,
        page_count=1,
        metadata={"rows": len(rows), "cols": len(header)},
    )


def _extract_pdf(path: Path, *, enable_ocr: bool = False) -> ExtractionResult:
    # Prefer pypdf; fall back to a minimal text scrape if unavailable
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            return ExtractionResult(
                error="PDF support requires pypdf. Install with: pip install pypdf"
            )

    reader = PdfReader(str(path))
    blocks: list[ExtractedBlock] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        label = f"Page {i + 1}"
        if text.strip():
            blocks.append(
                ExtractedBlock(text=text.strip(), location_type="page", location_label=label)
            )
        elif enable_ocr:
            ocr_text = _ocr_pdf_page(path, i)
            if ocr_text:
                blocks.append(
                    ExtractedBlock(
                        text=ocr_text.strip(),
                        location_type="page",
                        location_label=label,
                    )
                )

    ocr_used = enable_ocr and any(True for b in blocks)
    # If no text at all and OCR not enabled, note it
    if not any(b.text.strip() for b in blocks):
        if not enable_ocr:
            return ExtractionResult(
                blocks=blocks,
                page_count=len(reader.pages),
                error="No extractable text found. Enable OCR for scanned PDFs (enable_ocr=true).",
            )
    meta = {}
    if reader.metadata:
        meta = {k: str(v) for k, v in dict(reader.metadata).items() if v}
    return ExtractionResult(
        blocks=blocks,
        page_count=len(reader.pages),
        metadata=meta,
        ocr_used=ocr_used,
    )


def _ocr_pdf_page(path: Path, page_index: int) -> str:
    """Optional OCR path — soft-fails if dependencies missing."""
    try:
        from pdf2image import convert_from_path  # type: ignore
        import pytesseract  # type: ignore
    except ImportError:
        log.warning("OCR requested but pdf2image/pytesseract not installed")
        return ""
    try:
        images = convert_from_path(str(path), first_page=page_index + 1, last_page=page_index + 1)
        if not images:
            return ""
        return pytesseract.image_to_string(images[0]) or ""
    except Exception as e:
        log.warning("OCR failed page %s: %s", page_index, e)
        return ""


# OOXML namespaces
_W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_A_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
_P_NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main"}


def _extract_docx(path: Path) -> ExtractionResult:
    blocks: list[ExtractedBlock] = []
    try:
        with zipfile.ZipFile(path) as zf:
            # document.xml body paragraphs
            xml = zf.read("word/document.xml")
            root = ET.fromstring(xml)
            paras = []
            for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                texts = [
                    t.text or ""
                    for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
                ]
                line = "".join(texts).strip()
                if line:
                    paras.append(line)
            # Detect simple headings (style name contains Heading)
            current_heading = None
            buf: list[str] = []
            for line in paras:
                # Heuristic: short ALL-CAPS or lines ending without period as soft headings
                is_heading = len(line) < 80 and (line.isupper() or not line.endswith((".", "!", "?")))
                if is_heading and len(line.split()) <= 12:
                    if buf:
                        blocks.append(
                            ExtractedBlock(
                                text="\n".join(buf),
                                location_type="section",
                                heading=current_heading,
                            )
                        )
                        buf = []
                    current_heading = line
                else:
                    buf.append(line)
            if buf:
                blocks.append(
                    ExtractedBlock(
                        text="\n".join(buf),
                        location_type="section",
                        heading=current_heading,
                    )
                )
            # Tables
            for tbl in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tbl"):
                rows = []
                for tr in tbl.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tr"):
                    cells = []
                    for tc in tr.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}tc"):
                        cell_text = "".join(
                            t.text or ""
                            for t in tc.iter(
                                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
                            )
                        )
                        cells.append(cell_text.strip())
                    if any(cells):
                        rows.append(" | ".join(cells))
                if rows:
                    blocks.append(
                        ExtractedBlock(
                            text="\n".join(rows),
                            location_type="section",
                            heading="Table",
                        )
                    )
    except KeyError:
        return ExtractionResult(error="Invalid DOCX: missing word/document.xml")
    return ExtractionResult(blocks=blocks, page_count=None, metadata={"format": "docx"})


def _extract_pptx(path: Path) -> ExtractionResult:
    blocks: list[ExtractedBlock] = []
    try:
        with zipfile.ZipFile(path) as zf:
            names = sorted(
                n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")
            )
            for idx, name in enumerate(names):
                xml = zf.read(name)
                root = ET.fromstring(xml)
                texts = []
                for t in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t"):
                    if t.text:
                        texts.append(t.text)
                body = "\n".join(texts).strip()
                if body:
                    blocks.append(
                        ExtractedBlock(
                            text=body,
                            location_type="slide",
                            location_label=f"Slide {idx + 1}",
                            heading=f"Slide {idx + 1}",
                        )
                    )
            return ExtractionResult(
                blocks=blocks, page_count=len(names), metadata={"format": "pptx", "slides": len(names)}
            )
    except Exception as e:
        return ExtractionResult(error=f"PPTX extraction failed: {e}")
