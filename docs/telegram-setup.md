# Setup Telegram (Telethon)

Telethon = библиотека для работы с **личным** Telegram-аккаунтом через MTProto API. Не путать с Telegram-ботами — у бота нет доступа к твоим личным переписками.

## Шаги (5 минут)

### 1. Получить api_id и api_hash
1. https://my.telegram.org → войти своим номером телефона
2. **API development tools**
3. Создать приложение (если ещё нет):
   - App title: что-то нейтральное, например `claude-crm-sync`
   - Short name: `claudecrm`
   - Platform: Other
4. Сохранить **App api_id** и **App api_hash**

### 2. Установить Telethon

```bash
pip install telethon python-dotenv
```

### 3. Получить session string

```bash
cd ~/.claude/skills/sync-messenger
python scripts/auth_telegram.py
```

Скрипт спросит api_id, api_hash, потом телефон, потом код из Telegram (придёт в самом ТГ).

В конце выведет длинную строку — это **session string**. Сохрани в `.env`:

```env
TG_API_ID="<api_id>"
TG_API_HASH="<api_hash>"
TG_SESSION="<длинная-строка-сессии>"
```

### 4. Проверить

```bash
python scripts/sync_telegram.py --contact "Имя из contacts.json" --dry-run
```

## Безопасность

- **Session string = доступ к твоему ТГ-аккаунту**. Утёк = доступ ко всем твоим перепискам
- Хранить только локально в `.env`. Не коммитить
- Если утёк — Telegram → Settings → Devices → терминируй сессию
- Никогда не вставляй session string в чат с LLM (включая Claude) — храни только в файле

## Что Telethon НЕ делает в этом toolkit

- ❌ Не отправляет сообщения от твоего имени (read-only)
- ❌ Не модифицирует чаты
- ❌ Не лезет в чаты, которых нет в `contacts.json`
- ✅ Только читает указанные чаты с момента last_sync

## Лимиты

Telegram API имеет flood protection. При синке 10+ контактов одновременно может выдать FloodWaitError — скрипт сам подождёт сколько надо.

## Альтернатива: Telegram-бот

Если не хочешь использовать личный аккаунт — можно создать бота через @BotFather и добавлять его в нужные чаты. Минус: бот видит только чаты куда его добавили, и не видит личные переписки 1-на-1.

В будущей версии toolkit опционально поддержим этот вариант.
