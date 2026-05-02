"""Обработчики входящих сообщений: voice, text, forwarded, document."""
import logging
import tempfile
from pathlib import Path

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

import state
from handlers.preview import build_keyboard, format_preview

logger = logging.getLogger(__name__)

MAX_AUDIO_MB = 20
MAX_DOC_MB = 20


def is_allowed(update: Update, allowed_ids: set[int]) -> bool:
    user = update.effective_user
    return bool(user and user.id in allowed_ids)


async def reject_unauthorized(update: Update):
    await update.message.reply_text(
        'Этот бот персональный — твой ID не в whitelist.\n'
        f'Твой ID: `{update.effective_user.id}`\n'
        'Если это твой бот — добавь ID в `.env` ALLOWED_USER_IDS.',
        parse_mode=ParseMode.MARKDOWN,
    )


async def send_preview(update: Update, payload: dict, source_text: str = ''):
    user_id = update.effective_user.id
    sent = await update.message.reply_text(
        format_preview(payload),
        parse_mode=ParseMode.MARKDOWN,
    )
    item_id = state.add(
        payload,
        user_id,
        source_text,
        chat_id=sent.chat_id,
        preview_message_id=sent.message_id,
    )
    await sent.edit_reply_markup(reply_markup=build_keyboard(item_id))


async def update_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: str, item, new_payload: dict):
    """Применяет новый payload к существующему превью (edit message)."""
    state.update_payload(item_id, new_payload)
    try:
        await context.bot.edit_message_text(
            chat_id=item.chat_id,
            message_id=item.preview_message_id,
            text=format_preview(new_payload),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=build_keyboard(item_id),
        )
        await update.message.reply_text('✏️ Правка применена. Проверь превью выше.')
    except Exception as e:
        logger.exception('edit_message failed')
        await update.message.reply_text(f'Не получилось обновить превью: {e}')


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return await reject_unauthorized(update)

    text = update.message.text or ''
    if not text.strip():
        return

    awaiting = state.find_awaiting_for_user(update.effective_user.id)
    if awaiting:
        item_id, item = awaiting
        await update.message.reply_chat_action('typing')
        gemini = context.bot_data['gemini']
        try:
            new_payload = await gemini.apply_correction_text(item.payload, text)
        except Exception as e:
            logger.exception('correction failed')
            return await update.message.reply_text(f'Не получилось применить правку: {e}')
        return await update_preview(update, context, item_id, item, new_payload)

    if update.message.forward_origin:
        sender = ''
        origin = update.message.forward_origin
        sender = getattr(origin, 'sender_user_name', '') or (
            origin.sender_user.full_name if getattr(origin, 'sender_user', None) else ''
        )
        text = f'[Пересланное сообщение от {sender}]\n\n{text}'

    await update.message.reply_chat_action('typing')
    gemini = context.bot_data['gemini']
    try:
        payload = await gemini.extract_from_text(text)
    except Exception as e:
        logger.exception('Gemini failed')
        return await update.message.reply_text(f'Не получилось обработать: {e}')

    await send_preview(update, payload, source_text=text)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return await reject_unauthorized(update)

    voice = update.message.voice or update.message.audio
    if not voice:
        return
    if voice.file_size and voice.file_size > MAX_AUDIO_MB * 1024 * 1024:
        return await update.message.reply_text(f'Файл больше {MAX_AUDIO_MB}MB — обрежь, пожалуйста.')

    await update.message.reply_chat_action('typing')
    file = await voice.get_file()

    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await file.download_to_drive(str(tmp_path))
        gemini = context.bot_data['gemini']

        awaiting = state.find_awaiting_for_user(update.effective_user.id)
        if awaiting:
            item_id, item = awaiting
            new_payload = await gemini.apply_correction_audio(item.payload, tmp_path)
            return await update_preview(update, context, item_id, item, new_payload)

        payload = await gemini.extract_from_audio(tmp_path)
    except Exception as e:
        logger.exception('Voice processing failed')
        return await update.message.reply_text(f'Не получилось распознать аудио: {e}')
    finally:
        tmp_path.unlink(missing_ok=True)

    await send_preview(update, payload)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return await reject_unauthorized(update)

    doc = update.message.document
    if not doc:
        return
    if doc.file_size and doc.file_size > MAX_DOC_MB * 1024 * 1024:
        return await update.message.reply_text(f'Файл больше {MAX_DOC_MB}MB.')

    await update.message.reply_chat_action('typing')
    file = await doc.get_file()
    suffix = Path(doc.file_name or 'file').suffix or '.bin'

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        await file.download_to_drive(str(tmp_path))
        text = _extract_text_from_doc(tmp_path)
        gemini = context.bot_data['gemini']
        payload = await gemini.extract_from_document(tmp_path, doc_text=text)
    except Exception as e:
        logger.exception('Document processing failed')
        return await update.message.reply_text(f'Не получилось обработать файл: {e}')
    finally:
        tmp_path.unlink(missing_ok=True)

    await send_preview(update, payload)


def _extract_text_from_doc(path: Path) -> str | None:
    """Локальная экстракция для DOCX/PDF — отдаём Gemini уже текст, чтобы экономить токены и время."""
    suffix = path.suffix.lower()
    try:
        if suffix == '.docx':
            from docx import Document
            doc = Document(str(path))
            return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        if suffix == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return '\n'.join(page.extract_text() or '' for page in reader.pages)
        if suffix in ('.txt', '.md'):
            return path.read_text(encoding='utf-8', errors='ignore')
    except Exception as e:
        logger.warning('Local extraction failed (%s) — fallback to Gemini upload', e)
    return None
