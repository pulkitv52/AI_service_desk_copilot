# AGENTS.md — AI Service Desk Copilot

## 1. Project Mission

Build a portfolio-ready **AI Service Desk Automation Platform** that demonstrates how conversational AI, RAG, ServiceNow integration, intelligent ticket routing, and safe automated remediation can reduce repetitive Service Desk work.

This project is intentionally designed to help the developer learn the technologies expected in enterprise **Digital Automation & AI / Platform Engineering** roles while producing a working GitHub project.

The system should be built incrementally. Do **not** attempt to implement Azure, Microsoft Teams, Nexthink, ServiceNow, RAG, and self-healing all at once.

The first objective is a working local MVP on a laptop with:

- FastAPI
- React + TypeScript
- PostgreSQL
- pgvector
- Gemini 3.5 Flash Lite via API key
- ServiceNow Personal Developer Instance (PDI)

---

## 2. Core Problem Statement

Employees frequently contact IT Service Desks for repetitive issues such as:

- Password reset guidance
- VPN connectivity problems
- Software installation requests
- Low disk-space issues
- Outlook / Teams troubleshooting
- Application access issues
- General IT knowledge questions

Traditional support creates unnecessary tickets and increases resolution time.

The platform should:

1. Understand an employee's support request.
2. Search enterprise IT knowledge using RAG.
3. Resolve simple questions without creating a ticket.
4. Run only approved diagnostic/remediation tools when appropriate.
5. Create a ServiceNow incident or request when the issue cannot be resolved automatically.
6. Classify the ticket.
7. Select an appropriate assignment group.
8. Preserve traceability for every decision and automation action.
9. Collect metrics such as containment, routing accuracy, resolution time, and automation success.

The long-term goal is to demonstrate a simplified **Zero Service Desk** architecture.

---

## 3. Target User Journey

```text
Employee
   |
   v
Chat UI
   |
   v
Intent / Request Understanding
   |
   +-------------------------+
   |                         |
   v                         v
Knowledge Question       Technical Issue
   |                         |
   v                         v
RAG Search             Diagnostics / Tools
   |                         |
   v                         v
Good answer?            Resolved safely?
 |       |                |       |
Yes      No              Yes      No
 |       |                |       |
 v       +----------------+       v
Answer                      ServiceNow Ticket
                                 |
                                 v
                         Classification + Routing
                                 |
                                 v
                           Support Team
```

---

## 4. Fixed Technology Choices

These are the default choices for the project unless explicitly changed later.

### Backend

- Python
- FastAPI
- Pydantic
- httpx
- pytest

### Frontend

- React
- TypeScript
- Vite
- shadcn/ui

### Database

- PostgreSQL

### Vector Database

- PostgreSQL + **pgvector**
- Do not introduce ChromaDB, FAISS, Weaviate, Milvus, Pinecone, or another vector store unless explicitly requested.

### LLM

- **Gemini 3.5 Flash Lite**
- Accessed through an API key
- Keep Gemini access behind a provider/service abstraction

### Embeddings

Use a Gemini-compatible embedding model or another explicitly selected embedding provider.

The embedding implementation must also sit behind an abstraction so the storage layer does not depend directly on a specific SDK.

### Service Management

- ServiceNow Personal Developer Instance
- ServiceNow REST APIs

### Infrastructure

- Docker
- docker-compose
- Git
- GitHub

---

## 5. Explicitly Excluded From MVP

Do not introduce the following unless explicitly requested later:

- Ollama
- ChromaDB
- Azure OpenAI
- Azure AI Search
- Microsoft Teams integration
- Power Automate
- Nexthink
- Production SSO
- Real enterprise endpoint fleet management

The local MVP must remain fully usable without these.

---

## 6. MVP Scope

### Must Have

- Web-based chat interface
- FastAPI backend
- Basic conversation/session handling
- IT-support intent classification
- Local knowledge base
- RAG retrieval using PostgreSQL + pgvector
- Grounded answer generation using Gemini 3.5 Flash Lite
- Confidence/fallback logic
- ServiceNow incident creation
- Basic ticket classification
- Basic assignment-group routing
- Audit logging
- Docker-based local development
- Automated tests for critical backend components

### Should Have

After the MVP:

- Service request creation
- Incident update/status lookup
- RAG evaluation
- Intelligent LLM-assisted routing
- Approved diagnostic tools
- Safe remediation workflows
- Synthetic DEX telemetry
- User feedback capture
- Metrics dashboard

