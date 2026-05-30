"""
retriever.py
Searches the Chroma vector database for course chunks
relevant to a student's question.
"""

import chromadb
from embedder import embed_text

CHROMA_FOLDER = "chroma_db"
COLLECTION_NAME = "cyber_course"

# If the best match is farther than this distance, we treat the
# question as "not well covered by the course material".
RELEVANCE_THRESHOLD = 1.35

# Connect to Chroma once when this file loads
_client = chromadb.PersistentClient(path=CHROMA_FOLDER)
_collection = _client.get_collection(COLLECTION_NAME)


def retrieve(question: str, n_results: int = 4) -> dict:
    """
    Search the course content for chunks relevant to the question.

    Returns a dict with:
      - 'chunks'      : list of relevant chunk texts
      - 'modules'     : list of module names the chunks came from
      - 'best_distance': the distance of the closest match (lower = better)
      - 'has_good_match': True if at least one chunk is relevant enough
    """
    question_vector = embed_text(question)

    results = _collection.query(
        query_embeddings=[question_vector],
        n_results=n_results,
    )

    chunks = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    modules = [m["module"] for m in metadatas]
    best_distance = distances[0] if distances else 999

    return {
        "chunks": chunks,
        "modules": modules,
        "distances": distances,
        "best_distance": best_distance,
        "has_good_match": best_distance <= RELEVANCE_THRESHOLD,
    }


# --- Quick test ---
if __name__ == "__main__":
    for q in ["What is ethical hacking?", "How do I bake a cake?"]:
        print(f"\nQuestion: {q}")
        result = retrieve(q)
        print(f"  Best distance: {result['best_distance']:.3f}")
        print(f"  Good match? {result['has_good_match']}")
        print(f"  From modules: {result['modules']}")