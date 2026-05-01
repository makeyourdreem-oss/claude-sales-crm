"""Формирование превью с InlineKeyboard."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def format_preview(payload: dict) -> str:
    """Превью извлечённой структуры в человеко-читаемом виде."""
    lines = []
    op = payload.get('operation', 'create')
    op_label = '🆕 Создать строку' if op == 'create' else '✏️ Обновить существующую'
    lines.append(f'**{op_label}** в листе **{payload.get("target_sheet", "?")}**')
    lines.append('')

    if payload.get('company'):
        lines.append(f'🏢 **Компания**: {payload["company"]}')
    if payload.get('type'):
        lines.append(f'📂 **Тип**: {payload["type"]}')

    people = payload.get('people') or []
    if people:
        lines.append('')
        lines.append('👤 **Контакты**:')
        for p in people[:3]:
            parts = [p.get('name', '?')]
            if p.get('role'):
                parts.append(f'_{p["role"]}_')
            if p.get('contact'):
                parts.append(p['contact'])
            lines.append('  • ' + ' — '.join(parts))

    if payload.get('history_entry'):
        lines.append('')
        lines.append(f'📝 **Запись в историю**:')
        lines.append(f'  _{payload["history_entry"]}_')

    if payload.get('next_action'):
        lines.append('')
        lines.append(f'➡️ **Следующее действие**: {payload["next_action"]}')
        if payload.get('next_action_date'):
            lines.append(f'   📅 До {payload["next_action_date"]}')

    confidence = payload.get('confidence')
    if confidence is not None:
        emoji = '🟢' if confidence > 0.8 else '🟡' if confidence > 0.5 else '🔴'
        lines.append(f'\n{emoji} Уверенность: {int(confidence * 100)}%')

    warnings = payload.get('warnings') or []
    if warnings:
        lines.append('\n⚠️ **Предупреждения**:')
        for w in warnings:
            lines.append(f'  • {w}')

    return '\n'.join(lines)


def build_keyboard(item_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('✅ Записать', callback_data=f'ok:{item_id}'),
            InlineKeyboardButton('✏️ Править', callback_data=f'edit:{item_id}'),
            InlineKeyboardButton('❌ Отмена', callback_data=f'cancel:{item_id}'),
        ]
    ])
