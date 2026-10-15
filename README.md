# LLM Gateway

**One endpoint in front of every LLM provider. Your app sends one request, the gateway handles the rest.**

Right now, talking to AI models means signing up everywhere: an OpenAI SDK here, an Anthropic client there, a local Ollama setup for private workloads. Each with its own API shape, its own key, its own failure modes. Swap providers and you rewrite code. Add a provider and you add dependencies. Logs fill up with raw prompts containing customer emails and leaked keys.

LLM Gateway is the thin layer that fixes that.

```
your app  ──►  gateway  ──►  OpenAI (gpt-4o)
   one          one         Anthropic (claude)
   URL +        server      Ollama (local llama3)
   header
```

One `POST /chat/completions`. Set `provider: anthropic` (or `openai`, or `ollama`) as a header. The gateway maps it to the right model, redacts sensitive data from your logs, and shields you from providers that are down.

## Why you need this

| Problem without a gateway | What the gateway does |
| --- | --- |
| Every provider needs its own SDK and integration | One LiteLLM call covers all of them |
| Switching providers means rewriting application code | Change one header, deploy nothing |
| Logs leak customer emails, phone numbers, API keys | Emails, keys and phone numbers become `<EMAIL_REDACTED>` before any log line is written |
| A failing provider gets hammered with retries until your bill explodes | Circuit breaker opens after 5 failures, serves fast 503s for 30s, recovers on its own |
| Local models (Ollama) live on a different code path than cloud ones | Same request format, same endpoint, same logs |

## What's real today

This is a working prototype, not a production service. Be honest with yourself about that line.

**Works:**
- `POST /chat/completions` with a `provider` header, routed to `gpt-4o`, `claude-3-5-sonnet-20240620`, or `ollama/llama3` via LiteLLM
- PII redaction (email, API key, phone patterns) on requests, responses and errors, before they reach stdout
- Redis-backed circuit breaker: 5 failures open the circuit, 30 second sleep window, success resets the counter, unreachable Redis fails open so traffic keeps flowing
- 3 pytest tests covering the breaker, plus an inline redaction self-test
- Zero secrets in the repo (`.env.example` ships empty keys)

**Not built yet (planned, listed here so nobody is surprised):**
- Authentication and rate limiting
- A half-open probe state (after the sleep window the breaker closes fully)
- Persistent logging, cost tracking, retries, Dockerfile, CI

## Quickstart

```bash
git clone https://github.com/dgexplores/LLM_Gateway.git
cd LLM_Gateway
pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY / ANTHROPIC_API_KEY
redis-server                # must run on localhost:6379
uvicorn main:app --reload
```

Send a request:

```bash
curl localhost:8000/chat/completions \
  -H "provider: anthropic" \
  -H "content-type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

What lands in your logs:

```
[Request][anthropic]: {'messages': [{'role': 'user', 'content': 'hello'}]}
```

If that message had contained `alice@corp.com` or an `sk-` key, you would see `<EMAIL_REDACTED>` and `<API_KEY_REDACTED>` instead.

## How it works

```
client  ──►  circuit breaker  ──►  redact + log  ──►  LiteLLM  ──►  provider
              (503 if OPEN)        (stdout safe)      (routing)
```

| File | Role |
| --- | --- |
| `main.py` | FastAPI app: provider map, redaction, LiteLLM call |
| `redact.py` | PII patterns and `redact()`, with a built-in self-test |
| `middleware/circuit_breaker.py` | Redis failure counter and open-circuit guard |
| `docs/index.html` | [Project landing page](https://dgexplores.github.io/LLM_Gateway/) |

## Tests

```bash
python redact.py              # "Redaction tests passed"
python -m pytest tests -q     # 3 passed
```

## Who this is for

Engineers who want a reference implementation for the boring, load-bearing parts of shipping LLM features: provider abstraction, log hygiene, and failure containment. Read the source, fork it, open an issue.

Built in public at [dgexplores/LLM_Gateway](https://github.com/dgexplores/LLM_Gateway).

## License

MIT. See [LICENSE](LICENSE).
