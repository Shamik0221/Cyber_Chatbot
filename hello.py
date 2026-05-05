import os
from dotenv import load_dotenv
from groq import Groq

# Load API key from .env
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# Create the Groq client
client = Groq(api_key=api_key)

# Ask a cybersecurity question
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": "Explain what a firewall is in 2 simple sentences for a beginner."}
    ]
)

# Print the response
print("Groq says:")
print(response.choices[0].message.content)
