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
    awaiting_correction: bool = False
    chat_id: int | None = None
    preview_message_id: int | None = None


_pending: dict[str, PendingItem] = {}
_TTL = 3600  # 1 час


def add(payload: dict, user_id: int, source_text: str = '', chat_id: int | None = None, preview_message_id: int | None = None) -> str:
    """Saves payload, returns short ID for callback_data."""
    cleanup()
    item_id = uuid.uuid4().hex[:12]
    _pending[item_id] = PendingItem(
        payload=payload,
        user_id=user_id,
        source_text=source_text,
        chat_id=chat_id,
        preview_message_id=preview_message_id,
    )
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


def find_awaiting_for_user(user_id: int) -> tuple[str, PendingItem] | None:
    """Возвращает самый свежий awaiting_correction item для пользователя."""
    cleanup()
    candidates = [
        (item_id, item) for item_id, item in _pending.items()
        if item.user_id == user_id and item.awaiting_correction
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x[1].created_at)


def update_payload(item_id: str, new_payload: dict) -> None:
    item = _pending.get(item_id)
    if item:
        item.payload = new_payload
        item.awaiting_correction = False
