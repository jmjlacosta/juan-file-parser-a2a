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

from caller_agent import CallerAgent
from agent_executor import CallerAgentExecutor
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""
    pass


secrets_health = {
    "STATUS": "No LLM dependencies - ready for A2A testing",
    "AGENT_A_URL": "OK" if os.getenv("AGENT_A_URL") is not None else "MISSING",
}

capabilities = AgentCapabilities(streaming=True)
skill = AgentSkill(
    id="call_greeter",
    name="Call Greeter Agent",
    description="Calls the Greeter Agent (Agent A) to get a greeting for someone.",
    tags=["greeting", "a2a", "communication"],
    examples=[
        "Ask the greeter to say hello to John",
        "Get a greeting for Maria from the other agent",
        "Call the greeter agent to welcome Alex",
    ],
)
agent_card = AgentCard(
    name="Caller Agent",
    description=(
        "This agent demonstrates A2A communication by calling another agent (Greeter Agent). "
        "It's a test agent for validating agent-to-agent interactions."
    ),
    url=os.getenv("HU_APP_URL"),
    version="1.0.0",
    defaultInputModes=CallerAgent.SUPPORTED_CONTENT_TYPES,
    defaultOutputModes=CallerAgent.SUPPORTED_CONTENT_TYPES,
    capabilities=capabilities,
    skills=[skill],
)
request_handler = DefaultRequestHandler(
    agent_executor=CallerAgentExecutor(),
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
        {"status": "Caller Agent is running.", "secrets_health": secrets_health}
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

    # Use the PORT environment variable provided by Cloud Run, defaulting to 8082
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8082)))