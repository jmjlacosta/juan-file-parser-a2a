# Progressive Document Parser A2A Service

An Agent-to-Agent (A2A) implementation of a progressive document parser that efficiently extracts information from large documents without hitting context window limits.

## Overview

This service uses a multi-agent architecture to parse large documents (especially clinical trial protocols) by employing a progressive refinement approach similar to how humans scan documents - first getting an overview, then diving into specific sections.

### Key Features

- **Progressive Parsing**: Analyzes documents in phases without loading entire content into memory
- **Parallel Extraction**: Multiple specialized agents work simultaneously on different fields
- **Context Window Management**: Smart expansion of context only when needed
- **Confidence Scoring**: Each extraction includes confidence metrics
- **A2A Architecture**: Built using Google ADK framework for agent-based processing

## Architecture

The parser uses a 3-phase approach:

1. **Scanner Agent**: Rapidly analyzes document structure using command-line tools
2. **Extractor Agents**: Parallel extraction of specific fields with progressive context windows
3. **Synthesizer Agent**: Combines results with confidence scoring

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed technical design.

## Technology Stack

- **Framework**: Google ADK (Agent Development Kit)
- **Runtime**: Python 3.10 with uvicorn
- **Caching**: Redis for performance optimization
- **Tools**: pdftotext, ripgrep for efficient text processing
- **Deployment**: HealthUniverse platform with Docker

## Project Structure

```
/
├── main.py                    # A2A server setup
├── parser_agent.py            # Main orchestrator agent
├── scanner_agent.py           # Document structure analysis
├── extractor_agents.py        # Field-specific extractors
├── synthesizer_agent.py       # Results synthesis
├── tools/                     # Agent tools and utilities
├── models.py                  # Data models & schemas
└── requirements.txt           # Dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- Redis (for caching)
- System tools: pdftotext, ripgrep
- API keys for LLM services (OpenAI/Google AI)

### A2A Communication Test

We've implemented a basic agent-to-agent communication test with two agents:
- **Agent A (Greeter)**: Simple agent that greets users
- **Agent B (Caller)**: Demonstrates A2A communication by calling Agent A

See `agent_a_greeter/` and `agent_b_caller/` directories for the implementation.

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd juan-file-parser-a2a

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running Locally

```bash
# Start the A2A server
uvicorn main:app --host 0.0.0.0 --port 8501 --reload
```

## Implementation Roadmap

### Milestone 1: Foundation (Week 1)
- [x] Project setup and documentation
- [ ] A2A server structure with health endpoint
- [ ] Document upload handling
- [ ] Scanner Agent implementation
- [ ] DocumentMap data model

### Milestone 2: Core Extractors (Week 2)
- [ ] SponsorExtractor with fallback strategies
- [ ] ConditionsExtractor with pattern matching
- [ ] Progressive context window system
- [ ] Redis caching layer

### Milestone 3: Advanced Features (Week 3)
- [ ] Remaining field extractors
- [ ] Synthesizer Agent with confidence scoring
- [ ] Batch processing support
- [ ] Job status tracking

### Milestone 4: Production Ready (Week 4)
- [ ] Performance optimization
- [ ] Error handling & retry mechanisms
- [ ] Monitoring & logging
- [ ] Deployment documentation

## Contributing

This project follows a progressive development approach. Each feature is tracked as a GitHub issue with clear acceptance criteria. See our [GitHub Issues](https://github.com/your-username/juan-file-parser-a2a/issues) for current tasks.

## License

[Your license here]

## Acknowledgments

Based on the Progressive Document Parser Service specification and implemented using A2A patterns from the AI Agents guide.