# Telegram Bot → CRM

Личный Telegram-бот, который превращает голосовые / текст / пересланные сообщения / файлы в строки CRM.

## Что делает

1. Получает любой контент в личке
2. Через **Gemini 2.0 Flash** транскрибирует аудио, распознаёт смысл, извлекает компанию/людей/action items
3. Отправляет тебе **превью** с кнопками:
   - ✅ **Записать** — добавляет/обновляет строку в Google Sheets
   - ✏️ **Править** — переходит в режим правки. Дальше можешь голосом ИЛИ текстом дать уточнение ("это не Лиды, это Партнёры", "компания на самом деле Beta Corp", "добавь email ivan@example.com") — превью обновится прямо в чате
   - ❌ **Отмена**
4. Пишет только то, что ты подтвердил

## Архитектура

```
TG voice/text/file → @bot
    ↓
Gemini 2.0 Flash (audio + reasoning)
    ↓
Structured JSON: {type, company, people, history, action, target_sheet, operation}
    ↓
Превью в чате + InlineKeyboard
    ↓
Service Account → Google Sheets append/update
```

## Поддерживаемые типы входа

- 🎙 **Голосовые** — транскрипция Gemini + анализ
- 📝 **Текст** — "вчера созвонился с Acme, обсудили КП"
- ↪️ **Пересланные** — переслал переписку → бот парсит
- 📄 **Файлы** — PDF/DOCX/audio как documents

## Деплой на VPS

См. [deploy.md](deploy.md). Кратко:

```bash
git clone https://github.com/makeyourdreem-oss/claude-sales-crm.git
cd claude-sales-crm/tg-bot
cp .env.example .env  # заполнить токены
docker compose up -d
```

Что нужно:
- Docker + Docker Compose на VPS
- Telegram Bot Token (через @BotFather)
- Gemini API ключ (https://aistudio.google.com/app/apikey)
- Service account JSON для Google Sheets (см. ../docs/google-sheets-setup.md)
- Spreadsheet ID

## Безопасность

- **Whitelist по user_id** — бот отвечает только тебе (или указанному списку)
- **Service account** — у бота нет доступа к чужим Google аккаунтам
- **Read-only по входящим** — бот не отправляет сообщения от твоего имени
- **Append-only по CRM** — никогда не удаляет строки

## Команды бота

- `/start` — приветствие, проверка прав
- `/status` — статус сервисов (Gemini, Sheets, очередь)
- `/help` — список возможностей
- `/sheet` — ссылка на твою CRM
- `/cancel` — отменить текущий pending preview

Просто отправь любой контент — без команды.
