# ruff: noqa: RUF001 -- Chinese product copy intentionally uses Chinese punctuation.
"""Complete source access with native tables/pages and explicit
extraction uncertainty."""

from __future__ import annotations

import hashlib
import io
import math
import re
import threading
from collections.abc import Callable
from html.parser import HTMLParser
from typing import Any

import pdfplumber
import pypdfium2 as pdfium  # type: ignore[import-untyped]
from pypdf import PdfReader

from researchforge.v2.contracts import Json
from researchforge.v2.storage import ResearchRepository

_PDFIUM_LOCK = threading.Lock()


def terms(text: str) -> set[str]:
    lowered = text.casefold()
    result = set(re.findall(r"[a-z0-9][a-z0-9_.-]+", lowered))
    for phrase in re.findall(r"[\u4e00-\u9fff]{2,}", lowered):
        result.update(phrase[index : index + 2] for index in range(len(phrase) - 1))
    return result


_RETRIEVAL_ALIAS_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    ("@occupancy", frozenset({"occupancy", "occupied"})),
    ("@rent", frozenset({"rent", "rents", "rental", "rentals"})),
    (
        "@change",
        frozenset(
            {
                "change",
                "changes",
                "changed",
                "growth",
                "grow",
                "grew",
                "increase",
                "increased",
                "increases",
            }
        ),
    ),
    ("@same_home", frozenset({"same-store", "same-home", "samehome"})),
)


def _retrieval_terms(text: str) -> set[str]:
    """Add a tiny, explicit synonym layer for lexical retrieval only.

    These aliases never become evidence or financial semantics. They only prevent common filing
    wording variants such as ``occupancy``/``occupied`` and ``rental``/``rent`` from hiding a
    native table that otherwise contains the exact row/column evidence the Agent should inspect.
    """

    base = terms(text)
    expanded = set(base)
    for canonical, aliases in _RETRIEVAL_ALIAS_GROUPS:
        if base & aliases:
            expanded.add(canonical)
    return expanded


