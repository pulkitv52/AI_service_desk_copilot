"""Read-only capability verification for explicitly configured Gemini models."""

import httpx


async def verify_models(
    api_key: str, generation_model: str, embedding_model: str
) -> dict[str, str]:
    selected = {generation_model: "generateContent", embedding_model: "embedContent"}
    async with httpx.AsyncClient(timeout=20) as client:
        for model, method in selected.items():
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}",
                headers={"x-goog-api-key": api_key},
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Configured Gemini model capability check failed (HTTP {response.status_code})"
                )
            if method not in response.json().get("supportedGenerationMethods", []):
                raise RuntimeError(
                    "Configured Gemini model does not support the required capability"
                )
    return {"generation_model": generation_model, "embedding_model": embedding_model}
