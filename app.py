import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import Groq
from database import save_message, get_history
from retriever import retrieve
from guardrail import is_safe
from hint_system import is_how_to, generate_hints, is_mistake_diagnosis, diagnose_mistake

# --- Configuration ----------------------------------------------------------

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are CyberMentor, a friendly cybersecurity tutor for an online course.

You answer cybersecurity-related questions for students. Use this priority order:

1. PREFER THE COURSE MATERIAL:
   If the "Course Material" section below the student's question contains the
   answer, answer FROM that material. End with a line: "Source: ModuleXX"
   (using the exact module name shown in the material).

2. FALL BACK TO GENERAL CYBERSECURITY KNOWLEDGE:
   If the course material is missing, thin, or marked "(no relevant course
   material found)" — but the question is still about cybersecurity, ethical
   hacking, networking, encryption, security tools, or any related technical
   topic — answer it using your general cybersecurity knowledge.
   In that case, end with the line: "Source: General cybersecurity knowledge
   (not in course)".

3. REFUSE OFF-TOPIC QUESTIONS:
   If the question is not about cybersecurity in any way (e.g., cooking,
   sports, movies, personal advice, general coding unrelated to security),
   reply with exactly:
   "I'm CyberMentor, your cybersecurity tutor. I can only help with topics
   related to cybersecurity. Could you please ask me something related to
   the course?"

General rules:
- Keep answers clear, beginner-friendly, and concise (2-5 sentences unless
  more detail is asked).
- Never invent module numbers that don't appear in the provided material.
- Never claim something is "in the course" if it isn't.
"""

# --- FastAPI app ------------------------------------------------------------

app = FastAPI(title="CyberMentor API", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helper functions -------------------------------------------------------

def now_iso() -> str:
    """Current time as ISO8601 string in UTC."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def new_message_id(prefix: str = "msg") -> str:
    """Generate a unique message ID like 'msg-3f2a1b8c'."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def call_groq(user_query: str, course_context: str, used_course_material: bool) -> str:
    """Send the user's question to Groq with optional retrieved course context."""
    if used_course_material:
        user_message = (
            f"Course Material:\n{course_context}\n\n"
            f"Student Question:\n{user_query}"
        )
    else:
        user_message = (
            f"(NOTE: No relevant course material was retrieved for this question. "
            f"If the question is about cybersecurity, answer it using your general "
            f"cybersecurity knowledge and end with the line: "
            f"'Source: General cybersecurity knowledge (not in course)'. "
            f"If it is not about cybersecurity, refuse as instructed.)\n\n"
            f"Student Question:\n{user_query}"
        )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


# --- Request/Response models -----------------------------------------------

class ChatMetadata(BaseModel):
    courseId: Optional[str] = None
    chapterId: Optional[str] = None
    topicId: Optional[str] = None
    pageUrl: Optional[str] = None
    videoTimestampSec: Optional[int] = None


class ChatRequest(BaseModel):
    userId: str
    query: str
    metadata: Optional[ChatMetadata] = None
    clientMessageId: Optional[str] = None


class HintRequest(BaseModel):
    userId: str
    question: str
    courseContext: Optional[str] = None


class FeedbackRequest(BaseModel):
    userId: str
    messageId: str
    rating: int
    comment: Optional[str] = None


# --- Endpoints --------------------------------------------------------------

@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/widget")
def widget_demo():
    return FileResponse("widget.html")


