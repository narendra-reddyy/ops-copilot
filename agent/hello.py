import os
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()  # reads ANTHROPIC_API_KEY and MODEL from .env

client = Anthropic()
response = client.messages.create(
    model=os.getenv("MODEL", "claude-sonnet-5-5"),
    max_tokens=1000,
    messages=[{"role": "user", "content": "Say hello to Ops Copilot in one sentence."}],
)

for block in response.content:
    print(f"[{block.type}]")
    if block.type == "text":
        print(block.text)