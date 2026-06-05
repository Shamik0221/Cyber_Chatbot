# CyberMentor — Cybersecurity AI Learning Chatbot

A production-shaped Retrieval-Augmented Generation (RAG) chatbot designed to act
as an embedded tutor inside a cybersecurity e-learning course. The bot answers
questions strictly grounded in the course's own material, transparently falls
back to general cybersecurity knowledge when content is thin, and refuses
off-topic queries through a two-layer safety system.

---

## What It Does

- **Course-grounded answers** — every response cites the source module from the
  10-module course (250+ pages)
- **Three-tier behavior** — course content → general cybersecurity knowledge →
  polite refusal
- **Multi-layer safety** — a fast pre-check ("doorman") plus a system-prompt
  guardrail, both required to pass before answering
- **Adaptive tutoring** — detects how-to questions and offers progressive hints
  (Hint 1 → 2 → 3) instead of immediately giving the answer
- **Mistake diagnosis** — when a student shares a wrong answer, the bot explains
  *where the thinking went wrong*, not just the correct answer
- **Persistent multi-user history** — each student's chat history is stored in
  cloud Postgres and reloads automatically when the widget opens
- **Floating draggable widget** — bot appears as a chat bubble on any course
  page; remembers its position; mobile-responsive

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI + Uvicorn |
| LLM provider | Groq (Llama 3.3 70B main, Llama 3.1 8B for classification) |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local, free, 90MB) |
| Vector store | Chroma (local persistent) |
| Database | Supabase PostgreSQL with `psycopg2` connection pooling |
| Document parsing | `python-docx` + `odfpy` |
| Frontend | HTML + CSS + vanilla JavaScript (floating widget) |

---

## Setup — Clone and Run Locally

### Prerequisites

- Python 3.10 or higher
- Git
- A free Groq account (https://console.groq.com)
- A free Supabase account (https://supabase.com)
- A copy of the course content (10 .docx/.odt files), supplied separately

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Shamik0221/Cyber_Chatbot
cd Cyber_Chatbot

# 2. Create a virtual environment
python -m venv venv

# Windows:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

# 3. Install dependencies (takes 3-8 minutes - PyTorch is large)
pip install -r requirements.txt

# 4. Configure your environment
copy .env.example .env       # Windows
# Then edit .env and fill in your real GROQ_API_KEY and DATABASE_URL

# 5. Set up your Supabase database
# In Supabase SQL editor, run:
#   CREATE TABLE chat_history (
#     id BIGSERIAL PRIMARY KEY,
#     message_id TEXT,
#     user_id TEXT,
#     role TEXT,
#     text TEXT,
#     created_at TIMESTAMPTZ DEFAULT NOW(),
#     metadata JSONB
#   );
#   CREATE INDEX idx_chat_user_time ON chat_history (user_id, created_at DESC);

# 6. Add your course content
# Create a folder called "course_notes" in the project root
# Place 10 module files named module_01.* through module_10.*
mkdir course_notes
# (copy your files into it)

# 7. Run ingestion (one-time, ~5 minutes)
python ingest.py

# 8. Start the server
uvicorn app:app --reload
```

Visit **http://127.0.0.1:8000/widget** to see the floating chatbot.

---

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Full-page fallback chat UI |
| GET | `/widget` | Floating widget chat UI |
| POST | `/chat` | Main conversation endpoint |
| POST | `/hint` | Generate 3 progressive hints for a how-to question |
| GET | `/history?userId=X&limit=N` | Load past messages for a user |
| POST | `/feedback` | Submit thumbs up/down |
| GET | `/docs` | Swagger UI for interactive API testing |

---

## Notes

- **Never commit `.env`** — it contains API keys. Already excluded via .gitignore.
- **Course content is not in this repo** — supplied separately.
- **Each developer needs their own Groq key and Supabase project.** Free tiers cover everything.
- **The Chroma vector database (`chroma_db/`) is regenerated locally** via `ingest.py`.

---

## Project Phases

- Phase 0 — Prototype (done)
- Phase 1 — Production backend (done)
- Phase 2 — Floating widget (done)
- Phase 3 — RAG (done)
- Phase 4 — Smart tutoring: doorman + hints + mistake diagnosis (done)
- Phase 5 — Feedback loop (next)
- Phase 6 — Polish + monitoring
- Phase 7 — Cloud deployment