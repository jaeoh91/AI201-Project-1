import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).parent
DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_PATH = str(BASE_DIR / "chroma_db")

# --- ChromaDB ---
COLLECTION_NAME = "f1_visa_policies"

# --- Embeddings ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- LLM ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"

# --- Chunking ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# --- Retrieval ---
TOP_K = 5
DISTANCE_THRESHOLD = 0.5
