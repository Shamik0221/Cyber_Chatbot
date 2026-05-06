.\venv\Scripts\Activate.ps1import os
from dotenv import load_dotenv
from groq import Groq

# Load API key from .env
load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# The model we'll use (fast and free on Groq)
MODEL = "llama-3.3-70b-versatile"

# This is the "personality" and rules of our chatbot
SYSTEM_PROMPT = """You are CyberMentor, a friendly cybersecurity tutor.

You ONLY answer questions related to cybersecurity topics, including:
- Cybersecurity basics and fundamentals
- Ethical hacking
- Penetration testing
- Networking fundamentals (as they relate to security)
- Cryptography, firewalls, malware, phishing, authentication
- Security tools (Wireshark, Nmap, Burp Suite, etc.)
- Cyber attacks and defenses

If the user asks ANYTHING not related to cybersecurity (for example:
cooking, movies, sports, personal advice, general coding, politics,
celebrities, health, travel, or anything off-topic), you MUST respond
with exactly this message and nothing else:

"I'm CyberMentor, your cybersecurity tutor. I can only help with topics
related to this course,like networking, ethical hacking, or penetration
testing. Could you please ask me something about cybersecurity?"

Keep answers clear, beginner-friendly, and concise (2-4 sentences unless
the user asks for more detail)."""


def ask_bot(user_question):
    """Send the user's question to Groq and get an answer."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_question}
        ],
        temperature=0.3,  # lower = more focused/consistent answers
    )
    return response.choices[0].message.content


def main():
    print("=" * 60)
    print("  CyberMentor — Your Cybersecurity Learning Assistant")
    print("=" * 60)
    print("Ask me anything about cybersecurity!")
    print("Type 'quit' or 'exit' to end the chat.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "bye"]:
            print("CyberMentor: Goodbye! Keep learning, stay secure. 🔒")
            break

        if not user_input:
            continue

        try:
            answer = ask_bot(user_input)
            print(f"\nCyberMentor: {answer}\n")
        except Exception as e:
            print(f"\n[Error talking to AI: {e}]\n")


if __name__ == "__main__":
    main()