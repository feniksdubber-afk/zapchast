"""
Fayl-asoslangan FSM Storage.

aiogram standart MemoryStorage bot qayta ishga tushganda (deploy, crash,
restart) barcha login token va savat ma'lumotlarini yo'qotadi, chunki
hammasi faqat RAM'da saqlanadi.

Bu klass BaseStorage interfeysini to'g'ridan-to'g'ri implement qiladi
(o'z ichki dict'i bilan), shuning uchun aiogram'ning MemoryStorage ichki
tuzilishiga bog'liq emas — versiyalar orasida barqaror ishlaydi.

Har bir yozish operatsiyasidan keyin holat butunlay JSON faylga
yoziladi (atomik almashtirish bilan — yarim yozilgan fayl xavfi yo'q).
Bot ishga tushganda fayldan o'qib oladi.

Eslatma: bir nechta bot nusxasi (replica) parallel ishlasa, fayl race
condition'ga uchraydi — bitta nusxa (single instance) uchun mo'ljallangan.
Ko'p nusxali deploy kerak bo'lsa, RedisStorage'ga o'tish tavsiya etiladi.
"""

import json
import logging
import os
from typing import Any, Optional

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey

logger = logging.getLogger(__name__)


def _key_to_str(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.destiny}"


def _state_to_str(state: Optional[State | str]) -> Optional[str]:
    if state is None:
        return None
    if isinstance(state, State):
        return state.state
    return str(state)


class JSONFileStorage(BaseStorage):
    def __init__(self, path: str = "fsm_storage.json") -> None:
        self._path = path
        # key_str -> {"state": str|None, "data": dict}
        self._store: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self._path):
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._store = json.load(f)
            logger.info("FSM storage fayldan yuklandi: %s (%d kalit)", self._path, len(self._store))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("FSM storage faylini o'qishda xatolik, bo'sh holatda boshlanadi: %s", e)
            self._store = {}

    def _save(self) -> None:
        """Joriy holatni diskka atomik yozadi."""
        tmp_path = self._path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._store, f, ensure_ascii=False)
            os.replace(tmp_path, self._path)  # bir vaqtda almashtirish — yarim yozilish xavfsiz
        except OSError as e:
            logger.error("FSM storage faylini yozishda xatolik: %s", e)

    async def set_state(self, key: StorageKey, state: Any = None) -> None:
        k = _key_to_str(key)
        entry = self._store.setdefault(k, {"state": None, "data": {}})
        entry["state"] = _state_to_str(state)
        self._save()

    async def get_state(self, key: StorageKey) -> Optional[str]:
        entry = self._store.get(_key_to_str(key))
        return entry["state"] if entry else None

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        k = _key_to_str(key)
        entry = self._store.setdefault(k, {"state": None, "data": {}})
        entry["data"] = data
        self._save()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        entry = self._store.get(_key_to_str(key))
        return dict(entry["data"]) if entry else {}

    async def close(self) -> None:
        self._save()
