"""
ingest.py
One-time script: reads all course modules, chunks them,
embeds the chunks, and stores everything in the Chroma vector database.
Run this whenever the course content changes.
"""

import os
import chromadb

from document_reader import read_document
from chunker import chunk_text
from embedder import embed_many

# --- Configuration ----------------------------------------------------------
COURSE_FOLDER = "course_notes"
CHROMA_FOLDER = "chroma_db"          # Chroma stores its data here
COLLECTION_NAME = "cyber_course"     # name of our chunk collection


def ingest():
    print("=" * 60)
    print("  COURSE CONTENT INGESTION")
    print("=" * 60)

    # 1. Connect to Chroma (creates the chroma_db folder if missing)
    print("\n[1/5] Connecting to Chroma database...")
    client = chromadb.PersistentClient(path=CHROMA_FOLDER)

    # 2. Create a fresh collection (delete old one if it exists)
    print("[2/5] Preparing the collection...")
    try:
        client.delete_collection(COLLECTION_NAME)
        print("      (removed old collection so we start fresh)")
    except Exception:
        pass  # no old collection — that's fine
    collection = client.create_collection(COLLECTION_NAME)

    # 3. Read and chunk every module
    print("[3/5] Reading and chunking all modules...")
    all_chunks = []      # the chunk texts
    all_ids = []         # a unique id for each chunk
    all_metadatas = []   # extra info: which module each chunk came from

    files = sorted(os.listdir(COURSE_FOLDER))
    for f in files:
        path = os.path.join(COURSE_FOLDER, f)
        text = read_document(path)
        chunks = chunk_text(text)

        # module name without extension, e.g. "module_06"
        module_name = os.path.splitext(f)[0]

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{module_name}_chunk_{i:03d}")
            all_metadatas.append({"module": module_name, "chunk_index": i})

        print(f"      {f}: {len(chunks)} chunks")

    print(f"      Total: {len(all_chunks)} chunks")

    # 4. Embed all chunks (turn text into vectors)
    print("[4/5] Embedding all chunks (this may take 1-2 minutes)...")
    embeddings = embed_many(all_chunks)

    # 5. Store everything in Chroma
    print("[5/5] Storing chunks + embeddings in Chroma...")
    collection.add(
        ids=all_ids,
        documents=all_chunks,
        embeddings=embeddings,
        metadatas=all_metadatas,
    )

    print("\n" + "=" * 60)
    print(f"  ✅ DONE — {len(all_chunks)} chunks stored in Chroma")
    print(f"  Database saved in: ./{CHROMA_FOLDER}/")
    print("=" * 60)


if __name__ == "__main__":
    ingest()