"""Точка входа Telegram-бота."""
import logging
from pathlib import Path

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from handlers.callbacks import handle_callback
from handlers.messages import handle_document, handle_text, handle_voice, is_allowed
from services.gemini import GeminiClient
from services.sheets import SheetsClient


def setup_logging(level: str):
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    )
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return await update.message.reply_text(
            f'Бот персональный. Твой ID: `{update.effective_user.id}`',
            parse_mode=ParseMode.MARKDOWN,
        )
    await update.message.reply_text(
        'Привет! Шли мне:\n'
        '🎙 голосовые\n'
        '📝 текст\n'
        '↪️ пересланные сообщения\n'
        '📄 файлы (PDF/DOCX)\n\n'
        'Я разберу через Gemini, покажу превью — ты подтвердишь — я запишу в твою CRM.\n\n'
        '/sheet — ссылка на CRM\n'
        '/status — состояние сервисов'
    )


async def cmd_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return
    sheet_id = context.bot_data['sheet_id']
    await update.message.reply_text(f'https://docs.google.com/spreadsheets/d/{sheet_id}/edit')


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update, context.bot_data['allowed_ids']):
        return
    import state as st
    await update.message.reply_text(f'Бот работает.\nPending превью: {len(st._pending)}')


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand('start', 'Начать'),
        BotCommand('sheet', 'Ссылка на CRM'),
        BotCommand('status', 'Состояние'),
        BotCommand('help', 'Помощь'),
    ])
    Path('/app/data').mkdir(parents=True, exist_ok=True)
    Path('/app/data/healthy').touch()


def main():
    cfg = config.load()
    setup_logging(cfg.log_level)
    log = logging.getLogger(__name__)
    log.info('Starting bot. Allowed users: %s', cfg.allowed_user_ids)

    gemini = GeminiClient(
        api_key=cfg.gemini_api_key,
        model_name=cfg.gemini_model,
        product=cfg.product_description,
        icp=cfg.icp_description,
    )
    sheets = SheetsClient(
        service_account_path=cfg.service_account_path,
        sheet_id=cfg.sheet_id,
    )

    app = ApplicationBuilder().token(cfg.telegram_token).post_init(post_init).build()
    app.bot_data['gemini'] = gemini
    app.bot_data['sheets'] = sheets
    app.bot_data['sheet_id'] = cfg.sheet_id
    app.bot_data['allowed_ids'] = cfg.allowed_user_ids

    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(CommandHandler('sheet', cmd_sheet))
    app.add_handler(CommandHandler('status', cmd_status))

    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.add_handler(CallbackQueryHandler(handle_callback))

    log.info('Bot polling…')
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
