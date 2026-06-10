# F-1 Visa RAG Knowledge Base — System Design

**Status:** In progress  
**Last updated:** June 2026

---

## Problem Statement

Georgia Tech's Office of International Education publishes F-1 visa policy across 25 separate web pages. Students trying to answer a specific question — "does part-time CPT count toward my OPT eligibility?" or "what's the minimum credits I can take with a medical RCL?" — have to navigate between multiple pages, each written in dense bureaucratic language.

This system makes the GT ISSS F-1 policy corpus queryable in plain language. A student asks a question and receives a specific, cited answer drawn directly from the official policy pages. The core constraint: the system must refuse to answer when the retrieved context is insufficient, rather than hallucinating an authoritative-sounding response about immigration rules.

---

## Architecture

The system is a RAG (Retrieval-Augmented Generation) pipeline with five stages:

```
[0] SCRAPE          ──► Raw HTML is fetched from 25 GT ISSS policy pages and
    download_sources.py  converted to structured plain text (documents/*.txt)
         │
         ▼
[1] INGEST          ──► Text files are chunked and stored once into ChromaDB
    ingest.py
         │
         ▼
[2] RETRIEVE        ──► User query is embedded and matched against stored
    retriever.py         chunks via cosine similarity; low-relevance chunks filtered
         │
         ▼
[3] GENERATE        ──► Retrieved chunks are passed as context to an LLM,
    generator.py         which produces a grounded, cited answer (or refuses)
         │
         ▼
[4] UI              ──► Gradio chat interface serves the response to the user
    app.py
```

Stage 0 (`download_sources.py`) is a one-time offline step. Stages 1–4 form the runtime pipeline.

---

## File Structure

```
Week-1/Project-1/
├── app.py                  # Gradio UI; wires retriever + generator
├── config.py               # Central config: model names, paths, thresholds
├── ingest.py               # Load docs → chunk → embed → store in ChromaDB
├── retriever.py            # Query embedding + ChromaDB search + distance filter
├── generator.py            # Context formatting + Groq LLM call + citation
├── download_sources.py     # One-time scraper: HTML → structured .txt files
├── requirements.txt
├── .env                    # GROQ_API_KEY (not committed)
├── documents/
│   ├── sources.csv         # Source index (number, name, URL)
│   └── *.txt               # 25 scraped policy documents
├── specs/
│   ├── system-design.md    # This file
│   ├── ingest-spec.md      # Input/output contract for ingest.py
│   ├── retrieve-spec.md    # Input/output contract for retriever.py
│   └── generate-spec.md    # Input/output contract for generator.py
└── chroma_db/              # Persistent ChromaDB index (auto-created)
```

---

## Technical Decisions

### Stage 0 — Document acquisition: `download_sources.py`

Rather than storing raw HTML or plain `.get_text()` output, the scraper walks the HTML DOM tag-by-tag and converts each element into structured plain text:

| HTML tag | Output |
|:---|:---|
| `<h1>`–`<h6>` | `# Heading` surrounded by blank lines |
| `<p>` | Paragraph text with `\n\n` before and after |
| `<ul>/<li>` | `- item` lines, with `\n\n` around the list |
| `<ol>/<li>` | `1. item` numbered lines |
| `<table>/<tr>` | Pipe-separated row: `col1 \| col2` |
| `<br>` | Single `\n` |
| `<nav>`, `<footer>`, `<script>`, `<form>` | Stripped entirely |

Every file begins with a `Source: <name>` and `URL: <url>` header line. These headers are preserved through chunking so every retrieved chunk can cite its source.

**Why:** Plain `.get_text()` produced broken sentences and collapsed structure. The structured conversion means `\n\n` boundaries in every output file correspond exactly to real paragraph/section boundaries — the same delimiter that the chunker tries first.

---

### Stage 1 — Chunking: `RecursiveCharacterTextSplitter`

```python
chunk_size    = 800    # characters (ceiling, not target)
chunk_overlap = 150    # characters
separators    = ["\n\n", "\n", ". ", " "]
```

The splitter tries separators in order, falling back to the next only if a block still exceeds 800 characters. Because the scraper marks every natural section boundary with `\n\n`, the chunker almost always splits at paragraph/heading boundaries rather than mid-sentence.

The `Source:` / `URL:` header from each document is prepended to every chunk at ingest time so that attribution is preserved even when a chunk lands in the middle of a large document.