@app.post("/chat")
def chat(request: ChatRequest):
    """Production-shape chat endpoint with timing instrumentation, doorman, and smart hint routing."""
    if not request.userId or not request.query:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing userId or query", "code": "ERR_BAD_REQUEST"},
        )

    start_time = datetime.now(timezone.utc)
    metadata_dict = request.metadata.dict() if request.metadata else None

    # ----- Timing instrumentation -----
    timings = {}
    _t = [time.time()]
    def _mark(label):
        timings[label] = round((time.time() - _t[0]) * 1000)
        _t[0] = time.time()

    # 1. Build & save the user message
    user_message = {
        "messageId": new_message_id("user"),
        "createdAt": now_iso(),
        "role": "user",
        "text": request.query,
    }
    save_message(
        message_id=user_message["messageId"],
        user_id=request.userId,
        role="user",
        text=request.query,
        metadata=metadata_dict,
    )
    _mark("save_user_msg")

    # 2. DOORMAN — pre-check the question
    safety = is_safe(request.query)
    _mark("doorman")

    if not safety["safe"]:
        refusal_text = (
            "I'm CyberMentor, your cybersecurity tutor. I can only help with "
            "topics related to cybersecurity. Could you please ask me something "
            "related to the course?"
        )
        assistant_message = {
            "messageId": new_message_id("assist"),
            "createdAt": now_iso(),
            "role": "assistant",
            "text": refusal_text,
            "topicHint": None,
            "sources": [],
            "confidence": None,
        }
        save_message(
            message_id=assistant_message["messageId"],
            user_id=request.userId,
            role="assistant",
            text=refusal_text,
            metadata=metadata_dict,
        )
        _mark("save_assistant_msg")

        processing_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        print(f"⏱  TIMINGS (ms) [blocked]: {timings} | total {processing_ms}")
        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "timing": {"processingMs": processing_ms},
        }
    # 2a. Mistake-diagnosis check — is the student showing us a wrong answer?
    is_mistake = is_mistake_diagnosis(request.query)
    _mark("classify_mistake")

    if is_mistake:
        # Retrieve course material — diagnoses benefit from grounding
        retrieval = retrieve(request.query, n_results=4)
        _mark("retrieve")

        if retrieval["has_good_match"]:
            labelled_chunks = []
            for module, chunk in zip(retrieval["modules"], retrieval["chunks"]):
                labelled_chunks.append(f"[From {module}]\n{chunk}")
            course_context = "\n\n---\n\n".join(labelled_chunks)
        else:
            course_context = ""

        # Generate the structured 3-paragraph diagnosis
        diagnosis_text = diagnose_mistake(request.query, course_context)
        _mark("diagnose_mistake")

        assistant_message = {
            "messageId": new_message_id("assist"),
            "createdAt": now_iso(),
            "role": "assistant",
            "text": diagnosis_text,
            "topicHint": "explain_mistake",
            "sources": [],
            "confidence": None,
        }
        save_message(
            message_id=assistant_message["messageId"],
            user_id=request.userId,
            role="assistant",
            text=diagnosis_text,
            metadata=metadata_dict,
        )
        _mark("save_assistant_msg")

        processing_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        print(f"⏱  TIMINGS (ms) [mistake]: {timings} | total {processing_ms}")
        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "timing": {"processingMs": processing_ms},
        }

    
    # 2b. Smart detection — is this a how-to question?
    how_to = is_how_to(request.query)
    _mark("classify_how_to")

    # 3. Retrieve relevant course chunks
    retrieval = retrieve(request.query, n_results=4)
    _mark("retrieve")

    if retrieval["has_good_match"]:
        labelled_chunks = []
        for module, chunk in zip(retrieval["modules"], retrieval["chunks"]):
            labelled_chunks.append(f"[From {module}]\n{chunk}")
        course_context = "\n\n---\n\n".join(labelled_chunks)
        used_course_material = True
    else:
        course_context = ""
        used_course_material = False

    # If this is a how-to question, generate hints instead of a direct answer
    if how_to:
        hints = generate_hints(request.query, course_context)
        _mark("generate_hints")

        reply_text = (
            "This looks like a problem-solving question. I can walk you through "
            "it with progressive hints, or just give the full answer. "
            "Click 'Show hint' below to start, or 'Show full answer' to skip ahead."
        )

        assistant_message = {
            "messageId": new_message_id("assist"),
            "createdAt": now_iso(),
            "role": "assistant",
            "text": reply_text,
            "topicHint": "how_to",
            "sources": [],
            "confidence": None,
            "hints": hints,
        }
        save_message(
            message_id=assistant_message["messageId"],
            user_id=request.userId,
            role="assistant",
            text=reply_text,
            metadata=metadata_dict,
        )
        _mark("save_assistant_msg")

        processing_ms = int(
            (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        )
        print(f"⏱  TIMINGS (ms) [how_to]: {timings} | total {processing_ms}")
        return {
            "userMessage": user_message,
            "assistantMessage": assistant_message,
            "timing": {"processingMs": processing_ms},
        }

    # 4. Call Groq for a normal definitional answer
    try:
        reply_text = call_groq(request.query, course_context, used_course_material)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")
    _mark("groq_main")

    # 5. Build & save the assistant message
    assistant_message = {
        "messageId": new_message_id("assist"),
        "createdAt": now_iso(),
        "role": "assistant",
        "text": reply_text,
        "topicHint": None,
        "sources": [],
        "confidence": None,
    }
    save_message(
        message_id=assistant_message["messageId"],
        user_id=request.userId,
        role="assistant",
        text=reply_text,
        metadata=metadata_dict,
    )
    _mark("save_assistant_msg")

    processing_ms = int(
        (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    )
    print(f"⏱  TIMINGS (ms): {timings} | total {processing_ms}")

    return {
        "userMessage": user_message,
        "assistantMessage": assistant_message,
        "timing": {"processingMs": processing_ms},
    }


@app.post("/hint")
def hint(request: HintRequest):
    """Generate three progressive hints for a how-to question."""
    if not request.userId or not request.question:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing userId or question", "code": "ERR_BAD_REQUEST"},
        )

    hints = generate_hints(request.question, request.courseContext or "")

    return {
        "userId": request.userId,
        "question": request.question,
        "hints": hints,
    }


@app.get("/history")
def history(userId: str, limit: int = 15):
    if not userId:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing userId", "code": "ERR_BAD_REQUEST"},
        )
    return get_history(userId, limit)


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    if request.rating not in (1, -1):
        raise HTTPException(
            status_code=400,
            detail={"error": "rating must be 1 or -1", "code": "ERR_BAD_REQUEST"},
        )
    return {"status": "received", "messageId": request.messageId}