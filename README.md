# agno-example

A small, working example of an [agno](https://github.com/agno-agi/agno) agent
with the pieces you usually end up needing:

- a model served through [OpenRouter](https://openrouter.ai), with free and paid
  options already configured
- custom Python functions registered as tools
- conversation history persisted to SQLite
- two front ends over one agent: a terminal loop and an HTTP API
- bearer-token auth on the API, and a connection to the agno control plane

Its structure follows [Пищов](https://yalishanda.net/pishtov.html), a
Bulgarian-language walkthrough of the same setup. The example tools query the
[Numista](https://en.numista.com) coin and banknote catalogue through its REST
API, but they are only a demonstration — see
[Replacing the tools](#replacing-the-tools).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- An [OpenRouter](https://openrouter.ai) API key
- A [Numista](https://en.numista.com) API key, for the example tools

## Setup

```bash
uv sync
```

Create a `.env` file in the project root:

```ini
# Required: model access via OpenRouter
OPENROUTER_API_KEY=sk-or-v1-...

# Required by the example tools: Numista catalogue access
NUMISTA_API_KEY=<your Numista API key>

# Required only for the HTTP API: bearer token protecting the endpoints
OS_SECURITY_KEY=<a long random string>
```

Get the Numista key from your account under **Profile → API**; the
[API documentation](https://en.numista.com/api/doc/index.php) describes the
endpoints. The free tier allows a few thousand requests a day, so OpenRouter's
quota runs out long before Numista's does.

Generate a security key with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`.env` is git-ignored.

## Layout

| File | Purpose |
|---|---|
| `agent.py` | the agent: model, tools, instructions, persistence. Also a terminal REPL. |
| `app.py` | wraps the same agent in an AgentOS HTTP server. |
| `agent.db` | SQLite history, created on first run (git-ignored). |

Both front ends import the same `agent` object, so a change in `agent.py`
applies to both.

## Running it

### Terminal

```bash
uv run agent.py
```

```
Ask something: what is the 1925 Bulgarian 2 leva made of?
```

Empty line, `Ctrl-D` or `Ctrl-C` quits.

### HTTP API

```bash
uv run app.py
```

Serves on `http://localhost:7777`. `/health` and the docs at `/docs` are
public; everything else needs the security key:

```bash
KEY=$(grep '^OS_SECURITY_KEY=' .env | cut -d= -f2-)

curl -H "Authorization: Bearer $KEY" \
     -F 'message=what is the 1925 Bulgarian 2 leva made of?' \
     http://localhost:7777/agents/1/runs
```

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /health` | no | liveness check |
| `GET /docs` | no | interactive API docs |
| `GET /config` | yes | agents, models and databases in this OS |
| `GET /agents` | yes | list agents |
| `POST /agents/1/runs` | yes | run the agent (`message` form field) |

`1` is the agent's `id` in `agent.py`.

### agno control plane

Start the server, then add the OS at [os.agno.com](https://os.agno.com) with
endpoint `http://localhost:7777`, pasting the same value as `OS_SECURITY_KEY`
into the **Security Key** field. The control plane calls the OS from your
browser, so `localhost` works without a tunnel.

"Connected but isn't running" while the server is up means the key in the UI
does not match `.env`.

## How tool calling works

```
terminal / HTTP  →  agent  →  OpenRouter  →  model
                      │                        │
                      └──────  tools  ←────────┘
```

1. agno sends your message to the model together with a schema for each tool,
   derived from its **signature and docstring**.
2. The model replies with a tool call rather than prose, e.g.
   `search_coins(query="1925 Bulgaria 2 leva")`.
3. agno runs that function locally and feeds its return value back.
4. The model writes the final answer from that result.

So a tool-using turn costs two model calls, and the model never reaches the
network itself — only your function does.

## Replacing the tools

A tool is a plain function. To swap the example out:

1. Write a function with type-annotated arguments and a docstring. Both are
   read by the model, so describe the arguments precisely — this is what
   decides whether it gets called correctly.

   ```python
   def get_weather(city: str) -> str:
       """Return the current weather for a city.

       Args:
           city: City name, e.g. "Sofia".
       """
       ...
   ```

2. Register it in the `Agent(...)` call:

   ```python
   tools=[get_weather],
   ```

3. Define it **above** the `Agent(...)` call — the list holds references, so a
   function defined further down the file raises `NameError`.

Note that not every model supports tool calling. All the models listed in
`agent.py` do; check `supported_parameters` on OpenRouter before swapping in
another.

## Configuration

In `agent.py`:

- **Model** — `OpenRouter(id=...)`. The default is free-tier; alternatives,
  including paid DeepSeek, are listed as comments.
- **Instructions** — the system prompt.
- **`add_history_to_context=True`** — replays earlier turns so follow-ups work.
- **`debug_mode=True`** — verbose logging, commented out. (agno's parameter is
  `debug_mode`, not `verbose`.)

## Known limits

- **History resets between runs.** `session_id` is not set, so each process
  starts a new session. Rows are still written to `agent.db`; the agent just
  does not read the previous session back. Set `session_id="default"` for
  continuity across restarts.
- **Free-tier quota.** Free OpenRouter models allow 50 requests/day, and a
  tool-using question costs about two — roughly 25 questions a day. Paid models
  need credits on the OpenRouter account, or requests fail with HTTP 402.
- **Free model availability fluctuates.** Shared free pools return HTTP 429
  when saturated; swap in one of the commented alternatives.
- **The example tools need a Numista key.** Without `NUMISTA_API_KEY` the tools
  raise immediately; the agent itself still answers from the model alone.
- **Numista response fields are read defensively.** `get_coin` falls back to
  `?` for anything missing, so a catalogue entry with sparse data degrades
  rather than failing.

## Credits

Based on [Пищов](https://yalishanda.net/pishtov.html) by
[yalishanda](https://yalishanda.net), which covers the `uv` and OpenRouter
setup this project is built on. The tutorial's example tools scrape
gotvach.bg; this repo swaps in the Numista catalogue API instead.
