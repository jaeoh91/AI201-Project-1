"""
Retrieval pipeline: embed a query and return the most relevant chunks from ChromaDB.

Public interface:
    retrieve(query: str) -> list[dict]

Each returned dict has:
    text      - chunk text (includes Source/URL header)
    source    - document source name
    url       - source URL
    distance  - cosine distance (lower = more similar; 0 = identical)
"""

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

import config


def _get_collection() -> chromadb.Collection:
    ef = SentenceTransformerEmbeddingFunction(model_name=config.EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    return client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def retrieve(query: str) -> list[dict]:
    """
    Embed *query* with all-MiniLM-L6-v2, query ChromaDB for the top-k
    nearest chunks, then filter out any chunk whose cosine distance exceeds
    DISTANCE_THRESHOLD.

    Returns a list of dicts ordered by ascending distance:
        [{"text": ..., "source": ..., "url": ..., "distance": ...}, ...]

    Returns an empty list if the collection is empty or no chunk passes
    the distance threshold.
    """
    collection = _get_collection()

    if collection.count() == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(config.TOP_K, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for text, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        if distance <= config.DISTANCE_THRESHOLD:
            chunks.append(
                {
                    "text": text,
                    "source": meta.get("source", ""),
                    "url": meta.get("url", ""),
                    "distance": round(distance, 4),
                }
            )

    return chunks


# ---------------------------------------------------------------------------
# Manual retrieval test — run with: python retriever.py
# ---------------------------------------------------------------------------

TEST_QUERIES = [
    "I worked 400 days on full-time CPT. Am I eligible for OPT after graduation?",
    "I worked 4 semesters on part-time CPT and 2 summers on full-time CPT. Am I good for OPT?",
    "I'm a F1 student working on campus. Do I need an SSN and how do I get one?",
    "I'm on post-completion OPT and my F-1 visa stamp expired. Can I travel abroad and re-enter?",
    "My doctor recommends a lighter course load. Can I drop below 12 credit hours?",
]

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test retrieval with predefined or custom queries.")
    parser.add_argument("query", nargs="?", help="Custom query to test (optional)")
    args = parser.parse_args()

    queries = [args.query] if args.query else TEST_QUERIES

    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}: {query}")
        print("=" * 70)

        chunks = retrieve(query)

        if not chunks:
            print("  [No chunks passed the distance threshold — would trigger refusal]")
            continue

        for j, chunk in enumerate(chunks, 1):
            print(f"\n  Chunk {j}  |  distance={chunk['distance']}  |  source={chunk['source']}")
            print(f"  URL: {chunk['url']}")
            print(f"  {'-'*60}")
            # Print first 300 chars of the chunk body (skip the Source/URL header lines)
            body_lines = chunk["text"].splitlines()
            body = "\n  ".join(body_lines[3:])  # skip "Source:", "URL:", blank line
            print(f"  {body[:400]}{'...' if len(body) > 400 else ''}")
