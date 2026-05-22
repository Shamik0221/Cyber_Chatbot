"""
document_reader.py
Reads plain text out of .docx and .odt course files.
"""

import os
from docx import Document
from odf.opendocument import load
from odf.text import P


def read_docx(file_path: str) -> str:
    """Extract all text from a .docx file."""
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs]
    return "\n".join(p for p in paragraphs if p.strip())


def read_odt(file_path: str) -> str:
    """Extract all text from a .odt file."""
    doc = load(file_path)
    paragraphs = doc.getElementsByType(P)
    texts = []
    for para in paragraphs:
        text = str(para)
        if text.strip():
            texts.append(text)
    return "\n".join(texts)


def read_document(file_path: str) -> str:
    """Auto-detect the file type and read it."""
    if file_path.lower().endswith(".docx"):
        return read_docx(file_path)
    elif file_path.lower().endswith(".odt"):
        return read_odt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_path}")


if __name__ == "__main__":
    folder = "course_notes"
    files = sorted(os.listdir(folder))
    print(f"Found {len(files)} files in '{folder}':\n")
    for f in files:
        path = os.path.join(folder, f)
        try:
            text = read_document(path)
            word_count = len(text.split())
            preview = text[:120].replace("\n", " ")
            print(f"✅ {f}")
            print(f"   Words: {word_count:,}")
            print(f"   Preview: {preview}...")
            print()
        except Exception as e:
            print(f"❌ {f} — ERROR: {e}\n")