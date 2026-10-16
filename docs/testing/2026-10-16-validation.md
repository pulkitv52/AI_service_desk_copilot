# Validation run — 2026-10-16

Scope: current uncommitted implementation, including grounded RAG, durable incident escalation, consent, audit persistence, embedding provenance, and frontend recovery. No commits or live ServiceNow writes were made.

## Results

| Layer | Observed result |
|---|---|
| Default isolated backend suite | 144 passed; seven PostgreSQL-only tests intentionally skipped here |
| Disposable PostgreSQL suite | All seven skipped-above tests passed separately against actual PostgreSQL + pgvector |
| Migration lifecycle | Fresh upgrade to `002_conversations`, downgrade to base, and re-upgrade passed in a disposable database |
| Frontend | Eight checks passed; lint and production build passed |
| Live RAG | All 12 cases in `evaluation/rag-acceptance.json` passed using Gemini 3.5 Flash Lite and the stored real embedding profile |
| Browser | Cited password/VPN answers, refusal, explicit mock escalation, repeated acceptance, New issue, reopening history, and history recovery after reload verified |
| ServiceNow | Read-only caller/group checks and retrieval of the existing synthetic `INC0010001` succeeded; returned P5 and Network Support |
| Diff hygiene | `git diff --check` passed; `.env` and local live-test evidence remain ignored |

These case results do not establish general accuracy or a production security guarantee. The suite counts exclude the 12 live acceptance cases and manual browser observations.

## Defects reproduced and corrected

1. Mixed cancellation and deferred consent: five new boundary cases initially created a mock incident, including “Create a ticket, but do not send it,” “Create a ticket? No need,” and “Create a ticket when I confirm.” Refusal recognition now handles these withdrawal forms. Future-condition requests offer confirmation instead of dispatching, including with a force flag. Without issue details, deferred requests ask for an issue rather than inventing one. Later explicit acceptance remains possible.
2. Existing-attempt recovery after classification changes: adding “I tried reinstalling GlobalProtect and it still fails” could change classification to software request, causing repeated acceptance to hide an existing or pending incident. Two tests reproduced this for created and timed-out attempts. Existing durable attempts now take precedence over the new-software-request guard; the saved incident is returned or reconciled without another POST. New software requests still do not create incidents.

Both defects were observed with failing endpoint tests before fixes. The final suite includes their regression cases.

## Persistence and failure checks

The PostgreSQL runner creates a randomly named local test database, applies actual migrations, runs tests, and drops that database in a finally block. Verified:

- Real cosine ranking, result limits, category filtering, exclusion of wrong embedding profiles and legacy vectors.
- Re-ingestion replaces chunks without duplicates; failed generation of embeddings or a mismatched batch rolls back and preserves the previously committed document/chunks.
- A 16-request concurrent acceptance burst dispatched one provider create and retained one accepted attempt.
- An externally committed incident is recovered in a new database session after simulated worker loss, without redispatch.
- Conversation messages and audit records survive reopening in a new session.

Other isolated tests cover unusable ServiceNow POST replies followed by correlation lookup, bounded embedding retries for transient failures, permanent errors without retry, document/query task separation, citation/output validation, and prevention of retrieved instructions from authorizing actions.

## Live and browser checks

The live RAG dataset covers every current KB topic: password, VPN, disk space, approved software, Outlook, Teams, and SAP. Five additional cases check unrelated topics, secret disclosure requests, and instruction overrides. Supported cases returned the expected source IDs; unsupported/adversarial cases offered escalation. Evidence, answers, retrieval scores, and selected chunks are saved in ignored `sample-data/rag-verification.local`. No re-ingestion was performed during this run.

The browser used temporary ports 5177/8007 and another disposable PostgreSQL database with a copy of the synthetic KB vectors. Ticketing was explicitly mock mode, and live ServiceNow create/update methods were disabled. Password and VPN answers used real Gemini. Browser console inspection found no warnings/errors. Repeated acceptance showed the same mock incident and one item in the recent-ticket list. The temporary tab, servers, and database were cleaned up.

A transient HTTP 503 during browser generation and a timeout during the live acceptance run were observed; configured retries recovered. These observations do not establish a latency SLA.

## Reproduce

From the repository root:

```bash
cd backend
uv run pytest -q
PYTHONPATH=. uv run python ../scripts/verify_postgres.py
PYTHONPATH=. uv run python ../scripts/verify_rag.py --live --cases ../evaluation/rag-acceptance.json
```

The PostgreSQL command requires local permission to create/drop a disposable database. The live RAG command uses the configured Gemini key, sends only synthetic prompts and KB evidence, and may incur API charges. It does not call ServiceNow.

For frontend checks, run `pnpm test`, `pnpm lint`, and `pnpm build` from `frontend/`.

## Remaining limits

- Citation membership is validated; individual claims are not independently checked for entailment by their cited passages.
- Refusal and intent classification remain deterministic language rules, not comprehensive natural-language understanding. Unambiguous escalation controls are preferable to relying on arbitrary phrasing.
- The live dataset is small and fixed. Model outputs may vary; these passing cases are not a broad adversarial benchmark.
- Application authentication, per-user conversation authorization, and rate limiting remain outside the local MVP milestone.
- Arbitrary large or multilingual KB uploads still require token-aware chunking. Current validation covers the seven English synthetic documents.
- Endpoint remediation remains simulated; these tests do not validate actions on real enterprise devices.
