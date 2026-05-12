import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq
from database import save_message, get_history

# --- Configuration ----------------------------------------------------------

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are CyberMentor, a friendly cybersecurity tutor.

You ONLY answer questions related to cybersecurity topics, including:
- Cybersecurity basics and fundamentals
- Ethical hacking
- Penetration testing
- Networking fundamentals (as they relate to security)
- Cryptography, firewalls, malware, phishing, authentication
- Security tools (Wireshark, Nmap, Burp Suite, etc.)
- Cyber attacks and defenses

If the user asks ANYTHING not related to cybersecurity (cooking, movies,
sports, personal advice, general coding, politics, celebrities, health,
travel, or anything off-topic), you MUST respond with exactly this
message and nothing else:

"I'm CyberMentor, your cybersecurity tutor. I can only help with topics
related to this course — like networking, ethical hacking, or penetration
testing. Could you please ask me something about cybersecurity?"

Keep answers clear, beginner-friendly, and concise (2-4 sentences unless
the user asks for more detail)."""

# --- FastAPI app ------------------------------------------------------------

app = FastAPI(title="CyberMentor API", version="1.0.0")

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


def call_groq(user_query: str) -> str:
    """Send the user's question to Groq and return the AI's reply text."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
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

    # 2. Call Groq
    try:
        reply_text = call_groq(request.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

    # 3. Build & save the assistant message
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
    # For now, just acknowledge.
    return {"status": "received", "messageId": request.messageId}