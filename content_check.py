"""content_check.py — checks which modules mention a given phrase."""
import os
from document_reader import read_document

PHRASES = ["CIA triad", "confidentiality", "integrity", "availability"]

folder = "course_notes"
for f in sorted(os.listdir(folder)):
    text = read_document(os.path.join(folder, f)).lower()
    print(f"\n{f}:")
    for phrase in PHRASES:
        count = text.count(phrase.lower())
        mark = "✅" if count > 0 else "❌"
        print(f"  {mark} '{phrase}' appears {count} times")