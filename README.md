# AI Service Desk Copilot

**Help employees troubleshoot IT problems, then hand unresolved issues to the right support team.**

An internal IT help-desk assistant built with React, FastAPI, Gemini, PostgreSQL + pgvector, and ServiceNow. It searches a support knowledge base, answers with source references, and creates an incident only when the employee explicitly asks or accepts an escalation.

**Status:** working local MVP with real Gemini and ServiceNow integrations. Knowledge articles and device telemetry are synthetic demo data. Production authentication and real endpoint remediation are not implemented.

[The problem](#the-problem) · [Demo](#a-support-request-from-start-to-finish) · [Run locally](#run-locally) · [ServiceNow](#connect-your-servicenow-instance) · [Tests](#testing-and-observed-results) · [Limitations](#current-limits)

![A knowledge-base answer with source citations in AI Service Desk Copilot](docs/images/knowledge-answer.jpg)

*Actual application screenshot: Gemini answer, PostgreSQL retrieval, mock ticketing, and simulated device telemetry. The example support portal is fictional.*

## The problem

Employees repeatedly contact IT about password resets, VPN connectivity, software installation, Outlook, Teams, and application access. Help-desk staff spend time repeating troubleshooting instructions, copying conversations into tickets, and directing issues to specialist teams.

This project puts those steps in one workflow. An employee can try documented guidance before raising an incident. If human support is needed, the incident carries the issue and conversation context so the employee does not have to explain everything again.

### Who it helps and where to use it

| Audience | Use |
|---|---|
| Employees | Get documented troubleshooting steps and request support from the same chat. |
| L1 service-desk staff | Reduce repeated explanations and manual ticket entry; retain a record of what was tried. |
| Network, identity, collaboration, and application teams | Receive incidents with context and a configured assignment group. |
| IT automation developers and students | Study a working integration of RAG, ITSM APIs, durable workflows, and safety checks. |

The current version is suited to a laptop demo, a ServiceNow PDI lab, or an internal proof of concept using approved test data. A company deployment would need its own reviewed knowledge, identity and access controls, and operational validation. Ticket reduction and time savings are intended outcomes, not measured results claimed by this repository.

## A support request from start to finish

Take a VPN problem:

1. **Describe the issue.** The employee types "My GlobalProtect VPN is not connecting."
2. **Try documented guidance.** The backend retrieves relevant KB passages from pgvector. Gemini generates an answer; the backend validates its output and source references.
3. **Choose whether to escalate.** If troubleshooting fails or evidence is insufficient, the assistant offers an incident. A refusal creates nothing. A conditional request waits for explicit acceptance.
4. **Create one incident.** Acceptance and its payload are persisted before the ServiceNow call. The configured network group receives the incident. The employee sees its number and priority.
5. **Keep the context.** Saved conversations can be reopened. Repeated acceptance returns the same incident. An uncertain timeout stays pending while the system looks up the existing incident by correlation ID.

<details>
<summary><strong>See escalation and the resulting incident</strong></summary>

### The employee controls escalation

![The assistant offers escalation with separate decline and create-ticket choices](docs/images/escalation-offer.jpg)

### The ticket stays attached to the conversation

![A mock incident with Network Support routing and P5 priority](docs/images/incident-created.jpg)

These screenshots use **mock ticketing** so the public walkthrough does not expose a personal ServiceNow instance or create live records. The same ticketing interface has been validated against a real ServiceNow PDI; see [the validation report](docs/testing/2026-10-16-validation.md).

</details>

### Live ServiceNow example

![User-provided screenshot showing a ServiceNow incident in the chat and recent-ticket list](docs/images/servicenow-live-incident.png)

*User-provided screenshot from a ServiceNow PDI session. The incident card shows the returned incident number, assignment group, and priority. The device telemetry remains simulated. This view continues an existing disk-space conversation; use **New issue** before switching to an unrelated SAP problem.*

## What works today

| Capability | Current implementation |
|---|---|
| Chat and history | React UI, one issue per conversation, persisted messages, and reopenable history. |
| Knowledge retrieval | Seven Markdown articles, indexed as 42 chunks in PostgreSQL + pgvector. |
| Answer generation | Gemini 3.5 Flash Lite with validated JSON output and retrieved-source citations. |
| Classification and routing | Deterministic rules for intent, category, impact/urgency priority, and logical support groups. |
| Incident management | Real ServiceNow create, retrieve, update, and query APIs; a separate mock provider for local testing. |
| Reliable escalation | Audit before dispatch, stable correlation IDs, duplicate prevention, and lookup-only reconciliation after uncertain outcomes. |
| Device panel | Synthetic DEX telemetry and allow-listed **simulated** cleanup/diagnostic actions, including dry-run support. |
| Local operations | Make commands for start, stop, restart, status, logs, migrations, tests, and builds. |

The device panel does **not** inspect or clean your laptop. Software installation questions provide guidance; formal service-catalog request submission is not available. Tools are not called autonomously by the RAG model.

## How it works

RAG means retrieval-augmented generation: retrieve relevant support passages first, then give the model that evidence to answer the question. The KB supplies the support policy; Gemini turns that evidence into an answer.

```mermaid
flowchart TD
    Employee[Employee] --> UI[React chat]
    UI --> API[FastAPI support workflow]
    API --> Rules[Deterministic classification and routing]
    Rules --> Retrieval[Knowledge retrieval]
    Retrieval <--> DB[(PostgreSQL + pgvector)]
    Retrieval --> Gemini[Gemini grounded generation]
    Gemini --> Validate[Validate output and source IDs]
    Validate --> Answer[Cited answer]
    Answer --> UI
    Validate --> Offer[Offer escalation when unresolved]
    Offer --> Confirm{Employee accepts?}
    Confirm -->|No| UI
    Confirm -->|Yes| Persist[Persist acceptance and ticket payload]
    Persist --> Ticketing[Ticketing provider]
    Ticketing --> SN[ServiceNow PDI or mock]
    SN --> Result[Incident number or pending verification]
    Result --> UI
    API --> Audit[(Conversations and audit trail)]
    Persist --> Audit
```

Gemini HTTP calls, ServiceNow HTTP calls, and vector queries sit behind integration and repository boundaries. There is no multi-agent framework or arbitrary model shell access. See [the incident workflow](docs/incident-workflow.md), [RAG design](docs/rag-workflow.md), and [architecture decision](docs/adr/0001-durable-incident-escalation.md).

### Knowledge included in the demo

| Topic | Document | Citation ID |
|---|---|---|
| Password reset and MFA | [Password reset](knowledge-base/password-reset.md) | `KB-SEC-001` |
| GlobalProtect VPN | [VPN troubleshooting](knowledge-base/vpn-troubleshooting.md) | `KB-NET-002` |
| Low disk space | [Disk space](knowledge-base/disk-space.md) | `KB-EUC-003` |
| Approved software installation | [Software installation](knowledge-base/software-installation.md) | `KB-EUC-004` |
| Outlook synchronization | [Outlook troubleshooting](knowledge-base/outlook-troubleshooting.md) | `KB-COL-005` |
| Teams desktop issues | [Teams troubleshooting](knowledge-base/teams-troubleshooting.md) | `KB-COL-006` |
| SAP purchase-order authorization | [SAP support](knowledge-base/sap-support.md) | `KB-APP-007` |

Each article includes symptoms, preconditions, resolution steps, escalation conditions, category, last-updated metadata, and a source identifier. The organizations, endpoints, and policies in these articles are fictional.

## Run locally

### 1. Prerequisites and checkout

The Make service controller currently targets **Linux**. Install Python 3.12+, Node.js (validated with Node 24), uv, pnpm, GNU Make, and Docker with Compose. Docker must be running and accessible to your user.

```bash
git clone https://github.com/pulkitv52/AI_service_desk_copilot.git
cd AI_service_desk_copilot
make setup
```

Setup installs locked dependencies and creates `.env` from [.env.example](.env.example) only if it does not already exist. It preserves an existing `.env`.

### 2. Choose the demo mode and configure `.env`

| Mode | What you need | What to expect |
|---|---|---|
| UI and workflow preview | Local database; no external credentials | Mock tickets and simulated device tools. This does not validate real semantic retrieval or Gemini answers. |
| **Recommended: live RAG + mock tickets** | Gemini API key | Real embeddings, retrieval, and generated answers; incidents stay in the mock provider. |
| Live RAG + ServiceNow | Gemini key, ServiceNow PDI, service-account credentials, and caller/group IDs | Real answers and real incidents when explicitly accepted. |

For the recommended mode, edit the root `.env`:

```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_LLM_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768
RAG_SIMILARITY_THRESHOLD=0.60

USE_MOCK_SERVICENOW=true
APP_PORT=8000
```

Keep the database settings supplied by `.env.example`. Configuration comes from `.env`, with normal shell environment variables taking precedence. Restart the backend after configuration changes. Never commit real keys or passwords.

If local PostgreSQL already occupies port 5432, change **both** values:

```env
POSTGRES_PORT=5433
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/service_desk
```

If backend port 8000 is occupied, set `APP_PORT=8007` or use the port overrides below. Keep embedding dimensions at 768 for the existing schema. Changing the embedding model requires re-ingestion; changing dimensions also requires a migration.

### 3. Start the stack

```bash
make start
make status
```

This starts PostgreSQL, waits for health, applies migrations, and launches FastAPI and Vite on localhost. Default addresses:

- Chat: [http://127.0.0.1:5173](http://127.0.0.1:5173)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

`make status` prints the actual URLs. Custom ports work together automatically:

```bash
make start BACKEND_PORT=8007 FRONTEND_PORT=5177
```

### 4. Index the knowledge base and verify live RAG

With a Gemini key configured and the database running:

```bash
cd backend
PYTHONPATH=. uv run --no-sync python ../scripts/verify_rag.py --live --ingest
cd ..
```

This checks model capabilities, embeds the seven synthetic documents, stores their vectors, and runs four acceptance cases. It makes Gemini API calls and may incur charges. It does not call ServiceNow. Later, `make rag-check` runs the larger 12-case dataset against existing vectors without re-ingestion.

### 5. Try these conversations

Use **New issue** between unrelated examples.

| Type or do this | Expected behavior |
|---|---|
| "How can I reset my corporate password?" | A cited answer when the KB evidence is sufficient. |
| "My GlobalProtect VPN is not connecting." | VPN guidance with a KB reference. |
| Then "The steps did not work." | An escalation offer, with no automatic ticket creation. |
| "No thanks." | No incident created. |
| "Create a ticket." | An incident using the retained issue context. Real when ServiceNow is enabled; mock otherwise. |
| Repeat "Create a ticket." | The same incident, without another create request. |
| "I need VS Code installed." | Software guidance and catalog direction, without silently creating an incident. |
| Ask an unrelated question | An escalation offer when evidence is insufficient. |

Mock incident records live in memory and reset when the backend restarts. Conversations and audit history remain in PostgreSQL. Use a new issue for a fresh mock-ticket demonstration after a restart.

## Connect your ServiceNow instance

Start with the recommended mock-ticketing mode, then follow [the ServiceNow setup guide](docs/servicenow-setup.md). Configure a dedicated service account, an active demo caller, and real assignment-group sys_ids. Set `USE_MOCK_SERVICENOW=false` only when ready to create real test incidents.

The backend supports Basic Auth for this PDI milestone. Missing specialist group mappings use the configured Service Desk fallback. Missing or invalid caller/group configuration blocks creation. Priority is calculated by deterministic impact/urgency rules; the returned ServiceNow priority is authoritative. The selected PDI uses P5 for low impact and low urgency; verify your own instance's policy.

## API

FastAPI publishes typed schemas and interactive requests at `/docs` on the backend URL printed by `make status`.

| Endpoint | Purpose |
|---|---|
| `GET /health` | App/configuration status; this is not a live dependency check. |
| `POST /api/chat` | Send a message, optionally continuing a saved `session_id`. |
| `POST /api/conversations` and `GET /api/conversations/{id}` | Reserve a conversation and reopen its history. |
| `GET /api/audit/{id}` | Inspect the conversation's retained audit events. |
| `POST /api/tickets` | Explicitly create/reconcile an incident through the selected provider. |
| `GET /api/tickets` and `GET/PATCH /api/tickets/{id}` | Query, retrieve, or update incidents. |
| `POST /api/knowledge/ingest`, `/search`, `/answer` | Ingest KB documents, retrieve passages, and generate a grounded answer. |
| `GET /api/devices/{id}/health` and `POST /api/devices/{id}/simulate` | Inspect/change synthetic device telemetry. |
| `POST /api/devices/{id}/remediate` | Run an allow-listed simulated tool. |

Direct ticket clients should supply a stable `correlation_id` and reuse it on retries. Omitting it treats each POST as a new incident request. See [the incident API behavior](docs/incident-workflow.md).

## Guardrails

- Recognized refusal takes precedence over ticket-creation language and the escalation flag. Deferred requests wait for explicit acceptance.
- Acceptance, the original request payload, and audit records commit before the external incident call. A database failure prevents dispatch.
- Repeated acceptance uses the saved incident attempt. Timeouts and uncertain results block another POST while correlation lookup checks the outcome.
- Every selected context chunk must pass the retrieval threshold. The client cannot lower it below the configured policy floor.
- Employee input and KB passages are treated as untrusted data. RAG has no ticketing or tool-execution capability; unsupported action fields in generated output are rejected.
- Model output must pass Pydantic validation and cite retrieved source IDs. Invalid output, missing evidence, and provider failures offer escalation.
- Reconciliation conflicts surface a manual-action message and a safe audit event rather than hiding the error.

These are tested workflow boundaries. Citation membership checks do not prove every sentence is supported, and prompt instructions do not guarantee resistance to every injection attempt.

## Testing and observed results

The detailed [validation report](docs/testing/2026-10-16-validation.md) records the run, reproduced defects, fixes, and limitations. The latest recorded checks on **2026-10-16** were:

| Check | Observed result |
|---|---|
| Isolated backend suite | 144 passed; seven PostgreSQL-only cases intentionally skipped here |
| Real PostgreSQL + pgvector suite | Those seven cases passed separately in a disposable database |
| Frontend checks | Eight passed; lint and production build passed |
| Service-control safety checks | Four passed, including stale PID protection and occupied-port refusal |
| Live RAG acceptance | 12 cases passed across all seven KB topics and five unsupported/adversarial prompts |
| ServiceNow | Live synthetic incident acceptance verified; later read-only retrieval succeeded |

These counts are a dated test snapshot, not a CI badge or a general accuracy benchmark. The project does not claim measured ticket reduction, employee time savings, or production routing accuracy.

```bash
make test            # Isolated tests; no live provider calls
make lint
make build
make test-postgres   # Disposable local database; requires create/drop permission
make rag-check       # Live Gemini calls against ingested synthetic KB
```

The PostgreSQL runner tests migrations in both directions, real vector filtering, ingestion rollback, persistence, and a 16-request acceptance burst that dispatched once. Live evidence files and runtime logs are ignored by Git.

## Everyday commands

```bash
make start
make status
make logs SERVICE=backend
make logs-follow
make restart
make stop            # Keeps the PostgreSQL data volume
make help
```

Use the same custom port overrides with `make restart`. `make stop-apps` leaves the database running. The controller stops only app process groups it started; it does not kill other services to free a port. More detail: [local development guide](docs/local-development.md).

## Repository map

```text
backend/app/
  api/             FastAPI routes and typed request boundaries
  services/        Conversation, escalation, RAG, classification, routing
  integrations/    Gemini, ServiceNow, and synthetic telemetry adapters
  repositories/    Persistence and pgvector queries
  models/          Domain schemas and database models
backend/alembic/   Database migrations
backend/tests/     Isolated and opt-in PostgreSQL tests
frontend/          React + TypeScript chat and device-demo UI
knowledge-base/    Synthetic IT-support Markdown articles
evaluation/        Labelled live RAG acceptance cases
scripts/           Local service control and explicit verification commands
tests/             Service-controller safety checks
docs/              Setup guides, design decisions, research, and test evidence
```

## Current limits

- Local conversations are shared demo data. Authentication, per-user authorization, and rate limiting are not implemented. Keep the app on localhost.
- Intent classification and routing use language rules; they do not understand every phrasing or enterprise policy.
- RAG validates output structure and source IDs, not claim-level factual support. The live dataset is small.
- The seven articles are synthetic. Larger or multilingual ingestion needs token-aware chunking and a reviewed document lifecycle.
- Remediation and endpoint experience data are simulated. There is no Nexthink tenant or real endpoint execution.
- Formal service requests, production SSO, Teams integration, and cloud deployment remain future work.

## What comes next

Improve classification for troubleshooting versus software requests, expand the evaluation dataset, add claim-level grounding checks, and define user ownership/access before considering a shared deployment. Real remediation needs its own approval and durable audit controls.

For changes, [open a GitHub issue](https://github.com/pulkitv52/AI_service_desk_copilot/issues) describing the behavior and expected outcome. Run the checks above, keep provider-specific code behind its adapter, and keep credentials and personal test data out of commits.
