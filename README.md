# AWS EC2 Corrective RAG (C-RAG) Agent 
                          

## Overview
An asynchronous DevOps AI Agent specialized in AWS EC2 infrastructure provisioning and error diagnosis.

##  System Architecture
```mermaid
graph TD
    %% Styles 
    classDef boundary fill:#f9f9f9,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5,color:#000;
classDef nodeStyle fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000;
classDef gateStyle fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000;
classDef toolStyle fill:#ede7f6,stroke:#5e35b1,stroke-width:2px,color:#000;
classDef errStyle fill:#ffe6e6,stroke:#ff0000,stroke-width:2px,color:#000;
classDef secureStyle fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#000;

    User([User Prompt]) --> Node1[Input Guardrails]:::secureStyle
    Node1 --> Router1{Pass?}:::gateStyle
    Router1 -- Yes --> Node2[Intent Classifier]:::nodeStyle
    Router1 -- No --> Node9
    
    Node2--> Router2{Route Intent?}:::gateStyle
    Router2 -- GENERAL --> Node6[Synthesizer Generator]:::nodeStyle
    Router2 -- DIAGNOSTIC --> Node3[Query Rewriter]:::nodeStyle
    Router2 -- PROVISIONING --> Node5[Code Generator]:::nodeStyle
    Router2 -- OUT OF SCOPE --> Node9([200 OK Hard coded Response]):::secureStyle
    
    Node3 --> Node4[Tool: Hybrid Search RAG ]:::toolStyle
    Node4 --> Router3{Context Found?}:::gateStyle
    Router3 -- No --> ToolWeb[Tool: Tavily Web Search]:::toolStyle
    Router3 -- Yes --> Router4{Check Intent?}:::gateStyle
    ToolWeb --> Router4 
    
    Router4 -- DIAGNOSTIC --> Node6
    Router4 -- PROVISIONING --> Node5
    
    Node5 --> Node7["Tool: Code Validator (LocalStack Sandbox)"]:::toolStyle
    Node7 --> Router5{Exit Code == 0?}:::gateStyle
    Router5 -- Yes --> Node6
    Router5 -- No: Under Max Retries --> Node4
    Router5 -- No: Exhausted Limits --> EndFail([400 Failure Payload Response]):::errStyle
    
        
    Node6 --> Node8[Output Guardrails]:::secureStyle
    Node8 --> Router6{Pass?}:::gateStyle
    Router6 -- Yes --> EndSuccess([200 OK Response]):::secureStyle
    Router6 -- No: Under Max Retries --> Node6
    Router6 -- No: Exhausted Limits --> EndFail
```
  

## Tech Stack
* **Language:** Python 3.12+
* **API:** FastAPI, Pydantic v2, Alembic, SQLAlchemy v2, Uvicorn
* **Data Layer:** PostgreSQL with PGVector 
* **AI Orchestration:** LangChain, LangGraph, Groq, text-embedding-3-small
* **Observability**: LangSmith, Structlog 
* **Evaluation**: DeepEval, Pytest
* **DevOps:** Docker, Docker-Compose, GitHub Actions, LocalStack Engine



## Key Features 
*   **Intent Classifier:** An incoming query router that classifies user intent to optimize downstream token costs and minimize latency. [Completed ✅]
*   **Hybrid Search Vector & Keyword Pipeline:** A dual-retrieval strategy combining semantic embeddings (Dense) with exact keyword matching (Sparse / BM25) to eliminate retrieval gaps. [Completed ✅]
*   **Incremental Indexing Document Pipeline:** An active ingestion pipeline that tracks ingested documents, avoiding redundant document processing and updating the vector database only when new content is available. [Completed ✅]
*   **Corrective RAG (C-RAG) Architecture:** A self-corrective loop that evaluates retrieved document relevance and triggers a web-search fallback if retrieved internal documents are deemed insufficient. [In Progress]
*   **Input & Output Guardrails:** Ingestion and generation safety nets engineered to enforce data privacy, screen for bias, block prompt injection attempts and block toxic outputs before they reach the user. [In Progress]
*   **Chainlit UI Frontend:** A streamlined streaming user interface providing real-time visual progress updates of the graph execution alongside interactive source citations. [Completed ✅]
*   **Token Streaming:** Optimized token delivery utilizing Server-Sent Events (SSE) to achieve minimal Time-to-First-Token (TTFT). [Completed ✅]

## Quick Start (Local Deployment)

### Prerequisites
* Docker and Docker-Compose installed.
* Active API keys for Tavily and Groq.


### Running the System
1. Clone the repository and navigate to the folder:
   ```bash
   git clone https://github.com/stephanie-codehub/aws-crag-agent 
   cd aws-crag-agent
   ```

2. Rename the `.env.example` file in the root directory to `.env` and populate with your values
   ```bash
   cp .env.example .env
   ```

3. Start the API, PostgreSQL database, and LocalStack instances:
   ```bash
   docker-compose up --build
   ```

4. - Access API Docs (Swagger) at `http://localhost:8000/docs`
   - Chainlit User Interface at `http://localhost:8000/chat`