### Later / Optional

- Azure deployment
- Azure Key Vault
- Microsoft Teams
- Power Automate
- Microsoft Graph
- Nexthink
- OAuth for ServiceNow
- Production authentication/SSO

---

## 7. High-Level Architecture

```text
              Employee
                  |
                  v
             React Chat UI
                  |
                  v
              FastAPI
                  |
          Support Orchestrator
       /          |           \
      /           |            \
     v            v             v
 Gemini       RAG Service    Ticketing
  LLM            |              |
                 v              v
            PostgreSQL      ServiceNow
             + pgvector       REST API
                 |
                 v
         Knowledge Chunks

                  |
                  v
          Approved Tools
                  |
                  v
         Synthetic DEX Layer

                  |
                  v
          Audit + Metrics
                  |
                  v
             PostgreSQL
```

---

## 8. Provider Abstractions

Even though Gemini is the selected LLM, keep integrations isolated.

### LLM

```text
LLMProvider
  |
  `-- GeminiProvider
```

Suggested interface:

```python
from typing import Protocol

class LLMProvider(Protocol):
    async def generate(self, prompt: str) -> str:
        ...
```

### Embeddings

```text
EmbeddingProvider
  |
  `-- GeminiEmbeddingProvider
```

### Ticketing

```text
TicketingProvider
  |- ServiceNowProvider
  `- MockTicketingProvider
```

### Telemetry

```text
TelemetryProvider
  |- SyntheticDEXProvider
  `- FutureNexthinkProvider
```

Do not let Gemini SDK calls, ServiceNow HTTP calls, or vector SQL leak throughout business logic.

---

## 9. Environment Variables

Use `.env` locally and `.env.example` in the repository.

Example:

```env
GEMINI_API_KEY=

SERVICENOW_INSTANCE_URL=
SERVICENOW_USERNAME=
SERVICENOW_PASSWORD=

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/service_desk

POSTGRES_DB=service_desk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

Never commit real secrets.

---

## 10. PostgreSQL + pgvector Design

Use one PostgreSQL instance initially for both:

- application data
- vector storage

Enable the `vector` extension.

Suggested schema:

### conversations

```text
id
user_id
created_at
status
```

### messages

```text
id
conversation_id
role
content
created_at
```

### ai_decisions

```text
id
conversation_id
intent
confidence
decision
reason
created_at
```

### ticket_mappings

```text
id
conversation_id
provider
external_ticket_id
external_sys_id
created_at
```

### automation_runs

```text
id
conversation_id
tool_name
input
status
output
started_at
completed_at
```

### knowledge_documents

```text
id
source_id
title
category
content
metadata
created_at
updated_at
```

### knowledge_chunks

```text
id
document_id
chunk_index
content
embedding vector(...)
metadata
created_at
```

The exact vector dimension must match the selected embedding model.

Do not hardcode a dimension until the embedding provider is selected and confirmed.

---

## 11. ServiceNow Learning Goals

### Core Platform

Learn:

- Tables
- Records
- Forms
- Lists
- Users
- Groups
- Roles
- Basic ACL concepts

### ITSM Concepts

Understand:

- Incident
- Service Request
- Problem
- Change
- Knowledge Article
- SLA
- Priority
- Assignment Group
- Escalation
- Service Catalog
- CMDB basics
- L1 / L2 / L3 support

### APIs

Initial capabilities:

- Create incident
- Retrieve incident
- Update incident
- Query incidents

Later:

- Create service request
- Add comments/work notes
- Update state
- Search knowledge where appropriate

All ServiceNow calls must be isolated inside the integration layer.

---

## 12. Initial Use Cases

### UC-01 — Password Reset Guidance

Input:

> "I forgot my password. How can I reset it?"

Expected behavior:

- Detect password-related intent.
- Retrieve password-reset KB content from pgvector.
- Answer using grounded RAG.
- Do not create a ticket if confidence is high.

---

### UC-02 — VPN Connectivity

Input:

> "My VPN is not connecting."

Expected behavior:

1. Retrieve troubleshooting steps.
2. Optionally run safe diagnostics.
3. Ask for required information if necessary.
4. If unresolved, create a ServiceNow incident.
5. Route to Network / VPN Support.

---

### UC-03 — Software Installation

Input:

> "I need VS Code installed."

Expected behavior:

- Detect software request.
- Treat it as a service request rather than a generic incident.
- Initially simulate approval/fulfilment if ServiceNow catalog implementation is not ready.
- Later integrate with ServiceNow request/catalog workflows.

---

### UC-04 — Low Disk Space

Input:

> "My laptop says disk space is almost full."

Expected behavior:

1. Inspect synthetic/local telemetry.
2. Identify low disk threshold.
3. Recommend an approved cleanup action.
4. Execute only a safe allow-listed remediation.
5. Re-check disk space.
6. Log before/after state.
7. Escalate if unsuccessful.

---

### UC-05 — Enterprise Application Issue

Input:

> "SAP is not allowing me to approve purchase orders."

Expected behavior:

- Detect application issue.
- Extract application = SAP.
- Extract module/domain where possible.
- Create incident if no self-service resolution exists.
- Route to an SAP support assignment group.
- Preserve classification evidence.

---

## 13. Knowledge Base

Create synthetic IT support documents in:

```text
knowledge-base/
  password-reset.md
  vpn-troubleshooting.md
  disk-space.md
  software-installation.md
  outlook-troubleshooting.md
  teams-troubleshooting.md
  sap-support.md
