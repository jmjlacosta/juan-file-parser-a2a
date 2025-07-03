# Progressive Document Parser A2A - Technical Architecture

## Overview

This document details the technical architecture of the Progressive Document Parser implemented as an Agent-to-Agent (A2A) system using the Google ADK framework.

## Core Design Principles

1. **Progressive Refinement**: Start with minimal context, expand only when needed
2. **Parallel Processing**: Multiple agents work simultaneously on different extraction tasks
3. **Tool-Based Architecture**: Agents use specific tools rather than REST endpoints
4. **Streaming Updates**: Real-time progress updates for long-running jobs
5. **Confidence-Based Decisions**: Each extraction includes confidence metrics

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        A2A Server (main.py)                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Parser Agent (Orchestrator)              │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │   │
│  │  │   Scanner    │  │  Extractors  │  │  Synthesizer   │ │   │
│  │  │    Agent     │  │   (Parallel) │  │     Agent      │ │   │
│  │  └─────────────┘  └──────────────┘  └────────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                        Tools Layer                        │   │
│  │  ┌───────────┐  ┌────────────┐  ┌──────────────────┐   │   │
│  │  │ PDF Tools │  │ Extraction │  │  Cache Tools     │   │   │
│  │  │           │  │   Tools    │  │  (Redis)         │   │   │
│  │  └───────────┘  └────────────┘  └──────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Details

### 1. Parser Agent (Main Orchestrator)

**Responsibilities:**
- Receives document parsing requests
- Orchestrates the 3-phase parsing process
- Manages job queue and status
- Streams progress updates to clients

**Key Methods:**
```python
async def parse_document(self, file_path: str, extraction_request: ExtractionRequest):
    # Phase 1: Scan document structure
    document_map = await self.scan_document(file_path)
    
    # Phase 2: Parallel extraction
    extractions = await self.extract_fields_parallel(file_path, document_map, extraction_request)
    
    # Phase 3: Synthesize results
    final_result = await self.synthesize_results(extractions)
    
    return final_result
```

### 2. Scanner Agent

**Purpose:** Rapidly analyze document structure without loading full content

**Tools:**
- `scan_document()`: Uses pdftotext + grep for structure analysis
- `detect_sections()`: Identifies major document sections
- `create_document_map()`: Builds navigation structure

**Implementation Strategy:**
```python
async def scan_document(self, document_path: str) -> DocumentMap:
    # Use command-line tools for efficiency
    cmd = f"pdftotext -layout {document_path} - | grep -n -i 'inclusion\\|exclusion\\|sponsor'"
    locations = await run_command(cmd)
    
    return DocumentMap(
        sections=parse_section_locations(locations),
        page_count=get_page_count(document_path),
        has_tables=detect_tables(document_path)
    )
```

### 3. Extractor Agents

**Purpose:** Extract specific fields using progressive context windows

**Types:**
- `SponsorExtractor`: Company/institution identification
- `ConditionsExtractor`: Medical conditions being studied
- `CriteriaExtractor`: Inclusion/exclusion criteria
- `OutcomesExtractor`: Primary/secondary outcomes

**Progressive Context Strategy:**
```python
CONTEXT_STRATEGIES = {
    "identifier": {
        "initial": {"before": 5, "after": 5},      # Start small
        "expanded": {"before": 10, "after": 10},   # Expand if needed
        "max": {"before": 20, "after": 20},        # Maximum context
        "max_attempts": 3
    }
}
```

### 4. Synthesizer Agent

**Purpose:** Combine extraction results with confidence scoring

**Tools:**
- `calculate_confidence()`: Field-specific confidence calculation
- `merge_results()`: Combine multiple extraction attempts
- `generate_metadata()`: Create extraction metadata

## Data Flow

```
1. Document Upload
   └─> Parser Agent receives file
       └─> Scanner Agent analyzes structure
           └─> Creates DocumentMap
   
2. Parallel Extraction
   └─> Parser Agent spawns extractors
       ├─> SponsorExtractor
       ├─> ConditionsExtractor
       └─> [Other Extractors]
           └─> Each uses progressive context
   
3. Result Synthesis
   └─> Synthesizer Agent combines results
       └─> Calculates confidence scores
           └─> Returns final structured data
```

## Key Data Models

### ExtractionRequest
```python
class ExtractionRequest(BaseModel):
    objective: str = "extract_clinical_trial_fields"
    extraction_schema: Dict[str, FieldConfig]
    options: Optional[Dict[str, Any]] = None
```

### DocumentMap
```python
class DocumentMap(BaseModel):
    sections: List[Section]
    page_count: int
    has_tables: bool
    metadata: Dict[str, Any]
```

### ExtractionResult
```python
class ExtractionResult(BaseModel):
    job_id: str
    status: str
    progress: float
    results: Optional[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    extraction_metadata: Dict[str, Any]
```

## Caching Strategy

### Redis Cache Layers

1. **Document Structure Cache** (TTL: 1 hour)
   - Key: `docparse:{file_hash}:structure`
   - Value: Serialized DocumentMap

2. **Extraction Cache** (TTL: 30 minutes)
   - Key: `docparse:{file_hash}:{field}:{context_size}`
   - Value: Extraction result with confidence

3. **LLM Response Cache** (TTL: configurable)
   - Key: `llm:{prompt_hash}`
   - Value: LLM response

## Error Handling

### Retry Strategy
```python
class RetryConfig:
    max_attempts = 3
    backoff_factor = 2
    max_delay = 30
```

### Fallback Mechanisms

1. **Sponsor Extraction Fallbacks:**
   - Direct mention → PI institution → Cover page analysis

2. **General Extraction Fallbacks:**
   - Pattern matching → LLM extraction → Expanded context → Manual review flag

## Performance Optimizations

1. **Parallel Processing**
   - All field extractors run concurrently
   - Async I/O for file operations
   - Batch processing for multiple documents

2. **Efficient Text Processing**
   - Use ripgrep for fast pattern matching
   - Stream large files instead of loading to memory
   - Process only relevant sections

3. **Smart Caching**
   - Cache expensive operations (PDF parsing, LLM calls)
   - Invalidate cache based on file modifications
   - Distributed cache for horizontal scaling

## Security Considerations

1. **File Upload Security**
   - Validate file types and sizes
   - Scan for malicious content
   - Isolate file processing

2. **API Security**
   - Secure API key management
   - Rate limiting per client
   - Audit logging

## Monitoring & Observability

### Metrics to Track
- Extraction success rates by field
- Average processing time per document
- Cache hit rates
- API costs per extraction
- Error rates and types

### Logging Strategy
```python
logger.info("extraction_started", extra={
    "job_id": job_id,
    "document_size": file_size,
    "requested_fields": fields
})
```

## Deployment Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Load Balancer │────▶│   A2A Server    │
└─────────────────┘     └─────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              ┌─────▼─────┐         ┌─────▼─────┐
              │   Redis    │         │   Storage │
              │   Cache    │         │   (S3)    │
              └───────────┘         └───────────┘
```

## Future Enhancements

1. **Multi-Modal Support**
   - OCR for scanned documents
   - Table extraction
   - Image analysis

2. **Advanced Confidence**
   - ML-based confidence scoring
   - Cross-validation between extractors
   - Human-in-the-loop feedback

3. **Scalability**
   - Kubernetes deployment
   - Horizontal scaling of extractors
   - Queue-based job distribution