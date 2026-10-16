# Reliable incident escalation

Agreed milestone: stabilize incident escalation before extending RAG or remediation.

- One issue per conversation, with persisted messages and reopenable history.
- Failed troubleshooting offers escalation. Only an explicit request or acceptance creates an incident; refusal wins over creation keywords.
- Persist acceptance, ticket payload, and audit event before contacting ServiceNow. A database failure stops creation.
- Repeated acceptance returns the same ticket. Timeouts, crashes after dispatch, and failures recording the result remain pending verification. Reconcile by correlation identifier; absence of a result does not authorize another create.
- Use a configured PDI caller and explicit assignment-group sys_ids, with a Service Desk fallback.
- Escalation remains available during Gemini or retrieval outages.
- Software requests provide guidance; catalog submission is unavailable in this milestone.
- Tests isolate credentials, network access, and application persistence. Acceptance includes a deliberately triggered live VPN escalation, correct routing, retained number/audit, no creation on decline, and no duplicate on repeated acceptance.
- Frontend health requests reach FastAPI; external errors do not expose credentials.

## Review fixes on 2026-10-16

- Refusal clauses take precedence over creation instructions, including “Create a ticket? Not now.” and “Create a ticket, but do not submit it.” Symptom descriptions such as applications stopping do not count as cancellation.
- Ordinary follow-ups and refusals preserve the pending-verification banner and status-check control until an incident is confirmed or its durable status is checked.
- Retrying a definitely rejected submission audits the original saved payload actually dispatched, rather than a newer incoming transcript.
- Multiple incidents matching one correlation ID return HTTP 409 with code `manual_reconciliation_required` through chat and verification APIs. The UI explains that manual reconciliation in ServiceNow is required. Creation remains blocked; each failed lookup records a safe audit event and correlated diagnostic without external error text.
- Validation: 92 backend tests and eight frontend checks passed; frontend lint and production build passed. Regression checks use isolated persistence and mocked providers. No live ServiceNow records were changed.

Production authentication, formal catalog requests, RAG extensions, and real endpoint remediation remain outside this milestone. This local demo shares conversations across its users.

## Verification on 2026-10-15

- 65 automated backend tests passed with external HTTP blocked and temporary SQLite persistence.
- Frontend production build and lint passed.
- Migration `002_conversations` applied to local PostgreSQL on port 5433; pgvector confirmed enabled.
- PostgreSQL workflow verified retained issue context, history/audit, and reuse of one mock incident on repeated acceptance.
- Browser check verified escalation offer, refusal without creation, explicit mock incident creation with the original VPN context, New issue, and reopening saved messages.
- Live PDI acceptance passed with a dedicated web-service-only account: created `INC0010001` for the synthetic VPN issue, verified its configured caller and Network routing, confirmed refusal created nothing, and confirmed repeated acceptance reused the same incident.
- The initial ServiceNow submission timed out. The workflow retained pending verification, then found the committed incident by correlation ID and recorded `ticket_reconciled`, without another creation request.
- The resumable local evidence is in ignored `sample-data/incident-demo.local`; PostgreSQL retains the messages and audit events for the saved conversation. The incident number is an observed test result, not a performance metric.

## Follow-up observed during live verification

Priority alignment is now corrected: the local matrix matches all nine rows inspected in the PDI Priority Data Lookup table (`dl_u_priority`), including low impact + low urgency → `P5` (Planning). P5 is supported in backend and frontend classification types, mock creation and updates use the same matrix, and the UI prefers the returned ticket priority over historical classification. Missing provider priorities display as unspecified. Saved historical classifications remain as recorded; no incident or audit history was rewritten. The service account lacks read permission for the lookup table, so verification used the signed-in admin browser without changing permissions. The current configured demo caller is the service-account user; set a separate synthetic employee caller ID when preparing an employee-facing demo.

Priority-alignment validation: 79 backend tests passed, three rendered-component checks passed, frontend build/lint passed, and a read-only lookup of `INC0010001` confirmed that the new local calculation and the live incident both report `P5`. No ServiceNow incident or priority rules were changed.

## Additional boundary validation on 2026-10-16

Thorough testing reproduced and fixed deferred/withdrawn-consent cases and loss of an existing attempt after later troubleshooting changed classification. Conditional requests now require a later explicit acceptance; refusal still wins over the force flag. Existing attempts remain authoritative when later wording resembles a software request. See [the validation report](testing/2026-10-16-validation.md) for test results and limits.
