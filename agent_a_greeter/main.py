import logging
import os

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from greeter_agent import GreeterAgent
from agent_executor import GreeterAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass


secrets_health = {
    "GOOGLE_API_KEY": "OK" if os.getenv("GOOGLE_API_KEY") is not None else "MISSING",
}

capabilities = AgentCapabilities(streaming=True)
skill = AgentSkill(
    id="greet_user",
    name="Greet User",
    description="Greets a user by name with a friendly message.",
    tags=["greeting", "hello", "welcome"],
    examples=[
        "Please greet John",
        "Say hello to Maria",
        "Welcome our guest Alex",
    ],
)
agent_card = AgentCard(
    name="Greeter Agent",
    description=(
        "This agent provides friendly greetings to users. "
        "It's a simple test agent for demonstrating A2A communication."
    ),
    url=os.getenv("HU_APP_URL"),
    version="1.0.0",
    defaultInputModes=GreeterAgent.SUPPORTED_CONTENT_TYPES,
    defaultOutputModes=GreeterAgent.SUPPORTED_CONTENT_TYPES,
    capabilities=capabilities,
    skills=[skill],
)
request_handler = DefaultRequestHandler(
    agent_executor=GreeterAgentExecutor(),
    task_store=InMemoryTaskStore(),
)


server = A2AStarletteApplication(
    agent_card=agent_card,
    http_handler=request_handler,
)


async def _health(request: Request) -> JSONResponse:
    """Handles GET requests for the health endpoint.

    Args:
        request: The incoming Starlette Request object.

    Returns:
        A JSONResponse containing the application health data.
    """
    return JSONResponse(
        {"status": "Greeter Agent is running.", "secrets_health": secrets_health}
    )


app = server.build(
    routes=[
        Route(
            "/health",
            _health,
            methods=["GET"],
            name="health_check",
        )
    ]
)

if __name__ == "__main__":
    import uvicorn

    # Use the PORT environment variable provided by Cloud Run, defaulting to 8081
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8081)))