```

Every document should contain:

- Title
- Problem description
- Symptoms
- Preconditions
- Resolution steps
- Escalation conditions
- Category
- Last-updated field
- Source identifier

RAG answers must include source references.

---

## 14. RAG Requirements

The RAG pipeline should include:

1. Document loading
2. Cleaning
3. Chunking
4. Embedding generation
5. Insert/update vectors in PostgreSQL + pgvector
6. Semantic retrieval using vector similarity
7. Optional metadata filtering
8. Optional re-ranking
9. Context pruning
10. Grounded answer generation using Gemini
11. Confidence/fallback logic

Do not rely on Gemini's general knowledge when KB evidence is required.

If retrieval confidence is below threshold:

```text
Do not invent answer
        |
        v
Offer escalation / create ServiceNow ticket
```

Track:

- retrieved document IDs
- retrieved chunk IDs
- similarity scores
- selected context
- Gemini response
- final workflow action

---

## 15. Gemini Usage Rules

Gemini 3.5 Flash Lite should be used for:

- intent understanding
- semantic extraction
- natural-language generation
- RAG synthesis
- summarization
- ambiguous routing suggestions

Do not use Gemini as the source of truth for deterministic enterprise rules.

Use deterministic logic for:

- priority policy
- tool permission
- required ticket fields
- escalation thresholds
- destructive action prevention
- assignment rules when explicit rules exist

All Gemini-produced structured outputs must be validated with Pydantic.

Implement:

- API timeouts
- retry strategy for transient failures
- rate-limit handling
- structured error handling
- request tracing where practical

Never log the Gemini API key.

---

## 16. Ticket Classification

Initial ticket schema:

```json
{
  "intent": "application_issue",
  "category": "software",
  "subcategory": "enterprise_application",
  "application": "SAP",
  "urgency": "medium",
  "impact": "medium",
  "priority": "P3",
  "assignment_group": "SAP Support",
  "confidence": 0.91
}
```

Use deterministic rules first where possible.

Example:

```text
application=SAP AND domain=procurement
    -> SAP Procurement Support
```

Later compare deterministic routing with Gemini-assisted routing.

Never allow the LLM to silently assign high-impact priority without validation rules.

---

## 17. Initial Routing Rules

```text
password/authentication
    -> Identity & Access Support

vpn/network
    -> Network Support

software_installation
    -> End User Computing

outlook/teams
    -> Collaboration Support

sap
    -> SAP Support

unknown
    -> Service Desk L1
```

Do not over-engineer routing in the first version.

---

## 18. Safe Automation / Self-Healing

The project must demonstrate **bounded agent autonomy**.

Do not give Gemini arbitrary shell access.

Create explicitly approved tools:

```text
automation/
  check_disk_space.py
  check_network.py
  collect_system_health.py
  clear_demo_cache.py
  restart_demo_service.py
