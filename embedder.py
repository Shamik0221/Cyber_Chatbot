"""
embedder.py
Converts text into embedding vectors using a local model.
"""

from sentence_transformers import SentenceTransformer

# The embedding model we'll use.
# 'all-MiniLM-L6-v2' is small (~90MB), fast, and great quality for our use case.
# It outputs 384-number vectors.
MODEL_NAME = "all-MiniLM-L6-v2"

# Load the model ONCE when this file is imported (loading is slow, ~5 sec).
print(f"Loading embedding model '{MODEL_NAME}'... (first run downloads ~90MB)")
_model = SentenceTransformer(MODEL_NAME)
print("Embedding model ready.")


def embed_text(text: str) -> list:
    """Convert a single piece of text into an embedding vector (list of 384 numbers)."""
    vector = _model.encode(text)
    return vector.tolist()


def embed_many(texts: list) -> list:
    """Convert a list of texts into a list of embedding vectors. Efficient for batches."""
    vectors = _model.encode(texts, show_progress_bar=True)
    return [v.tolist() for v in vectors]


# --- Quick test when run directly ---
if __name__ == "__main__":
    # Test 1: embed a single sentence, show its shape
    sample = "Firewalls protect networks from unauthorized access."
    vec = embed_text(sample)
    print(f"\nTest 1 — single embedding:")
    print(f"  Input: '{sample}'")
    print(f"  Output: a vector of {len(vec)} numbers")
    print(f"  First 5 numbers: {[round(n, 3) for n in vec[:5]]}")

    # Test 2: prove that similar meanings get similar vectors
    print(f"\nTest 2 — semantic similarity:")
    a = embed_text("How do firewalls block hackers?")
    b = embed_text("Network security devices preventing intruders")
    c = embed_text("My favourite food is chocolate cake")

    # Cosine similarity: 1.0 = identical meaning, 0 = unrelated
    def similarity(v1, v2):
        dot = sum(x * y for x, y in zip(v1, v2))
        mag1 = sum(x * x for x in v1) ** 0.5
        mag2 = sum(x * x for x in v2) ** 0.5
        return dot / (mag1 * mag2)

    print(f"  'firewalls block hackers'  vs  'security devices preventing intruders'")
    print(f"    similarity = {similarity(a, b):.3f}  (should be HIGH — related)")
    print(f"  'firewalls block hackers'  vs  'favourite food chocolate cake'")
    print(f"    similarity = {similarity(a, c):.3f}  (should be LOW — unrelated)")