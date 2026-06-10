"""
Ingest pipeline: load .txt documents → chunk → embed → store in ChromaDB.

Usage:
  python ingest.py              # ingest all documents (skips if already populated)
  python ingest.py --preview    # print sample chunks from 3 files, no storage
  python ingest.py --preview --n 5   # preview chunks from 5 files
"""
import argparse
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


# ---------------------------------------------------------------------------
# Document loading
# ---------------------------------------------------------------------------

def load_document(path: Path) -> tuple[str, str, str]:
    """
    Parse a structured policy .txt file.

    Every document begins with:
        Source: <name>
        URL: <url>
        <blank line>
        <body text>

    Returns (source_name, url, body_text).
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    source = ""
    url = ""
    body_start = 0

    for i, line in enumerate(lines):
        if line.startswith("Source:"):
            source = line[len("Source:"):].strip()
        elif line.startswith("URL:"):
            url = line[len("URL:"):].strip()
            body_start = i + 1  # everything after the URL line is body
            break

    body = "\n".join(lines[body_start:])
    return source, url, body


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _is_orphaned_heading(paragraph: str) -> bool:
    """
    Return True if paragraph looks like a section heading without body content:
    a single line that is either a markdown heading (# ...) or a short title
    with no terminal sentence punctuation (., ,, ;, :, )).

    These lines are safe to move to the next chunk so they stay paired with
    the content that follows them.
    """
    lines = [l for l in paragraph.splitlines() if l.strip()]
    if len(lines) != 1:
        return False
    line = lines[0].strip()
    if re.match(r"^#{1,6}\s", line):          # markdown heading of any level
        return True
    if len(line) <= 80 and line[-1] not in ".,:;)":  # short title-like line
        return True
    return False


def _fix_orphaned_headings(chunks: list[str]) -> list[str]:
    """
    Post-process raw chunks so that a heading never sits at the end of a chunk
    without any content beneath it.

    When the last non-empty paragraph of chunk N is a heading, it is removed
    from chunk N and prepended to chunk N+1.  This keeps headings co-located
    with the content they introduce, which produces better retrieval context.
    """
    if len(chunks) < 2:
        return chunks

    result: list[str] = []
    carry = ""          # heading moved forward from the previous chunk

    for i, chunk in enumerate(chunks):
        if carry:
            # The overlap may have already copied the heading to the start of
            # this chunk.  Deduplicate before prepending so it never appears
            # twice.  Compare stripped versions to be whitespace-tolerant.
            paragraphs_check = [p.strip() for p in chunk.split("\n\n") if p.strip()]
            if paragraphs_check and paragraphs_check[0] == carry.strip():
                # overlap already brought the heading in — strip the duplicate
                first_para_end = chunk.find(paragraphs_check[0]) + len(paragraphs_check[0])
                chunk = chunk[first_para_end:].lstrip("\n")
            chunk = carry + "\n\n" + chunk
            carry = ""

        paragraphs = chunk.split("\n\n")
        # drop trailing empty paragraphs
        while paragraphs and not paragraphs[-1].strip():
            paragraphs.pop()

        if not paragraphs:
            result.append(chunk)
            continue

        last_para = paragraphs[-1].strip()

        # Only carry forward if there is a next chunk to receive the heading
        if i < len(chunks) - 1 and _is_orphaned_heading(last_para):
            carry = last_para
            paragraphs.pop()
            chunk = "\n\n".join(paragraphs)

        result.append(chunk)

    # Edge case: last chunk ended with an orphaned heading — just keep it
    if carry:
        result[-1] = result[-1].rstrip() + "\n\n" + carry

    return result


def chunk_document(body: str, source: str, url: str) -> list[dict]:
    """
    Split body text using RecursiveCharacterTextSplitter, fix orphaned
    headings, then prepend the Source/URL header to every chunk so
    attribution is preserved regardless of where a chunk lands.

    Returns a list of dicts with keys: text, source, url.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " "],
    )
    raw_chunks = splitter.split_text(body)
    raw_chunks = _fix_orphaned_headings(raw_chunks)
    header = f"Source: {source}\nURL: {url}\n\n"
    return [
        {"text": header + chunk, "source": source, "url": url}
        for chunk in raw_chunks
    ]


def get_txt_files() -> list[Path]:
    return sorted(p for p in config.DOCUMENTS_DIR.iterdir() if p.suffix == ".txt")


# ---------------------------------------------------------------------------
# Ingest (full pipeline)
# ---------------------------------------------------------------------------

def ingest() -> None:
    """
    Chunk all documents and upsert into a persistent ChromaDB collection.
    Skips silently if the collection is already populated.
    """
    ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() > 0:
        print(
            f"Collection '{config.COLLECTION_NAME}' already contains "
            f"{collection.count()} chunks. Skipping ingest.\n"
            f"Delete '{config.CHROMA_PATH}' to re-ingest from scratch."
        )
        return

    txt_files = get_txt_files()
    all_chunks: list[dict] = []

    print(f"Loading and chunking {len(txt_files)} documents...")
    for path in txt_files:
        source, url, body = load_document(path)
        chunks = chunk_document(body, source, url)
        all_chunks.extend(chunks)
        print(f"  {path.name}: {len(chunks)} chunks")

    ids = [f"chunk_{i}" for i in range(len(all_chunks))]
    documents = [c["text"] for c in all_chunks]
    metadatas = [{"source": c["source"], "url": c["url"]} for c in all_chunks]

    print(f"\nEmbedding and storing {len(all_chunks)} chunks...")
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f"Done. Collection '{config.COLLECTION_NAME}' now has {collection.count()} chunks.")


# ---------------------------------------------------------------------------
# Preview (dry-run)
# ---------------------------------------------------------------------------

def preview(n: int = 3) -> None:
    """
    Print sample chunks from the first n documents without storing anything.
    Shows chunk 0 and chunk 1 of each file so you can verify:
      - Source/URL header is present
      - Chunks split at natural boundaries (not mid-sentence)
      - Character count is within the configured ceiling
    """
    txt_files = get_txt_files()[:n]

    for path in txt_files:
        source, url, body = load_document(path)
        chunks = chunk_document(body, source, url)
        print(f"\n{'='*70}")
        print(f"FILE : {path.name}")
        print(f"TOTAL: {len(chunks)} chunks")
        print(f"{'='*70}")

        for idx in range(min(2, len(chunks))):
            chunk_text = chunks[idx]["text"]
            print(f"\n--- Chunk {idx} ({len(chunk_text)} chars) ---")
            print(chunk_text)

    print(f"\n{'='*70}")
    print("Preview complete. No data was written to ChromaDB.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest F-1 policy documents into ChromaDB."
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Print sample chunks without storing (dry run).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="Number of documents to show in preview mode (default: 3).",
    )
    args = parser.parse_args()

    if args.preview:
        preview(n=args.n)
    else:
        ingest()
