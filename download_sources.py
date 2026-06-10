"""Download policy text from each source listed in documents/sources.csv.

Extracts only the main policy content (<div role="main" ...>) and converts
the HTML structure into structured plain text that preserves natural section
boundaries for recursive chunking:

  - h1–h6  →  section heading lines surrounded by blank lines
  - p       →  paragraph text surrounded by blank lines
  - ul/ol   →  bullet/numbered list items, each on its own line, with
               a blank line before and after the list
  - li      →  "- item text" (ul) or "N. item text" (ol)
  - br      →  single newline within a block
  - table   →  each row rendered as a pipe-separated line
  - div/section/article  →  transparent wrappers (content is preserved)
  - nav/header/footer/script/style/form/noscript/iframe  →  stripped

The resulting double-newline (\n\n) boundaries between paragraphs and
headings are exactly what RecursiveCharacterTextSplitter splits on first.

Usage:
    pip install requests beautifulsoup4
    python download_sources.py
"""

import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

SCRIPT_DIR = Path(__file__).parent
DOCUMENTS_DIR = SCRIPT_DIR / "documents"
SOURCES_CSV = DOCUMENTS_DIR / "sources.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
REQUEST_DELAY_SECONDS = 1  # be polite to the server

# Tags whose content should be silently dropped.
STRIP_TAGS = {"script", "style", "nav", "noscript", "iframe", "form",
              "header", "footer", "aside"}


def slugify(name: str) -> str:
    """Turn a source name into a safe filename."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def _node_to_text(node, list_type: str = "", list_index: list = None) -> str:
    """
    Recursively convert a BeautifulSoup node into structured plain text.

    Block-level elements (headings, paragraphs, lists) are wrapped in
    double newlines so they become natural split points for recursive chunking.
    Inline elements (a, strong, em, span, code) are rendered as plain text
    without any extra spacing.
    """
    if isinstance(node, NavigableString):
        text = str(node)
        # Collapse internal whitespace but keep a single space.
        return re.sub(r"[ \t]+", " ", text)

    if not isinstance(node, Tag):
        return ""

    tag = node.name.lower() if node.name else ""

    # ── Stripped tags ────────────────────────────────────────────────────────
    if tag in STRIP_TAGS:
        return ""

    # ── Line break ───────────────────────────────────────────────────────────
    if tag == "br":
        return "\n"

    # ── Headings: h1–h6 ──────────────────────────────────────────────────────
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        inner = "".join(_node_to_text(c) for c in node.children).strip()
        if not inner:
            return ""
        level = int(tag[1])          # 1–6
        prefix = "#" * level         # markdown-style prefix aids readability
        return f"\n\n{prefix} {inner}\n\n"

    # ── Paragraph ────────────────────────────────────────────────────────────
    if tag == "p":
        inner = "".join(_node_to_text(c) for c in node.children).strip()
        if not inner:
            return ""
        return f"\n\n{inner}\n\n"

    # ── Unordered list ───────────────────────────────────────────────────────
    if tag == "ul":
        items = []
        for child in node.children:
            if isinstance(child, Tag) and child.name == "li":
                item_text = "".join(_node_to_text(c) for c in child.children).strip()
                if item_text:
                    items.append(f"- {item_text}")
        if not items:
            return ""
        return "\n\n" + "\n".join(items) + "\n\n"

    # ── Ordered list ─────────────────────────────────────────────────────────
    if tag == "ol":
        items = []
        idx = 1
        for child in node.children:
            if isinstance(child, Tag) and child.name == "li":
                item_text = "".join(_node_to_text(c) for c in child.children).strip()
                if item_text:
                    items.append(f"{idx}. {item_text}")
                    idx += 1
        if not items:
            return ""
        return "\n\n" + "\n".join(items) + "\n\n"

    # ── Table ────────────────────────────────────────────────────────────────
    if tag == "table":
        rows = []
        for tr in node.find_all("tr"):
            cells = [td.get_text(" ", strip=True)
                     for td in tr.find_all(["td", "th"])]
            if any(cells):
                rows.append(" | ".join(cells))
        if not rows:
            return ""
        return "\n\n" + "\n".join(rows) + "\n\n"

    # ── Block-level wrappers (div, section, article, main, …) ────────────────
    # Treat as transparent: recurse into children and join.
    if tag in {"div", "section", "article", "main", "blockquote",
               "details", "summary", "figure", "figcaption"}:
        return "".join(_node_to_text(c) for c in node.children)

    # ── Inline elements (a, strong, em, span, code, td inside inline, …) ────
    return "".join(_node_to_text(c) for c in node.children)


def _collapse_blank_lines(text: str, max_blank: int = 2) -> str:
    """Reduce runs of more than `max_blank` consecutive blank lines."""
    pattern = r"\n{" + str(max_blank + 1) + r",}"
    return re.sub(pattern, "\n" * max_blank, text).strip()


def extract_structured_text(html: str) -> str:
    """
    Parse the HTML, isolate the main content container, convert it to
    structured plain text, and return the cleaned result.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Isolate the main policy content; skip GT banner/footer.
    main = (
        soup.find("div", attrs={"role": "main"})
        or soup.find("main")
        or soup.body
    )
    if main is None:
        return ""

    raw = _node_to_text(main)
    return _collapse_blank_lines(raw)


def main() -> None:
    DOCUMENTS_DIR.mkdir(exist_ok=True)

    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        sources = list(csv.DictReader(f))

    print(f"Found {len(sources)} sources in {SOURCES_CSV.name}\n")

    failures = []
    for row in sources:
        num = row["#"]
        name = row["Source"]
        url = row["URL or file path"]
        out_path = DOCUMENTS_DIR / f"{num.zfill(2)}_{slugify(name)}.txt"

        print(f"[{num}/{len(sources)}] {name} ... ", end="", flush=True)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            resp.raise_for_status()
            text = extract_structured_text(resp.text)
            if not text:
                raise ValueError("no main content found")

            header = f"Source: {name}\nURL: {url}\n\n"
            out_path.write_text(header + text, encoding="utf-8")
            print(f"saved -> {out_path.name} ({len(text):,} chars)")
        except Exception as e:
            print(f"FAILED ({e})")
            failures.append((name, url, str(e)))

        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\nDone: {len(sources) - len(failures)}/{len(sources)} succeeded.")
    if failures:
        print("Failures:")
        for name, url, err in failures:
            print(f"  - {name}: {url} ({err})")


if __name__ == "__main__":
    main()
