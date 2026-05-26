"""
test_search.py
Quick test: search the Chroma database with a question.
"""

import chromadb
from embedder import embed_text

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection("cyber_course")

# Ask a test question
question = "ethical hacking and reconnaissance"
print(f"\nQuestion: {question}\n")

# Embed the question and search for the 3 closest chunks
question_vector = embed_text(question)
results = collection.query(
    query_embeddings=[question_vector],
    n_results=3,
)

# Show the results
print("Top 3 most relevant chunks:\n")
for i in range(len(results["documents"][0])):
    doc = results["documents"][0][i]
    meta = results["metadatas"][0][i]
    distance = results["distances"][0][i]
    print(f"--- Result {i+1} (from {meta['module']}, distance {distance:.3f}) ---")
    print(doc[:300] + "...")
    print()