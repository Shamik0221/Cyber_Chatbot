import os
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
    """Current time as ISO8601 string in UTC, e.g. '2026-05-06T12:34:56.789Z'"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
           f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def new_message_id(prefix: str = "msg") -> str:
    """Generate a unique message ID like 'msg-3f2a1b8c'."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def call_groq(user_query: str, course_context: str, used_course_material: bool) -> str:
    """
    Send the user's question to Groq. If course material was retrieved,
    include it; otherwise tell the model to use general cybersecurity knowledge.
    """
    if used_course_material:
        # Course material was found — include it for grounded answers
        user_message = (
            f"Course Material:\n"
            f"{course_context}\n\n"
            f"Student Question:\n"
            f"{user_query}"
        )
    else:
        # No course material — explicitly tell the model to fall back
        user_message = (
            f"(NOTE: No relevant course material was retrieved for this question. "
            f"If the question is about cybersecurity, answer it using your general "
            f"cybersecurity knowledge and end with the line: "
            f"'Source: General cybersecurity knowledge (not in course)'. "
            f"If it is not about cybersecurity, refuse as instructed.)\n\n"
            f"Student Question:\n"
            f"{user_query}"
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


# --- Request/Response models (the "shape" of API data) ----------------------

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


class FeedbackRequest(BaseModel):
    userId: str
    messageId: str
    rating: int  # 1 = thumbs up, -1 = thumbs down
    comment: Optional[str] = None


# --- Endpoints --------------------------------------------------------------

@app.get("/")
def home():
    """Serve the chat UI."""
    return FileResponse("index.html")


@app.get("/widget")
def widget_demo():
    """Serve the new floating-widget chat (Phase 2)."""
    return FileResponse("widget.html")


@app.post("/chat")
def chat(request: ChatRequest):
    """Production-shape chat endpoint. Saves both messages to DB."""
    if not request.userId or not request.query:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing userId or query", "code": "ERR_BAD_REQUEST"},
        )

    start_time = datetime.now(timezone.utc)
    metadata_dict = request.metadata.dict() if request.metadata else None

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

    # 2. Retrieve relevant course chunks
    retrieval = retrieve(request.query, n_results=4)

    if retrieval["has_good_match"]:
        # Course material found — bundle chunks with their module labels
        labelled_chunks = []
        for module, chunk in zip(retrieval["modules"], retrieval["chunks"]):
            labelled_chunks.append(f"[From {module}]\n{chunk}")
        course_context = "\n\n---\n\n".join(labelled_chunks)
        used_course_material = True
    else:
        # No good match — bot will fall back to general knowledge
        course_context = ""
        used_course_material = False

    # 3. Call Groq with the question + retrieved chunks (or none)
    try:
        reply_text = call_groq(request.query, course_context, used_course_material)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    # 4. Build & save the assistant message
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

    processing_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

    return {
        "userMessage": user_message,
        "assistantMessage": assistant_message,
        "timing": {"processingMs": processing_ms},
    }


@app.get("/history")
def history(userId: str, limit: int = 15):
    """Return last N messages for a user from the database."""
    if not userId:
        raise HTTPException(
            status_code=400,
            detail={"error": "Missing userId", "code": "ERR_BAD_REQUEST"},
        )
    return get_history(userId, limit)


@app.post("/feedback")
def feedback(request: FeedbackRequest):
    """Accept thumbs up/down on AI replies. (Stub — DB wiring comes in Phase 5.)"""
    if request.rating not in (1, -1):
        raise HTTPException(
            status_code=400,
            detail={"error": "rating must be 1 or -1", "code": "ERR_BAD_REQUEST"},
        )
    return {"status": "received", "messageId": request.messageId}