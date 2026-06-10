"""
Gradio chat interface for the F-1 Visa RAG Knowledge Base.

Wires together retriever.retrieve() and generator.generate_response().
Ingestion is expected to have been run separately via ingest.py before
starting this app.
"""

import gradio as gr
import chromadb

import config
from retriever import retrieve
from generator import generate_response


# ---------------------------------------------------------------------------
# Startup check
# ---------------------------------------------------------------------------

def _check_collection_populated() -> bool:
    client = chromadb.PersistentClient(path=config.CHROMA_PATH)
    try:
        col = client.get_collection(config.COLLECTION_NAME)
        return col.count() > 0
    except Exception:
        return False


_INGESTION_WARNING = (
    "⚠️  The knowledge base appears to be empty. "
    "Run `python ingest.py` first to populate it, then restart this app."
)


# ---------------------------------------------------------------------------
# Chat handler
# ---------------------------------------------------------------------------

def chat(message: str, history: list) -> str:
    if not message.strip():
        return ""
    chunks = retrieve(message)
    return generate_response(message, chunks)


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

populated = _check_collection_populated()

with gr.Blocks(title="GT F-1 Visa Policy Assistant") as demo:

    gr.HTML("""
        <div style="text-align:center; padding:1.25rem 0 0.5rem;">
            <h1 style="font-size:2rem; font-weight:700; color:#003057; margin:0;">
                GT F-1 Visa Policy Assistant
            </h1>
            <p style="color:#6b7280; font-size:1rem; margin:0.4rem 0 0;">
                Ask questions about F-1 visa policy — answers drawn directly from
                GT ISSS official policy pages.
            </p>
        </div>
    """)

    if not populated:
        gr.Markdown(f"> **{_INGESTION_WARNING}**")

    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=chat,
                chatbot=gr.Chatbot(
                    height=520,
                    placeholder=(
                        "Ask a question about F-1 visa status, CPT, OPT, travel, "
                        "employment, or other GT ISSS policies."
                    ),
                    show_label=False,
                ),
                examples=[
                    "I worked 400 days on full-time CPT. Am I eligible for OPT after graduation?",
                    "I'm on post-completion OPT and my F-1 visa stamp expired. Can I travel abroad and re-enter the US?",
                    "I'm a F1 student working on campus. Do I need an SSN and how do I get one?",
                    "Can I drop below 12 credit hours for medical reasons, and if so what is the minimum?",
                ],
            )

        with gr.Column(scale=1):
            gr.Markdown("""
### About this tool

This assistant answers questions about **F-1 visa policy** using only the
official policy documents published by
[GT ISSS](https://isss.oie.gatech.edu/ISSS_F_Current).

**It will refuse to answer if relevant policy text cannot be found.**
For authoritative guidance, always follow up with GT ISSS directly.

---

**Contact GT ISSS**
- Email: isss@oie.gatech.edu
- Walk-in: Savant Building, Suite 080
            """)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(primary_hue="blue"))
