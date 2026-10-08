from fastapi import FastAPI, Request, HTTPException, Header
import litellm
import os
from dotenv import load_dotenv
import redis
from middleware.circuit_breaker import CircuitBreakerMiddleware
import re

load_dotenv()

# Initialize Redis (assuming local default)
redis_client = redis.Redis(host='localhost', port=6379, db=0)

app = FastAPI(title="LLM Gateway")
app.add_middleware(CircuitBreakerMiddleware, redis_client=redis_client)

PII_PATTERNS = {
    "email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "api_key": r"(sk-[a-zA-Z0-9]{32,})",
    "phone": r"\b\d{10,}\b"
}

def redact(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    for name, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"<{name.upper()}_REDACTED>", text)
    return text

@app.post("/chat/completions")
async def chat_completion(request: Request, provider: str = Header("openai")):
    data = await request.json()
    
    # Log request (redacted)
    print(f"[Request][{provider}]: {redact(str(data))}")
    
    # Map provider to LiteLLM model string
    model_map = {
        "openai": "gpt-4o",
        "anthropic": "claude-3-5-sonnet-20240620",
        "ollama": "ollama/llama3"
    }
    data["model"] = model_map.get(provider, "gpt-4o")
    
    try:
        response = await litellm.acompletion(**data)
        # Log response (redacted)
        print(f"[Response][{provider}]: {redact(str(response))}")
        return response
    except Exception as e:
        print(f"[Error][{provider}]: {redact(str(e))}")
        raise HTTPException(status_code=500, detail=str(e))