**Post-processing — orphaned heading fix:** After the initial split, a second pass detects chunks whose last meaningful paragraph is a heading without any content beneath it. This happens when a body paragraph ends exactly at the 800-character ceiling and the next HTML element is a section heading: the splitter places the heading at the tail of the current chunk and the content at the head of the next. The fix moves the orphaned heading forward to the top of the next chunk, keeping it co-located with the content it introduces. Without this pass, a retrieved chunk could contain only a citation header and a bare heading line — semantically useless to the LLM.

**Estimated chunk count:** ~150–250 total across 25 documents.

---

### Stage 2 — Embedding: `all-MiniLM-L6-v2`

- Runs locally via `sentence-transformers` — no API key, no rate limits, no cost
- 384-dimensional output vectors
- 256-token context window — safe for 800-character chunks (~200 tokens average)
- Integrated directly into ChromaDB via `SentenceTransformerEmbeddingFunction`

**Production alternative:** `BAAI/bge-base-en-v1.5` — same local setup, 512-token window, consistently higher retrieval benchmark scores. Drop-in replacement if retrieval quality is insufficient.

---

### Stage 3 — Vector store: ChromaDB (persistent)

- Persists the index to `./chroma_db/` on disk
- Ingestion runs once; subsequent startups skip it if the collection is already populated
- Similarity metric: cosine distance (lower = more similar; 0 = identical)
- Retrieval: top-k = 5, then filter out chunks with cosine distance > threshold (configurable in `config.py`)

**Why top-k = 5:** F-1 policy questions frequently require information from more than one source page (e.g., "can I do CPT and still be eligible for OPT?" requires both the CPT and OPT pages). A generous k ensures multi-document answers can surface.

---

### Stage 4 — Generation: Groq / `llama-3.3-70b-versatile`

- API key loaded from `.env` via `config.py`
- Retrieved chunks are formatted into a numbered context block, each labeled with its source name and URL
- System prompt enforces grounding: the model is instructed to answer **only** from the provided context, cite the source name for each claim, and respond with a refusal message if context is insufficient
- Fail-closed: if no chunks pass the distance threshold, the system returns a fixed refusal without calling the LLM

---

## Grounding Strategy

The system uses two layers to prevent hallucination:

**Layer 1 — Retrieval gate:** If all retrieved chunks have cosine distance above the threshold (configurable, default ~0.5), the pipeline short-circuits and returns a refusal without calling the LLM at all.

**Layer 2 — System prompt constraint:** The system prompt passed to the LLM explicitly states:
- Answer only using the provided context passages
- Cite the source name for every factual claim
- If the context does not contain enough information to answer, say so explicitly — do not infer or guess

This dual-layer approach means the system fails closed in two distinct ways: at the retrieval stage (no relevant context) and at the generation stage (context present but insufficient for the specific question).

---

## Data Flow (End-to-End)

```
User types: "Can I work on CPT for 2 years and still apply for OPT?"
    │
    ▼
retriever.py
  embed query with all-MiniLM-L6-v2
  query ChromaDB → top-5 chunks by cosine distance
  filter: discard chunks with distance > threshold
  return: [
    {text: "...", source: "CPT", url: "...", distance: 0.21},
    {text: "...", source: "OPT", url: "...", distance: 0.28},
    ...
  ]
    │
    ▼
generator.py
  format context block:
    [1] Source: CPT — https://...
        <chunk text>
    [2] Source: OPT — https://...
        <chunk text>
    ...
  call Groq API with system prompt + context + user query
  return: "No. According to the CPT policy [...], students authorized for
           more than 364 days of full-time CPT are no longer eligible for
           OPT. (Source: Curricular Practical Training (CPT),
           https://isss.oie.gatech.edu/content/...)"
    │
    ▼
app.py (Gradio)
  display response in chat window
```

---

## Configuration (`config.py`)

All tunable values should live in `config.py`, not hardcoded in pipeline files:

```python
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
LLM_MODEL         = "llama-3.3-70b-versatile"
CHROMA_PATH       = "./chroma_db"
COLLECTION_NAME   = "f1_visa_policies"
DOCUMENTS_DIR     = "/documents"
CHUNK_SIZE        = 800
CHUNK_OVERLAP     = 150
TOP_K             = 5
DISTANCE_THRESHOLD = 0.5
```

---