"""
hint_system.py
Decides if a question is "how-to" (deserves hints), "mistake diagnosis"
(deserves explanation of misconception), and generates the appropriate response.
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
# Bigger model for generation — needs to be thoughtful
HINTS_MODEL = "llama-3.3-70b-versatile"


# ===========================================================================
# === HOW-TO Classifier =====================================================
# ===========================================================================

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


def is_how_to(question: str, recent_context: str = "") -> bool:
    """Return True if the question is problem-solving, False if it's definitional."""
    user_content = question
    if recent_context:
        user_content = (
            f"Recent conversation:\n{recent_context}\n\n"
            f"New message: {question}"
        )

    response = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    answer = response.choices[0].message.content.strip().upper()
    return answer.startswith("HOW_TO")


# ===========================================================================
# === Generate three progressive hints in one call ==========================
# ===========================================================================

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
    """Generate three progressive hints for a how-to question."""
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

    # Extract JSON even if model wrapped it in extra text
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

    # Fallback
    return {
        "hint1": "Think about what tools or techniques cybersecurity professionals use for this kind of problem.",
        "hint2": "Consider the typical workflow: information gathering, then identifying targets, then testing.",
        "hint3": raw,
    }


# ===========================================================================
# === Mistake Diagnosis Classifier ==========================================
# ===========================================================================

MISTAKE_CLASSIFIER_PROMPT = """You are a classifier. Decide whether a student's
message is a "MISTAKE_DIAGNOSIS" request — meaning the student is sharing an
answer they gave that was wrong (or that they're not sure about) and wants to
understand what they got wrong.

MISTAKE_DIAGNOSIS examples:
- "I answered X but it was marked wrong, why?"
- "I thought Y was the answer but it's not — explain"
- "Got this wrong on my quiz: I said Z. What's the correct reasoning?"
- "My answer was W but the correct one is V — help me understand"

NOT mistake diagnosis (these are regular questions):
- "What is X?"
- "How does Y work?"
- "Why is Z important?"
- General questions, even if phrased as "I don't understand X"

Respond with EXACTLY one word:
MISTAKE
or
NORMAL
"""


def is_mistake_diagnosis(question: str, recent_context: str = "") -> bool:
    """Return True if the student is asking us to diagnose their wrong answer."""
    user_content = question
    if recent_context:
        user_content = (
            f"Recent conversation:\n{recent_context}\n\n"
            f"New message: {question}"
        )

    response = _client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {"role": "system", "content": MISTAKE_CLASSIFIER_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    answer = response.choices[0].message.content.strip().upper()
    return answer.startswith("MISTAKE")


# ===========================================================================
# === Mistake Diagnosis Generator ===========================================
# ===========================================================================

MISTAKE_DIAGNOSIS_PROMPT = """You are CyberMentor, a patient cybersecurity tutor.

The student has shared an answer they gave that was wrong (or that they're
uncertain about). Your job is NOT to just give them the right answer. Your job
is to:

1. Identify what their wrong answer reveals about their thinking.
2. Explain *specifically* where their reasoning went off track.
3. Contrast their wrong answer with the correct concept — what makes it wrong
   and why the correct answer is actually correct.
4. End with a short, supportive note encouraging them.

You will also receive relevant Course Material. Ground your explanation in that
material where possible. If the material is missing, use general cybersecurity
knowledge.

Structure your response in 3 short paragraphs:
- Paragraph 1: Acknowledge their answer and identify the misconception
- Paragraph 2: Explain why their answer is wrong here, and what the correct
  concept is (with the reasoning, not just the label)
- Paragraph 3: One sentence of encouragement + one practical takeaway.

End with: "Source: ModuleXX" if you used course material,
or "Source: General cybersecurity knowledge (not in course)" otherwise.
"""


def diagnose_mistake(question: str, course_context: str = "") -> str:
    """
    Diagnose the student's wrong answer and explain the misconception.
    Returns the explanation as a single text string.
    """
    user_message = (
        f"Course Material:\n{course_context if course_context else '(none provided)'}\n\n"
        f"Student's message (containing their wrong answer):\n{question}"
    )

    response = _client.chat.completions.create(
        model=HINTS_MODEL,
        messages=[
            {"role": "system", "content": MISTAKE_DIAGNOSIS_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


# ===========================================================================
# === Quick test when run directly ==========================================
# ===========================================================================

if __name__ == "__main__":
    classifier_tests = [
        ("What is phishing?", False),
        ("How would I detect a phishing email?", True),
        ("Define encryption", False),
        ("How do I find open ports on a target system?", True),
    ]

    print("\n=== HOW-TO Classifier test ===\n")
    for q, expected_how_to in classifier_tests:
        actual = is_how_to(q)
        ok = "✅" if actual == expected_how_to else "❌"
        label = "HOW_TO" if actual else "DEFINITIONAL"
        print(f"  {ok} '{q}' → {label}")

    print("\n=== MISTAKE Classifier test ===\n")
    mistake_tests = [
        ("What is phishing?", False),
        ("I answered 'use HTTPS' for SQL injection prevention but it was wrong", True),
        ("My quiz answer was 'antivirus' but the correct one is 'IDS' — explain", True),
        ("Explain firewalls", False),
        ("I thought social engineering was just emails but apparently I'm wrong", True),
    ]
    for q, expected_mistake in mistake_tests:
        actual = is_mistake_diagnosis(q)
        ok = "✅" if actual == expected_mistake else "❌"
        label = "MISTAKE" if actual else "NORMAL"
        print(f"  {ok} '{q}' → {label}")

    print("\n=== Mistake Diagnosis test ===\n")
    sample_q = "I answered 'use HTTPS' for the question 'how to prevent SQL injection' but it was marked wrong. Why?"
    print(f"Question: {sample_q}\n")
    explanation = diagnose_mistake(sample_q)
    print(f"--- DIAGNOSIS ---\n{explanation}\n")