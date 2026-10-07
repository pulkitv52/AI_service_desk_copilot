# AI Service Desk Copilot

Portfolio-ready AI Service Desk Automation Platform demonstrating conversational deflection via RAG, ServiceNow IT Service Management integration, intelligent ticket classification and routing, and safe bounded self-healing remediation.

## Overview

Employees frequently reach out to enterprise IT Service Desks for repetitive requests such as password resets, VPN connectivity troubleshooting, software requests, and enterprise application errors. This platform automates first-contact resolution, deflects inquiries with grounded knowledge answers, and escalates unresolved or complex issues directly into ServiceNow.

## Architecture

The system is built incrementally around provider abstractions and bounded autonomy:

- Backend: FastAPI, Pydantic, HTTPX, and Python standard logging
- Database: PostgreSQL with pgvector for knowledge chunk vector storage
- ITSM Integration: ServiceNow REST Table API with a local MockTicketingProvider fallback
- LLM and Embeddings: Gemini 3.5 Flash Lite and Gemini embeddings behind provider protocols
- Frontend: React, TypeScript, Vite, and shadcn/ui

## Getting Started

### Prerequisites

- Python 3.12 or newer
- uv package manager
- Docker and Docker Compose (for PostgreSQL with pgvector)

### Configuration

Copy the example environment file and configure your credentials:

```bash
cp .env.example .env
```

If you have a ServiceNow Personal Developer Instance (PDI), update `.env` with:

```env
SERVICENOW_INSTANCE_URL=https://devXXXXX.service-now.com
SERVICENOW_USERNAME=admin
SERVICENOW_PASSWORD=your_password
```

If ServiceNow credentials are omitted or `USE_MOCK_SERVICENOW=true`, the platform runs against an in-memory `MockTicketingProvider`.

### Running Locally

To start the database:

```bash
docker compose up -d db
```

To run the backend:

```bash
cd backend
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

To run the frontend:

```bash
cd frontend
pnpm dev
```

### Running Tests

Run the test suite using pytest via uv:

```bash
cd backend
uv run pytest
```

Format code using black:

```bash
cd backend
uv run black .
```

## API Endpoints

- `GET /health`: Health and operational status check
- `POST /api/chat`: Conversational endpoint combining intent classification, RAG deflection, and automated escalation
- `POST /api/knowledge/ingest`: Ingest markdown knowledge articles into PostgreSQL with pgvector embeddings
- `POST /api/knowledge/search`: Semantic vector similarity search over knowledge chunks
- `POST /api/knowledge/answer`: RAG-grounded question answering with source citations
- `POST /api/tickets`: Create a new incident ticket (ServiceNow or Mock)
- `GET /api/tickets/{ticket_id}`: Retrieve incident by sys_id or number
- `PATCH /api/tickets/{ticket_id}`: Update incident state, work notes, or assignment group
- `GET /api/tickets`: List and query incidents
- `GET /api/devices/{device_id}/health`: Retrieve simulated DEX endpoint telemetry metrics
- `POST /api/devices/{device_id}/simulate`: Simulate degraded endpoint metrics (e.g., low disk, latency)
- `POST /api/devices/{device_id}/remediate`: Execute allow-listed remediation tools with before-and-after verification
