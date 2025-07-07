import json
import re
from typing import Any, AsyncIterable


class GreeterAgent:
    """A simple agent that provides friendly greetings without LLM dependencies."""
    
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]
    
    def __init__(self):
        self.name = "greeter_agent"
    
    def get_processing_message(self) -> str:
        return "Preparing a friendly greeting..."
    
    def extract_name(self, query: str) -> str:
        """Extract a name from the query using simple patterns."""
        # Try different patterns to extract name
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
        
        # If no pattern matches, try to find any name-like word
        words = query.split()
        for word in words:
            if word[0].isupper() and len(word) > 1:
                return word
        
        return "Friend"  # Default if no name found
    
    def greet(self, name: str) -> str:
        """Generate a greeting message."""
        return f"Hello {name}! This is Agent A (Greeter) responding. I hope you're having a wonderful day!"
    
    async def stream(self, query: str, session_id: str) -> AsyncIterable[dict[str, Any]]:
        """Process the query and return a greeting."""
        # Yield processing message
        yield {
            "is_task_complete": False,
            "updates": self.get_processing_message(),
        }
        
        # Extract name and generate greeting
        name = self.extract_name(query)
        greeting = self.greet(name)
        
        # Yield final response
        yield {
            "is_task_complete": True,
            "content": greeting,
        }