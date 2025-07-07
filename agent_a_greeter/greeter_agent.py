import json
import re
import random
from typing import Any, AsyncIterable, Optional, Dict
from google.adk.tools.tool_context import ToolContext
from google.adk.artifacts import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.sessions import InMemorySessionService


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
    """An enhanced agent that provides customizable greetings with state management."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain", "application/json"]
    
    def __init__(self):
        self.name = "greeter_agent"
        self._user_id = "greeter_agent_user"
        self._artifact_service = InMemoryArtifactService()
        self._session_service = InMemorySessionService()
        self._memory_service = InMemoryMemoryService()
    
    def get_processing_message(self) -> str:
        return "Processing your greeting request..."
    
    def extract_name(self, query: str) -> Optional[str]:
        """Extract a name from the query using simple patterns."""
        patterns = [
            r"greet\s+(\w+)",
            r"hello\s+to\s+(\w+)",
            r"welcome\s+(\w+)",
            r"say\s+hello\s+to\s+(\w+)",
            r"greet\s+(?:our\s+guest\s+)?(\w+)",
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        
        # Try to find any name-like word
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1:
                return word
        
        return None
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """Process the query with enhanced form and state capabilities."""
        # Get or create session
        session = await self._session_service.get_session(
            app_name=self.name,
            user_id=self._user_id,
            session_id=session_id,
        )
        
        if session is None:
            session = await self._session_service.create_session(
                app_name=self.name,
                user_id=self._user_id,
                state={},
                session_id=session_id,
            )
        
        # Yield processing message
        yield {
            "is_task_complete": False,
            "updates": self.get_processing_message(),
        }
        
        # Check if this is a form submission
        try:
            query_data = json.loads(query)
            if isinstance(query_data, dict) and "greeting_id" in query_data:
                # This is a completed form, generate the greeting
                result = generate_greeting(query_data["greeting_id"])
                yield {
                    "is_task_complete": True,
                    "content": result,
                }
                return
        except json.JSONDecodeError:
            pass
        
        # Check for custom greeting request
        if "custom" in query.lower() or "form" in query.lower():
            # Create a form for customization
            name = self.extract_name(query)
            form_data = create_greeting_form(name=name)
            
            # Create mock tool context
            class MockToolContext:
                class Actions:
                    skip_summarization = False
                    escalate = False
                actions = Actions()
            
            form_response = return_greeting_form(
                form_data,
                MockToolContext(),
                "Please fill out this form to customize your greeting"
            )
            
            yield {
                "is_task_complete": True,
                "content": form_response,
            }
        else:
            # Simple greeting flow
            name = self.extract_name(query)
            if name:
                # Create a greeting record
                form_data = create_greeting_form(name=name, style="casual")
                result = generate_greeting(form_data["greeting_id"])
                
                yield {
                    "is_task_complete": True,
                    "content": result["greeting"],
                }
            else:
                yield {
                    "is_task_complete": True,
                    "content": "I'd be happy to greet someone! Please tell me who to greet, or ask for a 'custom greeting' to see more options.",
                }