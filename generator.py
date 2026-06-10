"""
Generation pipeline: format retrieved chunks and call the Groq LLM.

Public interface:
    generate_response(query: str, retrieved_chunks: list[dict]) -> str

retrieved_chunks is the list returned by retriever.retrieve():
    [{"text": ..., "source": ..., "url": ..., "distance": ...}, ...]

Returns a grounded, cited answer string, or a fixed refusal if no chunks
were provided (the retriever already filtered by distance threshold, so an
empty list means no relevant context was found).
"""

from groq import Groq
import config

_client = Groq(api_key=config.GROQ_API_KEY)

_SYSTEM_PROMPT = """\
You are an expert assistant on F-1 visa policy for Georgia Tech international students.
Answer the user's question using ONLY the information provided in the numbered context
passages below. Do not use any outside knowledge about immigration law or visa policy.

Rules:
1. Cite the source inline immediately after each sentence that contains a factual claim.
   Format citations as a Markdown link using the source name and URL from the passage header,
   e.g. "Students authorized for more than 364 days of full-time CPT are no longer eligible
   for OPT. ([Curricular Practical Training (CPT)](https://isss.oie.gatech.edu/content/curricular-practical-training-cpt-georgia-tech))"
2. If the context passages do not contain enough information to answer the question,
   respond with exactly:
   "I'm sorry, I don't have enough information in my knowledge base to answer that question. \
Please contact GT ISSS directly at isss@oie.gatech.edu for authoritative guidance."
3. Do not infer, guess, or extrapolate beyond what is explicitly stated in the passages.
4. Do not mention the context numbers or that you were given passages — answer naturally.
"""

_REFUSAL = (
    "I'm sorry, I don't have enough information in my knowledge base to answer that question. "
    "Please contact GT ISSS directly at isss@oie.gatech.edu for authoritative guidance."
)


def _format_context(chunks: list[dict]) -> str:
    """Build a numbered context block from retrieved chunks."""
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        header = f"[{i}] Source: {chunk['source']}"
        if chunk.get("url"):
            header += f" — {chunk['url']}"
        blocks.append(f"{header}\n{chunk['text']}")
    return "\n\n".join(blocks)


def generate_response(query: str, retrieved_chunks: list[dict]) -> str:
    """
    Generate a grounded answer from retrieved policy chunks.

    If retrieved_chunks is empty (retrieval gate triggered), returns a fixed
    refusal without calling the LLM.
    """
    if not retrieved_chunks:
        return _REFUSAL

    context = _format_context(retrieved_chunks)

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"CONTEXT PASSAGES:\n\n{context}\n\nQUESTION: {query}",
        },
    ]

    try:
        response = _client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred while generating the response: {e}"
