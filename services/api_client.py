"""
Aros Market API klient xizmati.
Login, mahsulot qidirish, savat operatsiyalari.
"""

import asyncio
import logging
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional
from urllib.parse import urlparse, parse_qs

import httpx

from config import settings
from models import Product, UserProfile, CartItem
from services.parser import parse_search_results, parse_similar_products

logger = logging.getLogger(__name__)


class ArosAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class ArosAPIClient:
    def __init__(self, token: Optional[str] = None) -> None:
        self._client: httpx.AsyncClient | None = None
        self._token = token

    def _build_headers(self) -> dict:
        headers = {"Accept": "application/json", "User-Agent": "ArosMarketBot/1.0"}
        if self._token:
            headers["Authorization"] = f"Token {self._token}"
        return headers

    async def __aenter__(self) -> "ArosAPIClient":
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.HTTP_TIMEOUT),
            headers=self._build_headers(),
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _url(self, path: str) -> str:
        if path.startswith("/web/"):
            return f"https://api.aros.uz/api{path}"
        return f"{settings.AROS_BASE_URL}{path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict | list:
        """Umumiy HTTP so'rov metodi. Vaqtincha xatolarda qayta urinadi."""
        assert self._client
        last_error: Exception | None = None

        for attempt in range(1, settings.HTTP_MAX_RETRIES + 1):
            try:
                response = await self._client.request(method, self._url(path), **kwargs)

                if response.status_code == 401:
                    raise ArosAPIError("Avtorizatsiya xatoligi. Qayta login qiling.", status_code=401)
                if response.status_code == 404:
                    raise ArosAPIError("Topilmadi.", status_code=404)
                if response.status_code == 400:
                    detail = response.text
                    try:
                        body = response.json()
                        detail = body.get("detail") or body.get("message") or str(body)
                    except Exception:
                        pass
                    logger.warning("400 Bad Request [%s]: %s", path, detail)
                    raise ArosAPIError(f"So'rov xato: {detail}", status_code=400)
                if response.status_code >= 500:
                    last_error = ArosAPIError(
                        f"Server xatoligi: {response.status_code}",
                        status_code=response.status_code,
                    )
                    logger.warning("5xx xato [urinish %d/%d]: %s -> %d",
                                   attempt, settings.HTTP_MAX_RETRIES, path, response.status_code)
                    if attempt < settings.HTTP_MAX_RETRIES:
                        await asyncio.sleep(0.5 * attempt)
                        continue
                    raise last_error

                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}

            except ArosAPIError:
                raise
            except httpx.TimeoutException:
                last_error = ArosAPIError("So'rov vaqti tugadi.")
                logger.warning("Timeout [urinish %d/%d]: %s", attempt, settings.HTTP_MAX_RETRIES, path)
            except httpx.ConnectError:
                last_error = ArosAPIError("Internetga ulanib bo'lmadi.")
                logger.warning("Ulanish xatosi [urinish %d/%d]: %s", attempt, settings.HTTP_MAX_RETRIES, path)
            except httpx.HTTPStatusError as e:
                last_error = ArosAPIError(f"HTTP xatoligi: {e.response.status_code}")

            if attempt < settings.HTTP_MAX_RETRIES:
                await asyncio.sleep(0.5 * attempt)

        raise last_error or ArosAPIError("Noma'lum xatolik.")

    async def _get(self, path: str, **params: Any) -> dict | list:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, data: dict | list) -> dict | list:
        return await self._request("POST", path, json=data)

    async def _delete(self, path: str) -> dict | list:
        return await self._request("DELETE", path)

    # ─── AUTH ────────────────────────────────────────────────────────────────

    async def send_sms(self, phone: str) -> None:
        await self._post("/web/v2/users/get_verification_code/", {
            "verification_type": "login",
            "phone_number": phone,
        })

    async def verify_sms(self, phone: str, code: str) -> str:
        data = await self._post("/web/v2/users/login/", {
            "verification_type": "login",
            "phone_number": phone,
            "code": code,
        })
        token = data.get("token") if isinstance(data, dict) else None
        if not token:
            raise ArosAPIError("Token olinmadi. Kod noto'g'ri bo'lishi mumkin.")
        return token

    async def get_profile(self) -> UserProfile:
        data = await self._get("/user/me/")
        if not isinstance(data, dict):
            raise ArosAPIError("Profil ma'lumotlari noto'g'ri.")

        # warehouse int yoki dict bo'lishi mumkin — ikkalasini ham qo'llab-quvvatlaymiz
        warehouse = data.get("warehouse") or {}
        send_warehouse = data.get("send_warehouse") or {}

        if isinstance(warehouse, int):
            warehouse_id = warehouse
            warehouse_name = ""
            region_id = None
        elif isinstance(warehouse, dict):
            warehouse_id = warehouse.get("id")
            warehouse_name = warehouse.get("name") or warehouse.get("name_uz") or ""
            region_id = warehouse.get("region") or warehouse.get("region_id")
        else:
            warehouse_id = None
            warehouse_name = ""
            region_id = None

        if isinstance(send_warehouse, int):
            send_warehouse_id = send_warehouse
        elif isinstance(send_warehouse, dict):
            send_warehouse_id = send_warehouse.get("id")
        else:
            send_warehouse_id = None

        return UserProfile(
            id=data.get("id", 0),
            phone=data.get("username", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            cashback_balance=float(data.get("cashback_balance", 0)),
            warehouse_name=warehouse_name,
            role=data.get("role", ""),
            warehouse_id=warehouse_id,
            send_warehouse_id=send_warehouse_id,
            region_id=region_id,
        )

    # ─── MAHSULOT ────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        search_after: str | None = None,
    ) -> tuple[list[Product], str | None]:
        """
        Mahsulot qidiradi.

        Returns:
            (products, next_cursor) — next_cursor keyingi sahifa uchun,
            None bo'lsa — oxirgi sahifa.
        """
        params: dict[str, Any] = {
            "query": query,
            "page_size": settings.AROS_PAGE_SIZE,
        }
        if search_after:
            params["search_after"] = search_after

        data = await self._get(
            "/product/product_variant_list/cursor-search/",
            **params,
        )

        products = parse_search_results(data)

        # Keyingi cursor ni ajratib olamiz
        next_cursor: str | None = None
        if isinstance(data, dict):
            next_url = data.get("next")
            if next_url:
                try:
                    qs = parse_qs(urlparse(next_url).query)
                    cursors = qs.get("search_after", [])
                    if cursors:
                        next_cursor = cursors[0]
                except Exception:
                    pass

        return products, next_cursor

    async def get_similar(self, product_id: str | int) -> list[Product]:
        data = await self._get(f"/product/get_similar_product_variants/{product_id}/")
        return parse_similar_products(data)

    # ─── SAVAT ───────────────────────────────────────────────────────────────

    async def get_cart(self) -> list[CartItem]:
        data = await self._get("/web/v2/cart/items/")
        logger.debug("get_cart raw response type=%s", type(data).__name__)

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("results")
                or data.get("items")
                or data.get("data")
                or data.get("cart_items")
                or []
            )
        else:
            items = []

        cart = []
        for item in items:
            variant = item.get("product_variant") or {}
            if isinstance(variant, int):
                variant_id = variant
                title = item.get("title", "Noma'lum")
                price = float(item.get("price", 0))
                image_url = None
            else:
                variant_id = variant.get("id", item.get("product_variant_id", 0))
                title = (
                    variant.get("title")
                    or variant.get("name")
                    or item.get("title", "Noma'lum")
                )
                price = float(
                    variant.get("selling_price")
                    or variant.get("price")
                    or item.get("price", 0)
                )
                images = variant.get("images") or []
                image_url = images[0].get("image") if images else None

            cart.append(CartItem(
                product_variant_id=variant_id,
                title=title,
                price=price,
                quantity=item.get("quantity", 1),
                image_url=image_url,
            ))
        return cart

    async def add_to_cart(self, variant_id: int, quantity: int = 1) -> None:
        await self._post("/web/v2/cart/items/add/", [{
            "origin": "client",
            "product_variant": variant_id,
            "quantity": quantity,
        }])

    async def remove_from_cart(self, variant_id: int) -> None:
        await self._delete(f"/web/v2/cart/items/delete/{variant_id}/")

    # ─── CHECKOUT ────────────────────────────────────────────────────────────

    async def get_payment_methods(self) -> list:
        from models import PaymentMethod
        data = await self._get("/web/v2/orders/payment_methods/")
        items = data if isinstance(data, list) else data.get("results", [])
        return [
            PaymentMethod(
                id=it.get("id", 0),
                name=it.get("name", ""),
                display_name=it.get("display_name") or it.get("name", ""),
            )
            for it in items
        ]

    async def get_order_addresses(self, region: int, delivery_method: int) -> list:
        from models import DeliveryAddress
        data = await self._get(
            "/web/v2/orders/order_page_addresses/",
            region=region,
            delivery_method=delivery_method,
        )
        items = data if isinstance(data, list) else data.get("results", [])
        return [
            DeliveryAddress(
                id=it.get("id", 0),
                name=it.get("name", ""),
                street=it.get("street", ""),
                building_number=it.get("building_number", ""),
                landmark=it.get("landmark"),
            )
            for it in items
        ]

    async def get_delivery_methods(self) -> tuple[list, list]:
        from models import DeliveryMethod
        data = await self._post("/web/v2/orders/calculate_delivery_price/", {})
        enabled_raw = data.get("enabled", []) if isinstance(data, dict) else []
        disabled_raw = data.get("disabled", []) if isinstance(data, dict) else []

        def _parse(items: list) -> list:
            return [
                DeliveryMethod(
                    id=it.get("id", 0),
                    name=it.get("name", ""),
                    is_home_delivery=it.get("is_home_delivery", False),
                    is_active=it.get("is_active", True),
                )
                for it in items
            ]

        return _parse(enabled_raw), _parse(disabled_raw)

    async def get_latest_order(self) -> dict:
        data = await self._get("/web/v2/orders/latest-order/")
        return data if isinstance(data, dict) else {}

    async def create_order(self, payload: dict) -> str:
        data = await self._post("/web/v2/orders/create-orders/", [payload])
        if isinstance(data, dict):
            return data.get("data", "")
        if isinstance(data, list) and data:
            return data[0].get("data", "") if isinstance(data[0], dict) else ""
        return ""


@asynccontextmanager
async def get_api_client(token: Optional[str] = None) -> AsyncIterator[ArosAPIClient]:
    async with ArosAPIClient(token=token) as client:
        yield client
