from fastapi import FastAPI, Request, HTTPException, Header
import litellm
import os
from dotenv import load_dotenv
import redis
from middleware.circuit_breaker import CircuitBreakerMiddleware
from redact import redact

load_dotenv()

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    db=0,
)

app = FastAPI(title="LLM Gateway")
app.add_middleware(CircuitBreakerMiddleware, redis_client=redis_client)

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
