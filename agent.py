import requests
from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://recepti.gotvach.bg"


def _fetch(url: str, params: dict | None = None) -> BeautifulSoup:
    response = requests.get(
        url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def search_recipes(query: str) -> str:
    """Търси рецепти в gotvach.bg и връща пълната първа рецепта и линкове към останалите.

    Args:
        query: Само името на ястието или продукта, например "мусака" или "тиквички".
    """
    page = _fetch(BASE_URL + "/", params={"kw": query.strip()})
    links = page.select("div.rprev a.title")
    if not links:
        return "Няма намерени рецепти."
    results = "\n".join(
        f"- {a.get_text(strip=True)}: {a['href']}" for a in links[:20]
    )
    return f"{get_recipe(links[0]['href'])}\n\nДруги резултати:\n{results}"


def get_recipe(url: str) -> str:
    """Връща съставките и начина на приготвяне на конкретна рецепта от gotvach.bg.

    Args:
        url: Пълният адрес на рецептата, върнат от search_recipes.
    """
    page = _fetch(url)
    title = page.select_one("h1").get_text(strip=True)
    products = page.select_one("section.products")
    products = products.get_text("\n", strip=True) if products else ""
    steps = "\n".join(p.get_text(" ", strip=True) for p in page.select("div.text p.desc"))
    content = f"{products}\n\nНачин на приготвяне:\n{steps}"[:4000]
    return f"{title}\n{url}\n\n{content}"


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
    instructions="You are Sergio, an AI assistant. Answer questions and provide assistance as needed.",
    # debug_mode=True   # note: agno uses debug_mode, not verbose
    add_history_to_context=True,
    db=SqliteDb(db_file="agent.db"),
    tools=[search_recipes, get_recipe],
)

if __name__ == "__main__":
    try:
        while prompt := input("Ask something: "):
            agent.print_response(prompt)
    except (EOFError, KeyboardInterrupt):
        pass
