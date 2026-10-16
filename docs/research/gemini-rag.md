# Gemini configuration for the RAG milestone

Researched: 2026-10-16. Scope: official public documentation and the existing integration source. No credentials were read and no authenticated, embedding, or generation requests were made.

## Generation model

Google documents **`gemini-3.5-flash-lite`** as a stable model, with text output and structured-output support. This verifies the project’s requested model name in public documentation; it does not establish access or quota for this project’s API key. Keep this exact model as the default rather than substituting a newer model. [Official model specification](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite).

For this generation, remove deprecated sampling parameters (`temperature`, `top_p`, `top_k`) and avoid ending requests with a prefilled model turn. The existing single user-turn REST request can remain; switching SDKs or adopting an agent API is unnecessary for this milestone. [Official migration guide](https://ai.google.dev/gemini-api/docs/generate-content/whats-new-gemini-3.6).

## Embedding choice

**`gemini-embedding-001` remains available for text.** It supports 768 dimensions, `RETRIEVAL_DOCUMENT` for indexed chunks, and `RETRIEVAL_QUERY` for search inputs. Request 768 explicitly and manually L2-normalize returned vectors. The newer `gemini-embedding-2` uses task instructions instead of the `taskType` field and produces an incompatible embedding space: migration requires re-embedding the corpus. Preserve `001` for this text-only milestone. [Official embedding guide and migration notes](https://ai.google.dev/gemini-api/docs/embeddings).

The `001` specification lists a 2,048-token input limit. Chunking must respect that limit; character counts alone are not a token guarantee. [Embedding model specification](https://ai.google.dev/gemini-api/docs/models/gemini-embedding-001).

## Capability preflight

Use the existing HTTP client for a read-only `GET https://generativelanguage.googleapis.com/v1beta/models`, following every `nextPageToken`. Check the exact returned names and `supportedGenerationMethods`: generation needs `generateContent`; embeddings need `embedContent`. `models.get` can inspect a specific model. A successful metadata check still does not prove a later paid operation will succeed. [Models REST reference](https://ai.google.dev/api/models).

Send the credential in `x-goog-api-key`, as in Google’s REST examples, and print only model names/capabilities—not credentials or authorization headers. [REST authentication example](https://ai.google.dev/gemini-api/docs/embeddings#rest).

## Minimal implementation recommendation

These are project recommendations, based on the sources above and the current source files:

- Add explicit configuration for generation model `gemini-3.5-flash-lite`, embedding model `gemini-embedding-001`, and embedding dimension `768`. Reject unsupported dimensions against the existing `vector(768)` schema instead of silently changing storage.
- Remove the current implicit generation failover to a different model. Model fallback should require explicit configuration; unavailable generation should produce the agreed escalation offer.
- Distinguish query and document embedding operations behind the existing provider abstraction. Validate exactly 768 finite values with a nonzero norm before normalizing. Keep HTTP details in the Gemini integration layer.
- Record embedding model, dimension, and provider mode with ingestion metadata. Re-ingest existing mock or differently configured vectors before using real query vectors; dimensional equality does not imply compatible embeddings.
- Keep PostgreSQL/pgvector and `httpx`; no extra SDK or vector store is needed.
- Run an explicit model metadata preflight before any real ingestion. Then separately verify real embeddings and retrieval with the synthetic KB, documenting actual outcomes rather than claiming semantic quality from mock tests.

The source inspection found `GeminiLLMProvider` defaulting to `gemini-2.5-flash` with a `gemini-3.1-flash-lite-preview` backup, while `GeminiEmbeddingProvider` already targets `gemini-embedding-001` and requests 768 dimensions. The latter currently lacks task-type separation, response validation, and real-vector normalization. `KnowledgeChunk` currently stores `vector(768)`. These observations describe the source at research time, not changes made by this note.
