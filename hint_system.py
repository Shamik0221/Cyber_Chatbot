"""
hint_system.py
Decides if a question is a "how-to" / problem-solving question
(deserves hints) and generates 3 progressive hints in one Groq call.
"""

import os
import json
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Same fast small model as the doorman — classification is light work
CLASSIFIER_MODEL = "llama-3.1-8b-instant"
# Bigger model for hint generation — needs to be thoughtful
HINTS_MODEL = "llama-3.3-70b-versatile"


# ---- Part 1: Decide if a question deserves hints --------------------------

CLASSIFIER_PROMPT = """You are a classifier. Given a student's cybersecurity question,
decide if it is a "how-to / problem-solving" question that benefits from progressive
hints, or a "what-is / definitional" question that just needs a direct answer.

HOW_TO examples:
- "How would I detect a phishing email?"
- "Walk me through finding open ports on a network"
- "How do I tell if a website is vulnerable to SQL injection?"
- "Help me approach this lab on privilege escalation"

DEFINITIONAL examples:
- "What is phishing?"
- "Define encryption"
- "Explain the OSI model"
- "What does TLS stand for?"

Respond with EXACTLY one word, nothing else:
HOW_TO
or
DEFINITIONAL
"""


def is_how_to(question: str) -> bool:
    """Return True if the question is problem-solving, False if it's definitional."""
    response = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    answer = response.choices[0].message.content.strip().upper()
    return answer.startswith("HOW_TO")


# ---- Part 2: Generate 3 progressive hints in one call ---------------------

HINTS_PROMPT = """You are CyberMentor, a cybersecurity tutor. The student has asked
a "how-to / problem-solving" question. Instead of giving the full answer immediately,
you will provide THREE progressive hints, from gentle nudge to near-complete answer.

You will also be given relevant Course Material. Ground your hints in that material
where possible. If no course material is provided, use your general cybersecurity
knowledge.

Return your response as STRICT JSON with this exact shape and nothing else:

{
  "hint1": "A small nudge — point the student toward the right concept or area to think about. 1-2 sentences. Do NOT give the answer yet.",
  "hint2": "A bigger hint — name the technique or tool involved, give a concrete clue about HOW it works. 2-3 sentences. Still not the full answer.",
  "hint3": "The full explanation. 3-5 sentences. Complete answer with reasoning."
}

Rules:
- Each hint should build on the previous one.
- Hint 1 should make the student think, not give it away.
- Hint 3 should be a satisfying complete answer.
- Respond with ONLY the JSON object, no extra text before or after."""


def generate_hints(question: str, course_context: str = "") -> dict:
    """
    Generate three progressive hints for a how-to question.
    Returns dict with keys 'hint1', 'hint2', 'hint3'.
    Falls back gracefully if JSON parsing fails.
    """
    user_message = (
        f"Course Material:\n{course_context if course_context else '(none provided)'}\n\n"
        f"Student Question:\n{question}"
    )

    response = _client.chat.completions.create(
        model=HINTS_MODEL,
        messages=[
            {"role": "system", "content": HINTS_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )
    raw = response.choices[0].message.content.strip()

    # Try to extract a JSON object even if the model wrapped it in extra text
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            return {
                "hint1": data.get("hint1", "").strip(),
                "hint2": data.get("hint2", "").strip(),
                "hint3": data.get("hint3", "").strip(),
            }
        except json.JSONDecodeError:
            pass

    # Fallback if the model didn't return clean JSON
    return {
        "hint1": "Think about what tools or techniques cybersecurity professionals use for this kind of problem.",
        "hint2": "Consider the typical workflow: information gathering, then identifying targets, then testing.",
        "hint3": raw,  # at least show the model's reply rather than nothing
    }


# ---- Quick test when run directly -----------------------------------------

if __name__ == "__main__":
    test_questions = [
        ("What is phishing?", False),                # definitional → no hints
        ("How would I detect a phishing email?", True),  # how-to → hints
        ("Define encryption", False),
        ("How do I find open ports on a target system?", True),
    ]

    print("\n=== Classifier test ===\n")
    for q, expected_how_to in test_questions:
        actual = is_how_to(q)
        ok = "✅" if actual == expected_how_to else "❌"
        label = "HOW_TO" if actual else "DEFINITIONAL"
        print(f"  {ok} '{q}' → {label}")

    print("\n=== Hint generation test ===\n")
    sample_q = "How would I detect a phishing email?"
    hints = generate_hints(sample_q)
    print(f"Question: {sample_q}\n")
    print(f"--- HINT 1 ---\n{hints['hint1']}\n")
    print(f"--- HINT 2 ---\n{hints['hint2']}\n")
    print(f"--- HINT 3 ---\n{hints['hint3']}\n")