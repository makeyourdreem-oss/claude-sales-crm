"""Обработка нажатий на кнопки превью."""
import logging

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import state

logger = logging.getLogger(__name__)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ''
    if ':' not in data:
        return

    action, item_id = data.split(':', 1)
    item = state.get(item_id)
    if not item:
        return await query.edit_message_text('⏰ Превью протухло (>1 часа). Отправь заново.')

    if item.user_id != query.from_user.id:
        return await query.answer('Не твой запрос.', show_alert=True)

    if action == 'cancel':
        state.remove(item_id)
        return await query.edit_message_text('❌ Отменено')

    if action == 'edit':
        item.awaiting_correction = True
        item.chat_id = query.message.chat_id
        item.preview_message_id = query.message.message_id
        return await query.edit_message_text(
            '✏️ Жду правку — голосом или текстом.\n\n'
            'Например: _"это не Лиды, это Партнёры"_, '
            '_"компания на самом деле Beta Corp"_, '
            '_"добавь email ivan@example.com"_.\n\n'
            'Или /cancel если передумал.',
            parse_mode=ParseMode.MARKDOWN,
        )

    if action == 'ok':
        sheets = context.bot_data['sheets']
        payload = item.payload
        try:
            target_sheet = payload.get('target_sheet') or 'Беклог'
            company = payload.get('company') or ''
            history = payload.get('history_entry') or ''
            next_action = payload.get('next_action')

            if payload.get('operation') == 'update' and company:
                row_num = sheets.find_company_row(target_sheet, company)
                if row_num:
                    sheets.append_history(target_sheet, row_num, history, next_action)
                    state.remove(item_id)
                    return await query.edit_message_text(
                        f'✅ Дописано в "{target_sheet}" → {company} (строка {row_num})',
                        parse_mode=ParseMode.MARKDOWN,
                    )

            sheets.append_new_row(target_sheet, payload)
            state.remove(item_id)
            await query.edit_message_text(
                f'✅ Добавлено в "{target_sheet}": **{company or "(без компании)"}**',
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            logger.exception('Sheets write failed')
            await query.edit_message_text(f'⚠️ Ошибка записи в Sheets: {e}')
