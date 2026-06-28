"""
Aros Market API klient xizmati.
"""

import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx

from config import settings
from models import Product
from services.parser import parse_search_results, parse_similar_products

logger = logging.getLogger(__name__)


class ArosAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ArosAPIClient:
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ArosAPIClient":
        self._client = httpx.AsyncClient(
            base_url=settings.AROS_BASE_URL,
            timeout=httpx.Timeout(settings.HTTP_TIMEOUT),
            headers={"Accept": "application/json", "User-Agent": "ArosMarketBot/1.0"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def _get(self, url: str, **params: Any) -> dict | list:
        assert self._client
        last_error: Exception | None = None

        for attempt in range(1, settings.HTTP_MAX_RETRIES + 1):
            try:
                response = await self._client.get(url, params=params)
                if response.status_code == 404:
                    raise ArosAPIError("Mahsulot topilmadi", status_code=404)
                if response.status_code >= 500:
                    raise ArosAPIError(f"Server xatoligi: {response.status_code}", status_code=response.status_code)
                response.raise_for_status()
                return response.json()
            except ArosAPIError:
                raise
            except httpx.TimeoutException:
                last_error = ArosAPIError("So'rov vaqti tugadi.")
                logger.warning("Timeout [urinish %d]: %s", attempt, url)
            except httpx.ConnectError:
                last_error = ArosAPIError("Internetga ulanib bo'lmadi.")
                logger.warning("Ulanish xatoligi [urinish %d]: %s", attempt, url)
            except httpx.HTTPStatusError as e:
                last_error = ArosAPIError(f"HTTP xatoligi: {e.response.status_code}")

        raise last_error or ArosAPIError("Noma'lum xatolik.")

    async def search(self, query: str) -> list[Product]:
        data = await self._get(
            "/product/product_variant_list/cursor-search/",
            query=query,
            page_size=settings.AROS_PAGE_SIZE,
        )
        return parse_search_results(data)

    async def get_similar(self, product_id: str | int) -> list[Product]:
        data = await self._get(f"/product/get_similar_product_variants/{product_id}/")
        return parse_similar_products(data)


@asynccontextmanager
async def get_api_client() -> AsyncIterator[ArosAPIClient]:
    async with ArosAPIClient() as client:
        yield client
