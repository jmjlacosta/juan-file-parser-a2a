import json
import os
import re
import httpx
from typing import Any, AsyncIterable


class CallerAgent:
    """A simple agent that demonstrates A2A communication without LLM dependencies."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
    
    def __init__(self):
        self.name = "caller_agent"
    
    def get_processing_message(self) -> str:
        return "Calling the Greeter Agent..."
    
    def extract_name(self, query: str) -> str:
        """Extract a name from the query for the greeter."""
        # Try patterns like "call greeter for NAME" or "get greeting for NAME"
        patterns = [
            r"for\s+(\w+)",
            r"greet\s+(\w+)",
            r"greeting\s+for\s+(\w+)",
            r"hello\s+to\s+(\w+)",
            r"call.*?(\w+)$",  # Last word after "call"
        ]
        
        query_lower = query.lower()
        for pattern in patterns:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
        
        # Try to find any capitalized word
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1 and word.lower() not in ['agent', 'greeter', 'caller']:
                return word
        
        return "Someone"  # Default if no name found
    
    async def call_greeter_agent(self, name: str) -> str:
        """Call Agent A (Greeter Agent) to get a greeting."""
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
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """Process the query and call Agent A."""
        # Yield processing message
        yield {
            "is_task_complete": False,
            "updates": self.get_processing_message(),
        }
        
        # Extract name from query
        name = self.extract_name(query)
        
        # Call Agent A
        response = await self.call_greeter_agent(name)
        
        # Yield final response
        yield {
            "is_task_complete": True,
            "content": f"Demonstrating A2A communication:\n{response}",
        }