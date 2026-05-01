"""In-memory state для pending confirmations.

Каждое сообщение бота с превью имеет UUID, по которому ищем структурированный payload
когда пользователь жмёт ✅ / ✏️ / ❌. После confirm/cancel — удаляем.

В роадмапе: Redis или SQLite если нужна персистентность через рестарты.
"""
import time
import uuid
from dataclasses import dataclass, field


@dataclass
class PendingItem:
    payload: dict
    user_id: int
    created_at: float = field(default_factory=time.time)
    source_text: str = ''  # для preview "Править"


_pending: dict[str, PendingItem] = {}
_TTL = 3600  # 1 час


def add(payload: dict, user_id: int, source_text: str = '') -> str:
    """Saves payload, returns short ID for callback_data."""
    cleanup()
    item_id = uuid.uuid4().hex[:12]
    _pending[item_id] = PendingItem(payload=payload, user_id=user_id, source_text=source_text)
    return item_id


def get(item_id: str) -> PendingItem | None:
    return _pending.get(item_id)


def remove(item_id: str) -> None:
    _pending.pop(item_id, None)


def cleanup() -> None:
    now = time.time()
    expired = [k for k, v in _pending.items() if now - v.created_at > _TTL]
    for k in expired:
        del _pending[k]
