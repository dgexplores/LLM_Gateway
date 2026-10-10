# LLM_Gateway

FastAPI gateway routing `/chat/completions` to multiple LLM providers via LiteLLM, with PII-redacted logging and a Redis circuit breaker.

Status: prototype. Core routing works. Not prod-ready (no auth, no rate limiting, no persistent logging).

## What it does

- `POST /chat/completions` with `provider` header (`openai` | `anthropic` | `ollama`). Maps to `gpt-4o`, `claude-3-5-sonnet-20240620`, `ollama/llama3` in `main.py`.
- Redacts email / API key / phone patterns from request, response, and error logs before printing.
- `CircuitBreakerMiddleware` returns 503 when Redis key `cb_status` is `OPEN`. Opens after 5 failures, 30s sleep window.

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | FastAPI app, provider map, redact + LiteLLM call |
| `redact.py` | Standalone PII redact + inline self-test |
| `middleware/circuit_breaker.py` | Redis failure counter + open-circuit guard |
| `requirements.txt` | fastapi, uvicorn, litellm, redis, python-dotenv, sqlalchemy, psycopg2-binary |
| `.env.example` | Required env keys, no secrets |

## Run

```bash
pip install -r requirements.txt
cp .env.example .env   # fill OPENAI_API_KEY / ANTHROPIC_API_KEY
redis-server           # must be on localhost:6379, no fallback yet
uvicorn main:app --reload
```

Test redact:

```bash
python redact.py  # expects "Redaction tests passed"
```

## Limitations

- Redis hardcoded `localhost:6379`, crashes when down.
- Redact logic duplicated in `main.py` and `redact.py`.
- `sqlalchemy` / `psycopg2-binary` listed but unused, no DB logging.
- Breaker `failure_count` never resets, no half-open probe.
- No auth, rate limiting, retry, cost tracking, Dockerfile, CI.