```

Rules:

- Tools must be allow-listed.
- Inputs must be validated.
- Destructive operations are prohibited.
- Every action must be logged.
- Tools should support dry-run mode.
- High-risk actions must require human approval.
- The system should explain why a tool is being invoked.

---

## 19. Synthetic DEX Layer

Because a Nexthink tenant may not be available, build a synthetic DEX simulator.

Example:

```json
{
  "device_id": "EMP-LT-104",
  "cpu_usage": 92,
  "memory_usage": 86,
  "disk_free_gb": 3.2,
  "teams_crashes_24h": 5,
  "network_latency_ms": 178
}
```

Create APIs such as:

```text
GET /api/devices/{device_id}/health
POST /api/devices/{device_id}/simulate
```

This simulates endpoint experience signals that an enterprise DEX platform could provide.

---

## 20. Proposed Backend Structure

```text
backend/
  app/
    main.py

    api/
      routes_chat.py
      routes_tickets.py
      routes_devices.py
      routes_health.py
      routes_knowledge.py

    core/
      config.py
      logging.py
      security.py

    models/
      chat.py
      ticket.py
      device.py
      knowledge.py

    services/
      conversation_service.py
      classification_service.py
      routing_service.py
      rag_service.py
      remediation_service.py

    integrations/
      gemini/
        client.py
        llm.py
        embeddings.py

      servicenow/
        client.py
        schemas.py
        mapper.py

      telemetry/
        base.py
        synthetic.py

    repositories/
      knowledge_repository.py
      audit_repository.py
      conversation_repository.py
      ticket_repository.py

    tools/
      disk.py
      network.py
      diagnostics.py

  tests/
```

---

## 21. Suggested Repository Structure

```text
ai-service-desk-copilot/
|
|-- AGENTS.md
|-- README.md
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|
|-- backend/
|-- frontend/
|-- knowledge-base/
|-- automation/
|-- evaluation/
|-- docs/
|-- scripts/
|-- tests/
|
`-- sample-data/
```

---

## 22. Implementation Phases

### Phase 0 — Repository Bootstrap

Create:

- Git repository
- `.gitignore`
- `.env.example`
- backend skeleton
- frontend skeleton
- PostgreSQL + pgvector container
- Docker Compose
- health endpoints
- pytest setup
- developer documentation

Success criterion:

```text
docker compose up
```

starts the local environment and PostgreSQL has pgvector enabled.

---

### Phase 1 — ServiceNow Integration

Goal:

Prove:

```text
Laptop
  |
  v
FastAPI
  |
  v
ServiceNow REST API
  |
  v
Incident created successfully
```

Implement:

```text
POST /api/tickets
GET /api/tickets/{sys_id}
PATCH /api/tickets/{sys_id}
```

This phase must be completed before agentic AI work.

---

### Phase 2 — PostgreSQL Knowledge Store + pgvector

Implement:

- pgvector extension
- document tables
- chunk tables
- vector column
- ingestion repository
- similarity search
- metadata filters
- migrations

Success criterion:

A query retrieves relevant KB chunks directly from PostgreSQL.

---

### Phase 3 — Gemini Integration

Implement:

- Gemini client
- LLM provider abstraction
- embedding provider abstraction
- config validation
- timeout handling
- structured outputs
- unit tests using mocks

Do not put Gemini SDK calls directly into route handlers.

---

### Phase 4 — RAG

Implement:

- IT-support documents
- ingestion pipeline
- chunking
- embedding generation
- storage in pgvector
- retrieval
- grounded answer generation with Gemini
- source citations
- fallback threshold

Success criterion:

Common IT questions are answered using only retrieved project KB evidence.

---

### Phase 5 — Intent Classification + Routing

Implement:

- intent schema
- category/subcategory classification
- urgency/impact inputs
- deterministic priority rules
- assignment-group routing
- confidence values

Success criterion:

Synthetic test tickets route correctly with measurable accuracy.

---

### Phase 6 — Conversational Orchestration

Build:

```text
message
  |
  v
classify
  |
  +---- knowledge -> pgvector RAG -> Gemini
  |
  +---- diagnostic -> approved tool
  |
  +---- service request -> workflow
  |
  `---- unresolved -> ServiceNow
```

Do not create a complex multi-agent system unless a simpler workflow proves insufficient.

---

### Phase 7 — Safe Remediation

Implement approved tools.

Minimum demo:

- disk health check
- synthetic cleanup/remediation
- network diagnostic
- verification step
- escalation on failure

---

### Phase 8 — Synthetic DEX

Add:

- device simulator
- health metrics
- threshold detection
- remediation triggers
- device history

---

### Phase 9 — Evaluation

Create evaluation dataset.

Measure:

- intent accuracy
- routing accuracy
- Recall@K
- MRR or nDCG where useful
- grounded-answer pass rate
- ticket containment rate
- remediation success rate
- average workflow latency

---

### Phase 10 — Enterprise Extensions

Only after local MVP works:

- Azure deployment
- secret management
- monitoring
- Teams adapter
- Power Automate workflows
- OAuth for ServiceNow
- real SSO
- Nexthink adapter

---

## 23. MVP APIs

```text
GET  /health

