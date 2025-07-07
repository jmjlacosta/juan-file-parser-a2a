"""Agent executor for the Greeter Agent."""

import json
import logging
import traceback
import uuid
from typing import Any, AsyncIterable

from a2a.server.agent_executor import A2AAgentExecutor, InternalError
from a2a.server.responses import StreamingMessage
from a2a.types import Request

from greeter_agent import GreeterAgent

logger = logging.getLogger(__name__)


class GreeterAgentExecutor(A2AAgentExecutor):
    """Executor for the Greeter Agent."""

    def __init__(self):
        super().__init__()
        self._agent = GreeterAgent()

    async def execute(self, request: Request) -> AsyncIterable[StreamingMessage]:
        """Execute the agent with the given request.

        Args:
            request: The incoming request.

        Yields:
            StreamingMessage: Messages from the agent execution.
        """
        logger.info(f"Executing GreeterAgent with request: {request}")
        
        try:
            # Extract query from request
            if hasattr(request, 'messages') and request.messages:
                query = request.messages[-1].content
            elif hasattr(request, 'query'):
                query = request.query
            else:
                query = str(request)
            
            # Generate session ID
            session_id = str(uuid.uuid4())
            
            # Stream responses from agent
            async for event in self._agent.stream(query, session_id):
                if event.get("is_task_complete"):
                    content = event.get("content", "")
                    if isinstance(content, dict):
                        # If content is a dict, convert to JSON string
                        yield StreamingMessage(
                            type="task",
                            content=json.dumps(content),
                        )
                    else:
                        yield StreamingMessage(
                            type="task",
                            content=str(content),
                        )
                else:
                    # Progress update
                    yield StreamingMessage(
                        type="progress",
                        content=event.get("updates", "Processing..."),
                    )
                    
        except Exception as e:
            logger.error(f"Error in GreeterAgentExecutor: {str(e)}")
            logger.error(traceback.format_exc())
            raise InternalError(f"Agent execution failed: {str(e)}")