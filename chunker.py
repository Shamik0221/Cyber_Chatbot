"""
chunker.py
Splits module text into small, retrieval-friendly chunks.
"""

import re


# --- Tuning knobs -----------------------------------------------------------
TARGET_WORDS = 180      # ideal chunk size in words
MAX_WORDS = 280      # never exceed this
OVERLAP_WORDS = 40      # words shared between consecutive chunks


def split_into_paragraphs(text: str) -> list:
    """Break text into paragraphs (separated by blank lines or single newlines)."""
    # Split on one or more newlines
    parts = re.split(r"\n+", text)
    # Clean up whitespace, drop empties
    return [p.strip() for p in parts if p.strip()]


def chunk_text(text: str) -> list:
    """
    Split a module's full text into chunks of ~TARGET_WORDS words.
    Keeps paragraphs whole where possible, adds overlap between chunks.
    """
    paragraphs = split_into_paragraphs(text)

    chunks = []
    current_chunk = []          # list of words in the chunk being built
    current_word_count = 0

    for para in paragraphs:
        para_words = para.split()
        para_len = len(para_words)

        # If adding this paragraph would overflow, close the current chunk first
        if current_word_count + para_len > MAX_WORDS and current_chunk:
            chunks.append(" ".join(current_chunk))
            # Start the next chunk with an overlap from the end of this one
            overlap = current_chunk[-OVERLAP_WORDS:]
            current_chunk = list(overlap)
            current_word_count = len(current_chunk)

        # Add the paragraph to the current chunk
        current_chunk.extend(para_words)
        current_word_count += para_len

        # If we've comfortably hit the target, close the chunk
        if current_word_count >= TARGET_WORDS:
            chunks.append(" ".join(current_chunk))
            overlap = current_chunk[-OVERLAP_WORDS:]
            current_chunk = list(overlap)
            current_word_count = len(current_chunk)

    # Don't forget the last partial chunk
    if current_chunk and len(current_chunk) > OVERLAP_WORDS:
        chunks.append(" ".join(current_chunk))

    return chunks


# --- Quick test when run directly ---
if __name__ == "__main__":
    import os
    from document_reader import read_document

    folder = "course_notes"
    files = sorted(os.listdir(folder))

    total_chunks = 0
    print("Chunking all modules:\n")

    for f in files:
        path = os.path.join(folder, f)
        text = read_document(path)
        chunks = chunk_text(text)
        total_chunks += len(chunks)

        # Show stats for this module
        avg_words = sum(len(c.split()) for c in chunks) // len(chunks) if chunks else 0
        print(f"📄 {f}")
        print(f"   {len(text.split()):,} words  →  {len(chunks)} chunks  (avg {avg_words} words/chunk)")

    print(f"\n✅ Total: {total_chunks} chunks across {len(files)} modules")

    # Show one example chunk so you can see what a chunk looks like
    print("\n" + "=" * 60)
    print("EXAMPLE — first chunk of module_01:")
    print("=" * 60)
    sample_text = read_document(os.path.join(folder, files[0]))
    sample_chunks = chunk_text(sample_text)
    print(sample_chunks[0])
    print("=" * 60)