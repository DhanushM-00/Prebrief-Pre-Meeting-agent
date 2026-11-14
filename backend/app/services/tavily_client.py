"""Thin async client for Tavily Search.

Supports include_images / include_image_descriptions per Tavily docs:
https://docs.tavily.com/documentation/api-reference/endpoint/search
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

import httpx

from app.core.errors import UpstreamError
from app.services.cache import SearchCache

log = logging.getLogger("prebrief.tavily")
_RETRY_STATUS = {429, 500, 502, 503, 504}


class TavilyClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.tavily.com",
        timeout: float = 20.0,
        cache: SearchCache | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
        backoff: float = 0.5,
    ):
        self._cache = cache
        self._max_attempts = max_attempts
        self._backoff = backoff
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def search(
        self,
        query: str,
        *,
        topic: str = "news",
        start_date: str | None = None,
        end_date: str | None = None,
        max_results: int = 8,
        search_depth: str = "basic",
        include_images: bool = False,
        include_image_descriptions: bool = False,
        time_range: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return result rows only (backward compatible)."""
        data = await self.search_full(
            query,
            topic=topic,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results,
            search_depth=search_depth,
            include_images=include_images,
            include_image_descriptions=include_image_descriptions,
            time_range=time_range,
        )
        results = data.get("results", [])
        if not isinstance(results, list):
            raise UpstreamError("Research provider returned an unexpected response.")
        return results

    async def search_full(
        self,
        query: str,
        *,
        topic: str = "general",
        start_date: str | None = None,
        end_date: str | None = None,
        max_results: int = 8,
        search_depth: str = "basic",
        include_images: bool = False,
        include_image_descriptions: bool = False,
        time_range: str | None = None,
    ) -> dict[str, Any]:
        """Full Tavily response including top-level images when requested."""
        payload: dict[str, Any] = {
            "query": query,
            "topic": topic,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": include_images,
            "include_image_descriptions": include_image_descriptions,
        }
        # Prefer explicit dates; time_range is an alternative (day/week/month/year)
        if start_date:
            payload["start_date"] = start_date
        if end_date:
            payload["end_date"] = end_date
        if time_range and not start_date:
            payload["time_range"] = time_range

        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if self._cache and (hit := self._cache.get(key)) is not None:
            if isinstance(hit, dict) and "results" in hit:
                return hit
            # Legacy cache stored only results list
            return {"results": hit, "images": []}

        data = await self._post(payload)
        if self._cache:
            self._cache.set(key, data)
        return data

    async def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        last = "unknown error"
        for attempt in range(self._max_attempts):
            try:
                res = await self._http.post("/search", json=payload)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last = f"network error ({type(exc).__name__})"
            else:
                if res.status_code == 200:
                    try:
                        return res.json()
                    except ValueError:
                        raise UpstreamError("Research provider returned invalid JSON.") from None
                if res.status_code in (401, 403):
                    raise UpstreamError("Research provider rejected the API key.")
                if res.status_code == 432 or res.status_code == 433:
                    raise UpstreamError("Research provider usage limit reached.")
                if res.status_code not in _RETRY_STATUS:
                    raise UpstreamError(f"Research provider error ({res.status_code}).")
                last = f"status {res.status_code}"
            if attempt < self._max_attempts - 1:
                await asyncio.sleep(self._backoff * (2**attempt))
        log.warning("tavily failed after retries: %s", last)
        raise UpstreamError("Research provider is temporarily unavailable.")