POST /api/chat
POST /api/chat/{session_id}/messages

POST /api/tickets
GET  /api/tickets/{ticket_id}
PATCH /api/tickets/{ticket_id}

POST /api/knowledge/ingest
POST /api/knowledge/search

GET  /api/devices/{device_id}/health
POST /api/devices/{device_id}/simulate

GET  /api/audit/{session_id}
```

Use typed Pydantic request/response models.

---

## 24. Security Requirements

Must implement:

- secrets in environment variables
- `.env` excluded from Git
- input validation
- API timeouts
- safe error messages
- structured logging
- no arbitrary shell execution
- tool allow-list
- audit trail
- least privilege mindset
- data redaction where appropriate

Never log:

- Gemini API key
- ServiceNow password
- access tokens

---

## 25. Observability

Use structured logs.

Every workflow should have a correlation/session ID.

Log events such as:

```text
request_received
intent_classified
knowledge_retrieved
gemini_request_started
gemini_request_completed
rag_answer_generated
tool_requested
tool_executed
ticket_created
ticket_routed
workflow_completed
workflow_failed
```

Later expose metrics for:

- request count
- error rate
- latency
- RAG fallback frequency
- ticket creation rate
- containment rate
- remediation success

---

## 26. Testing Strategy

### Unit Tests

- priority calculation
- routing rules
- ServiceNow payload mapping
- pgvector repository logic
- confidence fallback
- Gemini structured output parsing
- tool input validation

### Integration Tests

- FastAPI endpoint -> mock ServiceNow
- knowledge ingestion -> PostgreSQL/pgvector retrieval
- workflow -> ticket escalation
- Gemini provider -> mocked SDK response

### Contract Tests

Validate ServiceNow request/response mapping.

### Evaluation Tests

Run labelled examples through:

- classifier
- retriever
- router

Do not depend on a live ServiceNow PDI or live Gemini API for every automated test.

Use mocks/fixtures.

---

## 27. Coding Standards

- Python code should be typed.
- Prefer small modules and explicit interfaces.
- Use Pydantic for request/response models.
- Use dependency injection where useful.
- Avoid global mutable state.
- External API calls must have timeouts.
- Add retries only for transient failures.
- Do not swallow exceptions.
- Return useful structured errors.
- Keep business rules separate from route handlers.
- Write tests alongside meaningful functionality.
- Avoid unnecessary framework complexity.
- Use database migrations.
- Do not execute raw SQL from route handlers.
- Keep pgvector query logic in repository/data-access code.

---

## 28. Definition of MVP Done

### Demo A — Knowledge Deflection

User asks:

> "How do I reset my password?"

System:

- classifies request
- retrieves KB chunks from pgvector
- sends grounded context to Gemini
- returns answer with source reference
- does not create ServiceNow ticket

### Demo B — Ticket Escalation

User asks:

> "My SAP approval screen is failing and the KB steps did not work."

System:

- understands SAP issue
- fails self-service confidently
- generates ticket summary
- determines category
- determines assignment group
- creates ServiceNow incident
- returns incident number

### Demo C — Safe Remediation

Synthetic device reports low disk space.

System:

- detects threshold
- selects approved remediation
- executes it
- validates outcome
- records audit event
- escalates only if remediation fails

---

## 29. Portfolio Success Metrics

Do not fabricate results.

Report only measured values such as:

```text
Intent classification accuracy: XX%
Routing accuracy: XX%
Recall@5: XX%
MRR: XX
Grounded response pass rate: XX%
Ticket containment rate: XX%
Remediation success rate: XX%
Median response latency: XX seconds
```

---

## 30. First Coding Sequence

Codex should implement the project in this order.

### Step 1

Initialize repository structure.

### Step 2

Create FastAPI app with:

```text
GET /health
```

### Step 3

Add environment-based configuration.

### Step 4

Add PostgreSQL + pgvector to Docker Compose.

### Step 5

Add database migrations and verify pgvector extension.

### Step 6

Create `TicketingProvider` abstraction.

### Step 7

Create mock ticketing provider.

### Step 8

Add ServiceNow client.

### Step 9

Implement:

```text
POST /api/tickets
```

### Step 10

Create an incident through the developer ServiceNow instance.

### Step 11

Add ticket retrieval/update.

### Step 12

Add PostgreSQL audit logging.

### Step 13

Create synthetic knowledge documents.

### Step 14

Create knowledge document/chunk schema.

### Step 15

Create Gemini embedding provider.

### Step 16

Ingest chunks and embeddings into pgvector.

### Step 17

Implement similarity search.

### Step 18

Create Gemini LLM provider.

### Step 19

Implement grounded RAG answers.

### Step 20

Implement intent classification.

### Step 21

Implement deterministic routing.

### Step 22

Combine into `/api/chat`.

### Step 23

Build React chat UI.

### Step 24

Add approved remediation tools.

### Step 25

Add synthetic DEX simulator.

### Step 26

Build evaluation harness.

### Step 27

Polish README, screenshots, architecture, demo, and metrics.

---

## 31. Codex Working Instructions

When modifying this repository:

1. Read this file before proposing architecture changes.
2. Treat Gemini 3.5 Flash Lite as the default LLM.
3. Treat PostgreSQL + pgvector as the only vector store for MVP.
4. Do not add Ollama or ChromaDB.
5. Inspect existing code before creating new abstractions.
6. Work on one milestone at a time.
7. Do not introduce Azure/Teams/Nexthink dependencies into the MVP unless explicitly requested.
8. Do not fake enterprise integrations.
9. Where an external service is unavailable, create a clean adapter plus a mock implementation.
10. Keep the project runnable locally.
11. Prefer working code over speculative architecture.
12. Add/update tests with every meaningful backend change.
13. Update documentation whenever setup or behavior changes.
14. Never commit secrets.
15. Do not claim metrics until evaluation code has produced them.
16. Do not give Gemini arbitrary OS command execution.
17. Maintain an audit trail for AI decisions and automation actions.
18. Ensure graceful fallback to ServiceNow ticket creation when AI confidence is low.
19. Keep Gemini-specific code inside the Gemini integration layer.
20. Keep pgvector-specific SQL/query logic inside repository/data-access modules.

---

## 32. Immediate Development Goal

Do **not** start with RAG or a multi-agent framework.

The first engineering milestone is:

```text
Laptop
  |
  v
