import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from groq import Groq

# Load environment variables
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


# Create the web app
app = FastAPI()

# Allow the browser to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Define the shape of incoming messages
class ChatRequest(BaseModel):
    message: str


# The /chat endpoint — receives a question, returns the AI answer
@app.post("/chat")
def chat(request: ChatRequest):
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.message}
        ],
        temperature=0.3,
    )
    return {"reply": response.choices[0].message.content}


# Serve the frontend HTML file at the root URL
@app.get("/")
def home():
    return FileResponse("index.html")