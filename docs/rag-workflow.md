# Grounded knowledge answers

The current milestone uses `gemini-3.5-flash-lite` and `gemini-embedding-001` with 768-dimensional normalized vectors in PostgreSQL/pgvector. The API key stays in `.env` and is sent in a header. See [the cited model research](research/gemini-rag.md) for the provider facts.

## Setup and verification

Set the following alongside `GEMINI_API_KEY` in `.env`:

```env
GEMINI_LLM_MODEL=gemini-3.5-flash-lite
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
GEMINI_EMBEDDING_DIMENSION=768
RAG_SIMILARITY_THRESHOLD=0.60
```

Apply existing migrations to the local database, then explicitly run the live acceptance check:

```bash
cd backend
uv run alembic upgrade head
PYTHONPATH=. uv run python ../scripts/verify_rag.py --live --ingest
```

This sends the project's synthetic IT documents and acceptance questions to Gemini and may incur API charges. It does not call ServiceNow. Omit `--ingest` on later checks to reuse stored vectors. A read-only model capability check runs first. The command exits nonzero if any acceptance case fails and saves details in ignored `sample-data/rag-verification.local`.

Ingestion uses `RETRIEVAL_DOCUMENT`; search uses `RETRIEVAL_QUERY`. Every embedding must contain exactly 768 finite values with a nonzero norm. Document metadata records the provider/model/dimension/task-profile version, and search filters by that profile. Legacy vectors without this metadata and vectors from another provider are excluded until re-ingested. Switching models with the same vector length does not make their embedding spaces compatible. The dimension is fixed to the existing `vector(768)` migration; changing it requires a schema migration and re-ingestion.

## Answer policy

- Every selected chunk must pass the configured similarity threshold; callers can tighten the threshold but cannot reduce it below the configured floor of at least 0.60. Mock embeddings use the same floor and do not establish real semantic quality.
- Context is limited to four chunks, each capped at 2,800 characters for generation. The current seven English synthetic documents fit the embedding model's input limit; arbitrary larger or multilingual uploads require token-aware chunking before supporting them.
- Employee input and retrieved evidence are placed in a JSON data envelope and identified as untrusted data in the system instruction.
- Gemini returns JSON, validated with Pydantic. Only `answerable`, `answer`, and `source_ids` are accepted; tool/action fields are rejected. RAG has no tool execution or ticketing capability.
- An answer must declare retrieved source IDs and cite those IDs inline. Missing, invented, or inconsistent citations cause escalation fallback. Displayed sources come from retrieved metadata, not model-provided titles.
- Retrieval errors, invalid model output, model abstention, and generation outages offer escalation. Raw chunks are no longer substituted as a successful generated answer. The conversation requires explicit user acceptance before incident creation.
- Conversation audit events retain retrieved chunks/scores, selected chunk IDs, fallback reason, and the final response in saved message history.

These checks verify citation membership and workflow boundaries. They do not prove that every sentence is supported by its cited passage or guarantee resistance to every prompt injection. Claim-level evidence checking, a larger adversarial evaluation set, and calibration of retrieval thresholds remain future work. Similarity is a retrieval score, not a calibrated probability of correctness.

## Observed verification, 2026-10-16

The live check re-ingested seven documents into 42 chunks using the configured real embedding profile. Password-reset and GlobalProtect VPN questions returned cited answers from their expected KB sources. An unrelated submarine-navigation question fell below the retrieval threshold and offered escalation. An instruction-override request reached generation and the model abstained. All four acceptance cases passed. These four observations are not a benchmark accuracy measurement.

Isolated tests additionally cover weak-chunk exclusion, unsupported citations, malformed output, attempted tool-call output, retrieval/generation failures, embedding shape/norm validation, and a retrieved injection that cannot authorize incident creation. No ServiceNow records were created or changed for this milestone.

Final validation: 120 backend tests and eight frontend checks passed, along with frontend lint, production build, and `git diff --check`.

## Extended validation

The [2026-10-16 validation report](testing/2026-10-16-validation.md) records a later 12-case live run covering all seven KB topics plus five unsupported/adversarial requests, seven disposable PostgreSQL integration tests, browser verification, and the expanded backend regression suite. Repeat the live cases using `--cases ../evaluation/rag-acceptance.json` from `backend/`; re-ingestion is not required.
