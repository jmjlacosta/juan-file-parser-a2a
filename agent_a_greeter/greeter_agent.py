import json
import random
from typing import Any, AsyncIterable, Optional
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
from google.genai import types


# Local cache of greeting IDs for state management
greeting_ids = set()
greeting_history = {}


def create_greeting_form(
    name: Optional[str] = None,
    style: Optional[str] = None,
    message: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a greeting form for customized greetings.
    
    Args:
        name (str): The name to greet. Can be empty.
        style (str): The greeting style (formal/casual/fun). Can be empty.
        message (str): Custom message to include. Can be empty.
        
    Returns:
        dict[str, Any]: A dictionary containing the greeting form data.
    """
    greeting_id = "greeting_" + str(random.randint(1000000, 9999999))
    greeting_ids.add(greeting_id)
    
    form_data = {
        "greeting_id": greeting_id,
        "name": "<person's name>" if not name else name,
        "style": "<formal/casual/fun>" if not style else style,
        "message": "<optional custom message>" if not message else message,
    }
    
    # Store in history
    greeting_history[greeting_id] = form_data
    
    return form_data


def return_greeting_form(
    form_request: dict[str, Any],
    tool_context: ToolContext,
    instructions: Optional[str] = None,
) -> dict[str, Any]:
    """
    Returns a structured JSON object for greeting customization.
    
    Args:
        form_request (dict[str, Any]): The greeting form data.
        tool_context (ToolContext): The context in which the tool operates.
        instructions (str): Instructions for the form.
        
    Returns:
        dict[str, Any]: A JSON dictionary for the form response.
    """
    if isinstance(form_request, str):
        form_request = json.loads(form_request)
    
    tool_context.actions.skip_summarization = True
    tool_context.actions.escalate = True
    
    form_dict = {
        "type": "form",
        "form": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name of the person to greet",
                    "title": "Name",
                },
                "style": {
                    "type": "string",
                    "enum": ["formal", "casual", "fun"],
                    "description": "Style of greeting",
                    "title": "Greeting Style",
                },
                "message": {
                    "type": "string",
                    "description": "Optional custom message to include",
                    "title": "Custom Message",
                },
                "greeting_id": {
                    "type": "string",
                    "description": "Greeting ID for tracking",
                    "title": "Greeting ID",
                },
            },
            "required": ["name", "style", "greeting_id"],
        },
        "form_data": form_request,
        "instructions": instructions or "Please customize your greeting preferences",
    }
    return json.dumps(form_dict)


def generate_greeting(greeting_id: str) -> dict[str, Any]:
    """Generate the actual greeting based on the form data."""
    if greeting_id not in greeting_ids:
        return {
            "greeting_id": greeting_id,
            "status": "Error: Invalid greeting_id.",
        }
    
    # Get the greeting data
    data = greeting_history.get(greeting_id, {})
    name = data.get("name", "Friend")
    style = data.get("style", "casual")
    message = data.get("message", "")
    
    # Generate greeting based on style
    if style == "formal":
        greeting = f"Good day, {name}. I hope this message finds you well."
    elif style == "fun":
        greeting = f"Hey there, {name}! 🎉 Hope you're having an awesome day!"
    else:  # casual
        greeting = f"Hello {name}! This is Agent A (Greeter) responding. I hope you're having a wonderful day!"
    
    if message:
        greeting += f" {message}"
    
    return {
        "greeting_id": greeting_id,
        "status": "delivered",
        "greeting": greeting,
        "style": style,
    }


class GreeterAgent:
    """An agent that provides customizable greetings using Gemini."""
    
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
        return "Processing your greeting request..."
    
    def _build_agent(self) -> LlmAgent:
        """Builds the LLM agent for the Greeter agent using Gemini."""
        return LlmAgent(
            model="gemini-2.0-flash-001",  # Using Gemini like the sample
            name="greeter_agent",
            description=(
                "This agent provides customizable greetings. "
                "It demonstrates A2A communication with form handling and state management."
            ),
            instruction="""
You are a friendly greeting agent. Your job is to help users create personalized greetings.

When someone asks you to greet a person, you have two options:

1. For simple greetings (e.g., "greet John"), use the tools to:
   - First create a greeting form with `create_greeting_form()` 
   - Then immediately generate the greeting with `generate_greeting()`
   - Return the greeting text to the user

2. For custom greetings (when user says "custom" or "customize"), use the tools to:
   - Create a form with `create_greeting_form()`
   - Return the form to the user with `return_greeting_form()` so they can customize it
   - When they submit the completed form, use `generate_greeting()` with the greeting_id

Instructions:
- Extract the person's name from the request when possible
- For simple requests, use "casual" style by default
- Always be friendly and helpful
- If no name is provided, you can use "Friend" as a default

Examples:
- "Please greet John" -> create_greeting_form(name="John", style="casual") then generate_greeting()
- "Custom greeting for Maria" -> create_greeting_form(name="Maria") then return_greeting_form()
- "Say hello formally to Dr. Smith" -> create_greeting_form(name="Dr. Smith", style="formal") then generate_greeting()
""",
            tools=[
                create_greeting_form,
                return_greeting_form,
                generate_greeting,
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