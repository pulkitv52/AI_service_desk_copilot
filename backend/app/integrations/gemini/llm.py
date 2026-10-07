from typing import Any, Optional, Protocol, runtime_checkable
import httpx

from app.core.logging import get_logger

logger = get_logger("gemini_llm")


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM text and structured response generation."""

    async def generate(
        self, prompt: str, system_instruction: Optional[str] = None
    ) -> str:
        """Generate text completion from prompt."""
        ...


class MockLLMProvider:
    """Mock LLM provider returning realistic grounded responses for testing."""

    def __init__(self) -> None:
        pass

    async def generate(
        self, prompt: str, system_instruction: Optional[str] = None
    ) -> str:
        # Extract user request part if structured prompt
        text_to_check = prompt
        for marker in ["Employee Request:\n", "User Support Request:\n"]:
            if marker in prompt:
                text_to_check = prompt.split(marker)[1]
                break

        prompt_lower = text_to_check.lower()
        if "password" in prompt_lower:
            return (
                "To reset your corporate password, please navigate to the Self-Service "
                "Password Reset (SSPR) portal at https://passwordreset.corp.internal, "
                "authenticate using your registered MFA device, and select a new password "
                "satisfying the 14-character minimum policy.\n\n"
                "Sources: [KB-SEC-001 - Self-Service Password Reset Guide]"
            )
        elif "vpn" in prompt_lower:
            return (
                "For VPN connectivity issues, please try restarting the GlobalProtect "
                "service from Settings > Troubleshooting > Restart Service, or verify "
                "that your local internet connection is functional.\n\n"
                "Sources: [KB-NET-002 - Corporate VPN Connectivity Troubleshooting]"
            )
        elif "disk" in prompt_lower:
            return (
                "To free up disk space on your laptop, empty the Recycle Bin, clean temporary "
                "files from %TEMP%, and purge local developer caches.\n\n"
                "Sources: [KB-EUC-003 - Endpoint Low Disk Space Remediation Guide]"
            )
        elif "install" in prompt_lower or "software" in prompt_lower:
            return (
                "To install approved software packages, open the Company Portal application on "
                "Windows or Self Service on macOS, find the application in the catalog, and click Install.\n\n"
                "Sources: [KB-EUC-004 - Enterprise Software Installation and Service Requests]"
            )
        elif "sap" in prompt_lower:
            return (
                "For SAP Purchase Order authorization errors, check transaction /nSU53 "
                "for missing authorization objects (such as M_EINK_FRG) and verify with "
                "your manager if your approval limit matches the PO value.\n\n"
                "Sources: [KB-APP-007 - SAP ERP and Fiori Purchase Order Authorization Support]"
            )
        return (
            "I have reviewed your request. Based on our enterprise IT knowledge base, "
            "here are the recommended steps for your issue.\n\n"
            "Sources: [Knowledge Base]"
        )


class GeminiLLMProvider:
    """Provider for Google Gemini Flash models via REST API with retries and failover."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        backup_model: str = "gemini-3.1-flash-lite-preview",
        timeout_seconds: float = 20.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.backup_model = backup_model
        self.timeout = timeout_seconds
        self._external_client = client
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def generate(
        self, prompt: str, system_instruction: Optional[str] = None
    ) -> str:
        import asyncio

        models_to_try = [self.model]
        if self.backup_model and self.backup_model != self.model:
            models_to_try.append(self.backup_model)

        contents: list[dict[str, Any]] = [{"role": "user", "parts": [{"text": prompt}]}]
        payload: dict[str, Any] = {"contents": contents}

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        client = self._get_client()
        should_close = self._external_client is None
        last_error: Optional[Exception] = None

        try:
            for model_name in models_to_try:
                url = f"{self.base_url}/models/{model_name}:generateContent?key={self.api_key}"
                # Retry transient errors up to 2 times per model
                for attempt in range(2):
                    try:
                        response = await client.post(url, json=payload)
                        if response.status_code in (429, 500, 502, 503, 504):
                            logger.warning(
                                "Transient Gemini error HTTP %s on model %s (attempt %d/2). Retrying...",
                                response.status_code,
                                model_name,
                                attempt + 1,
                            )
                            await asyncio.sleep(0.75 * (attempt + 1))
                            continue

                        response.raise_for_status()
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if not candidates:
                            return "I was unable to generate an answer for this request."
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_result = "".join(part.get("text", "") for part in parts)
                        return text_result.strip()

                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        logger.warning(
                            "Network/timeout error on model %s (attempt %d/2): %s",
                            model_name,
                            attempt + 1,
                            exc,
                        )
                        last_error = exc
                        await asyncio.sleep(0.75 * (attempt + 1))
                    except httpx.HTTPStatusError as exc:
                        last_error = exc
                        # If 404 or other non-transient client error, switch model immediately
                        break
                    except Exception as exc:
                        last_error = exc
                        break

            if last_error:
                logger.error("All Gemini LLM models exhausted. Last error: %s", last_error)
                raise RuntimeError(f"Gemini API error: {last_error}") from last_error

            return "I was unable to process this request at this time."
        finally:
            if should_close:
                await client.aclose()
