import asyncio
import math
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import UpstreamServiceError, UpstreamTimeoutError


class LLMClient:
    def __init__(self, client: httpx.AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    @classmethod
    def from_settings(cls, settings: Settings) -> "LLMClient":
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": "https://github.com/ivanivanyuk1993/code-review-assistant",
            "X-Title": "Code Review Assistant",
        }
        client = httpx.AsyncClient(
            base_url=settings.openrouter_base_url,
            headers=headers,
            timeout=settings.http_timeout,
        )
        return cls(client, settings)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            response = await self._client.get("/models", timeout=5.0, follow_redirects=False)
            if response.status_code in {200, 301, 302, 307, 308}:
                return True
            response.raise_for_status()
            return True
        except httpx.RequestError as exc:  # pragma: no cover - guard path
            raise UpstreamServiceError(f"OpenRouter health failed: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise UpstreamServiceError(
                f"OpenRouter health failed: {exc.response.status_code} {exc.response.text}"
            ) from exc

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        max_attempts = self._settings.max_retries
        for attempt in range(max_attempts):
            try:
                response = await self._client.post("/chat/completions", json=payload)
                response.raise_for_status()
                data = response.json()
                # Check if OpenRouter returned an error in the response body
                if isinstance(data, dict) and "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    error_code = data["error"].get("code", 500)
                    raise UpstreamServiceError(f"OpenRouter error {error_code}: {error_msg}")
                return data
            except httpx.TimeoutException as exc:
                if attempt == max_attempts - 1:
                    raise UpstreamTimeoutError("OpenRouter request timed out") from exc
                await self._sleep(attempt)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status in {429, 502, 503, 504} and attempt < max_attempts - 1:
                    await self._sleep(attempt)
                    continue
                raise UpstreamServiceError(
                    f"OpenRouter request failed: {status} {exc.response.text}"
                ) from exc
            except httpx.RequestError as exc:  # pragma: no cover - guard path
                if attempt == max_attempts - 1:
                    raise UpstreamServiceError(f"OpenRouter request error: {exc}") from exc
                await self._sleep(attempt)
        raise UpstreamServiceError("OpenRouter request failed after retries")

    async def _sleep(self, attempt: int) -> None:
        delay = self._settings.backoff_factor * math.pow(2, attempt)
        await asyncio.sleep(delay)
