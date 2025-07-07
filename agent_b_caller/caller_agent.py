import json
import os
import httpx
from typing import Any, AsyncIterable, Optional
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import asyncio


async def call_greeter_agent(name: str) -> str:
    """
    Call Agent A (Greeter Agent) to get a greeting for someone.
    
    Args:
        name (str): The name of the person to greet.
        
    Returns:
        str: The greeting response from Agent A.
    """
    agent_a_url = os.getenv("AGENT_A_URL")
    if not agent_a_url:
        return "Error: AGENT_A_URL is not configured. Cannot call Agent A."
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Add Clerk token if available
    clerk_token = os.getenv("CLERK_TOKEN")
    if clerk_token:
        headers["Authorization"] = f"Bearer {clerk_token}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Prepare the request to Agent A
            request_data = {
                "query": f"Please greet {name}",
                "session_id": "test-session",
            }
            
            # Call Agent A's process endpoint
            response = await client.post(
                f"{agent_a_url}/process",
                json=request_data,
                headers=headers,
            )
            
            if response.status_code == 200:
                result = response.json()
                # Extract the actual greeting from the response
                if isinstance(result, dict):
                    if "content" in result:
                        return f"Agent A responded: {result['content']}"
                    elif "response" in result:
                        return f"Agent A responded: {result['response']}"
                    else:
                        return f"Agent A responded with: {json.dumps(result)}"
                else:
                    return f"Agent A responded: {result}"
            else:
                return f"Error calling Agent A: HTTP {response.status_code} - {response.text}"
                
    except httpx.TimeoutException:
        return "Error: Timeout while calling Agent A. The agent might be unavailable."
    except Exception as e:
        return f"Error calling Agent A: {str(e)}"


class CallerAgent:
    """An agent that demonstrates A2A communication by calling another agent."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
    
    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = "caller_agent_user"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
    
    def get_processing_message(self) -> str:
        return "Calling the Greeter Agent..."
    
    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the Caller agent using OpenAI."""
        return LlmAgent(
            model=LiteLlm(model="openai/gpt-4"),  # Using OpenAI GPT-4
            name="caller_agent",
            description=(
                "This agent demonstrates A2A communication by calling another agent (Greeter Agent). "
                "It's a test agent for validating agent-to-agent interactions."
            ),
            instruction="""
You are a caller agent that demonstrates agent-to-agent (A2A) communication. Your job is to call the Greeter Agent (Agent A) when someone wants to greet a person.

When someone asks you to get a greeting for a person, use the `call_greeter_agent` tool to communicate with Agent A.

Instructions:
1. When asked to get a greeting, extract the person's name from the request
2. Use the `call_greeter_agent` tool with that name
3. Report back the response from Agent A
4. If there's an error, explain what went wrong

Examples:
- "Ask the greeter to say hello to John" -> Use call_greeter_agent("John")
- "Get a greeting for Maria from the other agent" -> Use call_greeter_agent("Maria")
- "Call the greeter agent to welcome Alex" -> Use call_greeter_agent("Alex")

Always clearly indicate that you're demonstrating A2A communication and report the full response from Agent A.
""",
            tools=[
                call_greeter_agent,
            ],
        )
    
    async def stream(self, query, session_id) -> AsyncIterable[dict[str, Any]]:
        session = await self._runner.session_service.get_session(
            app_name=self._agent.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        content = types.Content(role="user", parts=[types.Part.from_text(text=query)])
        if session is None:
            session = await self._runner.session_service.create_session(
                app_name=self._agent.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        async for event in self._runner.run_async(
            user_id=self._user_id, session_id=session.id, new_message=content
        ):
            if event.is_final_response():
                response = ""
                if event.content and event.content.parts:
                    # Handle mixed responses (text + function calls)
                    text_parts = [p.text for p in event.content.parts if p.text]
                    function_parts = [
                        p.function_response.model_dump()
                        for p in event.content.parts
                        if p.function_response
                    ]
                    
                    if text_parts and function_parts:
                        # Mixed response: combine text and function data
                        response = {
                            "text": "\n".join(text_parts),
                            "function_data": (
                                function_parts[0] if function_parts else None
                            ),
                        }
                    elif text_parts:
                        # Text only response
                        response = "\n".join(text_parts)
                    elif function_parts:
                        # Function only response
                        response = function_parts[0]
                    else:
                        response = ""
                
                yield {
                    "is_task_complete": True,
                    "content": response,
                }
            else:
                yield {
                    "is_task_complete": False,
                    "updates": self.get_processing_message(),
                }