FastAPI
  |
  v
ServiceNow REST API
  |
  v
Incident created successfully
```

At the same time, PostgreSQL + pgvector should be running locally and ready for the next phase.

Once ServiceNow integration is stable and tested, proceed to:

```text
Knowledge Docs
    |
    v
Chunking
    |
    v
Gemini Embeddings
    |
    v
PostgreSQL + pgvector
    |
    v
Semantic Retrieval
    |
    v
Gemini 3.5 Flash Lite
    |
    v
Grounded Answer
```

---

## 33. End-State Architecture

```text
                    Employee
                       |
                 React Web Chat
                       |
                       v
                    FastAPI
                       |
                Support Orchestrator
          /             |              \
         /              |               \
        v               v                v
 Gemini LLM       Knowledge/RAG        Ticketing
                        |                  |
                        v                  v
                 PostgreSQL          ServiceNow
                  + pgvector          REST API
                        |
                        v
                  Approved Tools
                        |
                        v
                  Synthetic DEX

                        |
                        v
                  Audit + Metrics
                        |
                        v
                   PostgreSQL
```

Future deployment may move components to Azure without redesigning the core business logic.

---

## 34. Project Principle

The goal is not to build the largest possible AI system.

The goal is to build a **credible enterprise support automation platform** that demonstrates:

- AI engineering
- Gemini API integration
- PostgreSQL + pgvector
- enterprise RAG
- ServiceNow understanding
- ITSM understanding
- safe agentic automation
- intelligent ticket routing
- observability
- evaluation
- platform engineering discipline

Build small, validate, measure, then expand.

## Agent skills

### Issue tracker

Track issues and specs in GitHub Issues.
See `docs/agents/issue-tracker.md`.

### Triage labels

Use the five default triage labels.
See `docs/agents/triage-labels.md`.

### Domain docs

Use a single-context glossary and ADR layout.
See `docs/agents/domain.md`.
