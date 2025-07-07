import json
from typing import Any, AsyncIterable, Optional
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


def greet(name: str) -> str:
    """
    Greet a person by name with a friendly message.
    
    Args:
        name (str): The name of the person to greet.
        
    Returns:
        str: A greeting message.
    """
    return f"Hello {name}! This is Agent A (Greeter) responding. I hope you're having a wonderful day!"


class GreeterAgent:
    """An agent that provides friendly greetings."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
    
    def __init__(self):
        self._agent = self._build_agent()
        self._user_id = "greeter_agent_user"
        self._runner = Runner(
            app_name=self._agent.name,
            agent=self._agent,
            artifact_service=InMemoryArtifactService(),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
        )
    
    def get_processing_message(self) -> str:
        return "Preparing a friendly greeting..."
    
    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the Greeter agent using OpenAI."""
        return LlmAgent(
            model=LiteLlm(model="openai/gpt-4"),  # Using OpenAI GPT-4
            name="greeter_agent",
            description=(
                "This agent provides friendly greetings to users. "
                "It's a simple test agent for demonstrating A2A communication."
            ),
            instruction="""
You are a friendly greeting agent. Your job is to greet people warmly and make them feel welcome.

When someone asks you to greet a person, use the `greet` tool to generate a personalized greeting.

Instructions:
1. When asked to greet someone, extract the person's name from the request
2. Use the `greet` tool with that name
3. You can add additional friendly commentary around the greeting if appropriate
4. Always be warm, welcoming, and positive

Examples:
- "Please greet John" -> Use greet("John")
- "Say hello to Maria" -> Use greet("Maria")
- "Welcome our guest Alex" -> Use greet("Alex")
""",
            tools=[
                greet,
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