def _query_centered_snippet(text: str, query_terms: set[str], max_chars: int = 1200) -> str:
    """Return source text around the most query-relevant line, not always byte zero."""

    if len(text) <= max_chars:
        return text
    best_score = 0
    best_offset = 0
    offset = 0
    for line in text.splitlines(keepends=True):
        score = len(query_terms & _retrieval_terms(line))
        if score > best_score:
            best_score = score
            best_offset = offset
        offset += len(line)
    if best_score == 0:
        return text[:max_chars]
    start = max(0, best_offset - max_chars // 3)
    end = min(len(text), start + max_chars)
    start = max(0, end - max_chars)
    start = _token_boundary_start(text, start)
    return text[start:end]


def _token_boundary_start(text: str, start: int, *, max_backtrack: int = 96) -> int:
    """Avoid beginning an extracted evidence slice in the middle of a token.

    Fixed-width filing chunks are an implementation detail, not source semantics. If a chunk
    starts inside ``decreased`` or immediately after the sign in ``-45%``, dropping that prefix
    can invert deterministic numeric provenance even though the filing itself is unambiguous.
    Keep the nominal chunk grid, but backtrack a small bounded distance to the token boundary.
    """

    if start <= 0 or start >= len(text):
        return max(0, min(start, len(text)))

    def token_char(char: str) -> bool:
        return char.isalnum() or char in {"_", "-", "'", "’"}

    if not (token_char(text[start - 1]) and token_char(text[start])):
        return start
    lower_bound = max(0, start - max_backtrack)
    while start > lower_bound and token_char(text[start - 1]):
        start -= 1
    return start


def windows(text: str, size: int = 2200) -> list[tuple[int, str]]:
    chunks: list[tuple[int, str]] = []
    for nominal_start in range(0, len(text), size - 200):
        start = _token_boundary_start(text, nominal_start)
        chunks.append((start, text[start : nominal_start + size]))
    return chunks


def _id(kind: str, document_id: str, *parts: object) -> str:
    return f"{kind}_{document_id.removeprefix('doc_')}_" + "_".join(map(str, parts))


def _object(kind: str, identifier: str, source: Json, text: str, **metadata: Any) -> Json:
    return {
        "artifact_id": identifier,
        "kind": kind,
        "document_id": source["document_id"],
        "text": text,
        "text_hash": hashlib.sha256(text.encode()).hexdigest(),
        "source_uri": source["source_uri"],
        "published_at": source["published_at"],
        "content_role": "untrusted_source",
        **metadata,
    }


def _add_evidence(objects: dict[str, Json], source: Json, page: Json) -> None:
    for index, (offset, text) in enumerate(windows(page["text"]), 1):
        identifier = _id("ev", source["document_id"], page["page_index"], index)
        objects[identifier] = _object(
            "evidence",
            identifier,
            source,
            text,
            page_id=page["artifact_id"],
            page_number=page["page_number"],
            char_start=offset,
            char_end=offset + len(text),
        )


def parse_pdf(
    payload: bytes,
    source: Json,
    *,
    check: Callable[[], None] = lambda: None,
    progress: Callable[[int, int], None] = lambda _done, _total: None,
) -> tuple[dict[str, Json], tuple[str, ...], list[str]]:
    """Preserve all pages; tables/embedded images/footnotes are labeled
    extraction candidates."""
    reader = PdfReader(io.BytesIO(payload))
    if reader.is_encrypted and reader.decrypt("") == 0:
        raise ValueError("encrypted financial filing cannot be read")
    if len(reader.pages) > 1200:
        raise ValueError("document exceeds the 1200-page operational limit")
    native_pages: list[str] = []
    objects: dict[str, Json] = {}
    gaps: list[str] = []
    doc_id = source["document_id"]
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        for index, page in enumerate(pdf.pages, 1):
            check()
            native_text = reader.pages[index - 1].extract_text() or ""
            native_pages.append(native_text)
            text = page.extract_text() or native_text
            page_id = _id("page", doc_id, index)
            page_object = _object(
                "page",
                page_id,
                source,
                text,
                page_index=index,
                page_number=index,
                label=f"P{index}",
                width=float(page.width),
                height=float(page.height),
                raw_blob_id=source["raw_blob_id"],
                table_ids=[],
                figure_ids=[],
                footnote_ids=[],
                extraction_status="native_text" if text.strip() else "image_inspection_required",
                visual_inspection_available=True,
            )
            objects[page_id] = page_object
            if not text.strip():
                gaps.append(f"P{index}: 无可用文本层，须看页面图像；未执行 OCR。")
            try:
                tables = page.find_tables()
            except Exception as exc:
                tables = []
                gaps.append(f"P{index}: 表格结构提取失败 ({type(exc).__name__})，原页仍可读。")
            for table_index, table in enumerate(tables, 1):
                matrix = table.extract()
                if not matrix or not any(any(cell for cell in row) for row in matrix):
                    continue
                table_id = _id("table", doc_id, index, table_index)
                rows = []
                for row_index, row in enumerate(matrix):
                    cells = []
                    boxes = table.rows[row_index].cells
                    for column_index, cell in enumerate(row):
                        box = boxes[column_index]
                        cells.append(
                            {
                                "cell_id": f"{table_id}_r{row_index}_c{column_index}",
                                "row": row_index,
                                "column": column_index,
                                "text": cell,
                                "bbox": list(box) if box else None,
                                "status": "native_candidate"
                                if cell is not None
                                else "merged_or_missing",
                            }
                        )
                    rows.append(cells)
                table_text = "\n".join(
                    " | ".join(cell or "[合并/空白]" for cell in row) for row in matrix
                )
                units = re.findall(
                    r"(?:单位[：:]\s*[^\n]{1,45}|(?:RMB|HK\$|US\$|USD|CNY)[^\n]{0,30})", text
                )
                objects[table_id] = _object(
                    "table",
                    table_id,
                    source,
                    table_text,
                    page_id=page_id,
                    page_number=index,
                    bbox=list(table.bbox),
                    rows=rows,
                    row_count=len(rows),
                    column_count=max(len(row) for row in rows),
                    title=f"P{index} 表格 {table_index}",
                    unit_candidates=units,
                    header_status="requires_review",
                    extraction_status="structure_extracted_not_financially_verified",
                    footnote_ids=[],
                )
                page_object["table_ids"].append(table_id)
            for image_index, image in enumerate(page.images, 1):
                figure_id = _id("figure", doc_id, index, image_index)
                objects[figure_id] = _object(
                    "figure",
                    figure_id,
                    source,
                    f"P{index} 内嵌图像 {image_index}，内容尚未分类。",
                    page_id=page_id,
                    page_number=index,
                    bbox=[float(image[key]) for key in ("x0", "top", "x1", "bottom")],
                    extraction_status="embedded_image_unclassified",
                    requires_visual_inspection=True,
                )
                page_object["figure_ids"].append(figure_id)
            lines = text.splitlines()
            for line_index, line in enumerate(lines):
                if not re.match(
                    r"^\s*(?:注[：:（(\d一二三四五六七八九]|Notes?\s*[:\d])", line, re.I
                ):
                    continue
                footnote_id = _id("footnote", doc_id, index, line_index)
                objects[footnote_id] = _object(
                    "footnote",
                    footnote_id,
                    source,
                    "\n".join(lines[line_index : line_index + 5]),
                    page_id=page_id,
                    page_number=index,
                    extraction_status="heuristic_candidate",
                    related_table_ids=list(page_object["table_ids"]),
                    relation_status="same_page_only",
                )
                page_object["footnote_ids"].append(footnote_id)
            for table_id in page_object["table_ids"]:
                objects[table_id]["footnote_ids"] = list(page_object["footnote_ids"])
            _add_evidence(objects, source, page_object)
            if index == 1 or index % 10 == 0 or index == len(pdf.pages):
                progress(index, len(pdf.pages))
            page.close()
    # Native PDF bookmarks, where available, are navigable section boundaries.
    bookmarks: list[tuple[int, str]] = []

    def walk(items: list[Any]) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
            else:
                try:
                    destination_index = reader.get_destination_page_number(item)
                    if destination_index is None:
                        continue
                    page_number = destination_index + 1
                    if 1 <= page_number <= len(native_pages):
                        bookmarks.append((page_number, str(item.title)))
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue

    walk(reader.outline)
    bookmarks = sorted(set(bookmarks))
    for index, (start, title) in enumerate(bookmarks):
        end = bookmarks[index + 1][0] - 1 if index + 1 < len(bookmarks) else len(native_pages)
        end = max(start, end)
        identifier = _id("section", doc_id, index + 1)
        objects[identifier] = _object(
            "section",
            identifier,
            source,
            "\n".join(native_pages[start - 1 : end]),
            title=title,
            page_start=start,
            page_end=end,
            page_id=_id("page", doc_id, start),
            extraction_status="pdf_bookmark",
            page_number=start,
        )
    gaps.append(
        "表格/脚注为原生提取候选；跨页合并、无框线表格及矢量图未保证自动识别完整，可回原页核查。"
    )
    return objects, tuple(native_pages), gaps


class FilingHTMLParser(HTMLParser):
    """Visible text plus native HTML cell boundaries; never executes source
    markup."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.tables: list[list[list[Json]]] = []
        self.table_contexts: list[str] = []
        self.headings: list[str] = []
        self._hidden = 0
        self._table_depth = 0
        self._rows: list[list[Json]] = []
        self._row: list[Json] = []
        self._cell: Json | None = None
        self._heading: list[str] | None = None
        self._table_context: str = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attributes = dict(attrs)
        if tag in {"script", "style", "noscript", "ix:hidden"}:
            self._hidden += 1
        if self._hidden:
            return
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")
        if tag in {"h1", "h2", "h3", "h4"}:
            self._heading = []
        if tag == "table":
            if self._table_depth == 0:
                self._rows = []
                # SEC captions such as "(In millions)" are often adjacent to rather than
                # inside the HTML table. Keep a bounded native-text prefix so deterministic
                # series extraction can verify scale without model inference.
                self._table_context = "".join(self.parts[-240:])[-4000:]
            self._table_depth += 1
        if self._table_depth == 1 and tag == "tr":
            self._row = []
        if self._table_depth == 1 and tag in {"td", "th"}:

            def span_value(key: str) -> int:
                try:
                    return max(1, min(100, int(attributes.get(key) or "1")))
                except ValueError:
                    return 1

            self._cell = {
                "text": "",
                "rowspan": span_value("rowspan"),
                "colspan": span_value("colspan"),
                "header": tag == "th",
            }

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "ix:hidden"}:
            self._hidden = max(0, self._hidden - 1)
            return
        if self._hidden:
            return
        if self._table_depth == 1 and tag in {"td", "th"} and self._cell is not None:
            self._cell["text"] = re.sub(r"\s+", " ", self._cell["text"]).strip()
            self._row.append(self._cell)
            self._cell = None
            self.parts.append("\t")
        if self._table_depth == 1 and tag == "tr":
            if self._row:
                self._rows.append(self._row)
            self._row = []
        if tag == "table":
            if self._table_depth == 1 and self._rows:
                self.tables.append(self._rows)
                self.table_contexts.append(self._table_context)
                self._table_context = ""
            self._table_depth = max(0, self._table_depth - 1)
        if tag in {"h1", "h2", "h3", "h4"} and self._heading is not None:
            self.headings.append("".join(self._heading).strip())
            self._heading = None
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._hidden:
            return
        self.parts.append(data)
        if self._cell is not None:
            self._cell["text"] += data
        if self._heading is not None:
            self._heading.append(data)


def parse_html(payload: bytes, source: Json) -> tuple[dict[str, Json], tuple[str, ...], list[str]]:
    parser = FilingHTMLParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    text = "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())
    objects: dict[str, Json] = {}
    doc_id = source["document_id"]
    blocks: list[str] = []
    for index, nominal_start in enumerate(range(0, len(text), 12000), 1):
        start = _token_boundary_start(text, nominal_start)
        block = text[start : nominal_start + 12000]
        blocks.append(block)
        identifier = _id("page", doc_id, index)
        objects[identifier] = _object(
            "page",
            identifier,
            source,
            block,
            page_index=index,
            page_number=None,
            label=f"HTML 文本区段 {index}",
            char_start=start,
            char_end=start + len(block),
            table_ids=[],
            figure_ids=[],
            footnote_ids=[],
            raw_blob_id=source["raw_blob_id"],
            extraction_status="html_text_block_not_physical_page",
            visual_inspection_available=False,
        )
        _add_evidence(objects, source, objects[identifier])
    for index, raw_rows in enumerate(parser.tables, 1):
        identifier = _id("table", doc_id, index)
        occupied: dict[tuple[int, int], str] = {}
        rows: list[list[Json]] = []
        for row_index, raw_row in enumerate(raw_rows):
            cells = []
            column = 0
            for cell in raw_row:
                while (row_index, column) in occupied:
                    column += 1
                cell_id = f"{identifier}_r{row_index}_c{column}"
                cells.append(
                    {**cell, "cell_id": cell_id, "row": row_index, "column": column, "bbox": None}
                )
                for row_delta in range(cell["rowspan"]):
                    for col_delta in range(cell["colspan"]):
                        occupied[(row_index + row_delta, column + col_delta)] = cell_id
                column += cell["colspan"]
            rows.append(cells)
        table_text = "\n".join(" | ".join(cell["text"] for cell in row) for row in rows)
        objects[identifier] = _object(
            "table",
            identifier,
            source,
            table_text,
            title=f"HTML 表格 {index}",
            rows=rows,
            row_count=len(rows),
            column_count=max((c + 1 for _r, c in occupied), default=0),
            page_id=None,
            page_number=None,
            footnote_ids=[],
            unit_candidates=[],
            header_status="html_th_and_span_preserved",
            extraction_status="native_html_unverified",
            context_text=(
                re.sub(r"[ \t]+", " ", parser.table_contexts[index - 1]).strip()
                if index - 1 < len(parser.table_contexts)
                else ""
            ),
        )
    cursor = 0
    for index, heading in enumerate(parser.headings, 1):
        start = text.find(heading, cursor)
        if not heading or start < 0:
            continue
        next_heading = parser.headings[index] if index < len(parser.headings) else None
        end = text.find(next_heading, start + len(heading)) if next_heading else len(text)
        if end < 0:
            end = len(text)
        identifier = _id("section", doc_id, index)
        objects[identifier] = _object(
            "section",
            identifier,
            source,
            text[start:end],
            title=heading,
            char_start=start,
            char_end=end,
            page_id=None,
            page_number=None,
            extraction_status="native_html_heading",
        )
        cursor = start + len(heading)
    gaps = ["HTML 区段不是 PDF 物理页；原生表格保留单元格跨度，嵌套布局表及图像语义需另行核查。"]
    return objects, tuple(blocks), gaps


def render_page(repository: ResearchRepository, page: Json) -> str:
    if not page.get("visual_inspection_available") or page.get("page_number") is None:
        raise ValueError("this source has no rendered PDF page")
    path = repository.blob_path(page["raw_blob_id"])
    with _PDFIUM_LOCK:
        document = pdfium.PdfDocument(str(path))
        try:
            pdf_page = document[int(page["page_number"]) - 1]
            width, height = pdf_page.get_size()
            scale = min(2.0, 1800.0 / max(width, height))
            bitmap = pdf_page.render(scale=scale)
            try:
                image = bitmap.to_pil()
                output = io.BytesIO()
                image.save(output, format="PNG")
                blob_id = repository.put_blob(output.getvalue(), "png")
                image.close()
            finally:
                bitmap.close()
                pdf_page.close()
        finally:
            document.close()
    return blob_id


def search_objects(
    objects: dict[str, Json], query: str, kind: str = "all", document_id: str | None = None
) -> list[Json]:
    query_terms = _retrieval_terms(query)
    ranked: list[tuple[float, int, int, Json]] = []
    for obj in objects.values():
        if kind != "all" and obj["kind"] != kind:
            continue
        if document_id is not None and obj["document_id"] != document_id:
            continue
        body = str(obj.get("text", ""))
        text = str(obj.get("title", "")) + " " + body
        object_terms = _retrieval_terms(text)
        matched_terms = query_terms & object_terms
        overlap = len(matched_terms)
        if not overlap:
            continue
        concept_overlap = sum(term.startswith("@") for term in matched_terms)
        score = overlap / (1 + math.log1p(len(text)) / 10)
        # Native HTML/PDF table structure preserves row/column context better than an arbitrary
        # page/evidence slice. Bonus requires at least two independent normalized concepts, so a
        # company name containing one word such as ``Rent`` cannot promote an unrelated table.
        if obj.get("kind") == "table" and concept_overlap >= 2:
            score += 0.25 * concept_overlap
        elif obj.get("kind") == "section" and concept_overlap >= 2:
            score += 0.1
        ranked.append((score, overlap, concept_overlap, obj))
    ranked.sort(key=lambda item: (-item[0], item[3]["artifact_id"]))
    if kind == "all":
        # Keep the result page heterogeneous. Long page/evidence chunks can share many generic
        # query words and otherwise crowd a complete native table out of the Agent's first page.
        # If a table matches at least two normalized concepts, guarantee the strongest such table
        # a slot within the first eight results without making every table globally preferred.
        table_candidates = [
            (index, item)
            for index, item in enumerate(ranked)
            if item[3].get("kind") == "table" and item[2] >= 2
        ]
        if table_candidates:
            # Prefer the table matching the most independent alias concepts; score breaks ties.
            table_index, _table_item = max(
                table_candidates, key=lambda pair: (pair[1][2], pair[1][0])
            )
            if table_index >= 8:
                table_item = ranked.pop(table_index)
                ranked.insert(7, table_item)
    return [
        {
            "artifact_id": obj["artifact_id"],
            "kind": obj["kind"],
            "document_id": obj["document_id"],
            "page_id": obj.get("page_id"),
            "page_number": obj.get("page_number"),
            "title": obj.get("title", obj.get("label", "")),
            "snippet": _query_centered_snippet(str(obj.get("text", "")), query_terms, 1200),
            "score": round(score, 4),
            "score_kind": "lexical_overlap_not_confidence",
            "text_length": len(obj.get("text", "")),
        }
        for score, _overlap, _concept_overlap, obj in ranked
    ]
