import os

import requests
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from dotenv import load_dotenv

load_dotenv()

NUMISTA_API = "https://api.numista.com/v3"
CATALOGUE_URL = "https://en.numista.com/catalogue/pieces{}.html"


def _numista(path: str, params: dict | None = None) -> dict:
    key = os.getenv("NUMISTA_API_KEY")
    if not key:
        raise RuntimeError("NUMISTA_API_KEY is not set; see the README.")
    response = requests.get(
        NUMISTA_API + path,
        params={"lang": "en", **(params or {})},
        headers={"Numista-API-Key": key},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def search_coins(query: str) -> str:
    """Search the Numista catalogue for coins and banknotes.

    Args:
        query: Coin or banknote name, country or denomination, for example
            "2 leva 1925" or "Bulgarian stotinka".
    """
    data = _numista("/types", {"q": query.strip(), "count": 20})
    types = data.get("types", [])
    if not types:
        return "No matching coins found."
    return "\n".join(
        f"- [{t['id']}] {t.get('title', '?')}"
        f" ({t.get('issuer', {}).get('name', '?')},"
        f" {t.get('min_year', '?')}-{t.get('max_year', '?')})"
        for t in types
    )


def get_coin(type_id: int) -> str:
    """Return the full catalogue entry for one coin or banknote.

    Args:
        type_id: Numista type id, as returned by search_coins.
    """
    coin = _numista(f"/types/{type_id}")
    fields = [
        coin.get("title", "?"),
        CATALOGUE_URL.format(type_id),
        f"Issuer: {coin.get('issuer', {}).get('name', '?')}",
        f"Years: {coin.get('min_year', '?')}-{coin.get('max_year', '?')}",
        f"Composition: {coin.get('composition', {}).get('text', '?')}",
        f"Weight: {coin.get('weight', '?')} g",
        f"Diameter: {coin.get('size', '?')} mm",
        f"Obverse: {coin.get('obverse', {}).get('description', '')}",
        f"Reverse: {coin.get('reverse', {}).get('description', '')}",
    ]
    return "\n".join(fields)[:4000]


agent = Agent(
    id="1",
    name="Sergio",
    # Free tier: usable without purchased credits (50 requests/day).
    model=OpenRouter(id="nvidia/nemotron-3-ultra-550b-a55b:free", max_tokens=4096),
    # Alternatives, all via OpenRouter -- uncomment one to switch.
    # All of these support tool calling.
    #
    # Paid DeepSeek. Returns HTTP 402 until the account buys credits at
    # https://openrouter.ai/settings/credits
    # model=OpenRouter(id="deepseek/deepseek-v4.1-flash-1017", max_tokens=4096),
    #
    # Other free models confirmed reachable; swap in if the above 429s,
    # since free pools are shared and fluctuate.
    # model=OpenRouter(id="nvidia/nemotron-3.5-lightning:free", max_tokens=4096),
    # model=OpenRouter(id="cohere/north-mini-code:free", max_tokens=4096),
    # model=OpenRouter(id="dots-studio/dots-3-note-preview:free", max_tokens=4096),
    instructions=(
        "You are Sergio, a numismatics assistant. Use the Numista catalogue "
        "tools to answer questions about coins and banknotes. Search first, "
        "then fetch the full entry for the type id that best matches."
    ),
    # debug_mode=True   # note: agno uses debug_mode, not verbose
    add_history_to_context=True,
    db=SqliteDb(db_file="agent.db"),
    tools=[search_coins, get_coin],
)

if __name__ == "__main__":
    try:
        while prompt := input("Ask something: "):
            agent.print_response(prompt)
    except (EOFError, KeyboardInterrupt):
        pass
