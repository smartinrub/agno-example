from agno.os import AgentOS
from agno.os.settings import AgnoAPISettings
from dotenv import load_dotenv

from agent import agent

# Load .env before building settings, so OS_SECURITY_KEY is picked up.
load_dotenv()

agent_os = AgentOS(
    agents=[agent],
    # Reads OS_SECURITY_KEY from the environment and requires it as a
    # bearer token on every request: Authorization: Bearer <key>
    settings=AgnoAPISettings(),
)

app = agent_os.get_app()

if __name__ == "__main__":
    agent_os.serve(app="app:app")
