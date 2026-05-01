---
name: crm-init
description: Интерактивный мастер первого запуска toolkit. Задаёт вопросы про продукт/ICP/мессенджеры/стиль, создаёт Google Sheets с шаблонной структурой через service account, пишет .env с настройками. Запускается ОДИН РАЗ при установке.
---

# CRM Init — мастер первого запуска

**Запускай один раз** при установке toolkit. Если уже запускал — настройки в `.env` и таблица уже есть, не повторяй.

## Алгоритм для Claude (строго по шагам)

### Шаг 0 — Проверить что не запускался

Если `~/.claude/skills/.shared/.env` существует — спросить пользователя: "Уже настроено. Перенастроить?". Если нет — продолжить.

### Шаг 1 — Поприветствовать и объяснить

Сказать что будет 7 вопросов и потом создание таблицы. Займёт ~5 минут.

### Шаг 2 — Задать вопросы через AskUserQuestion

```
Вопрос 1 (header: "Продукт"): Что продаёшь? — свободный текст
Вопрос 2 (header: "ICP"): Кто идеальный клиент? — свободный текст
Вопрос 3 (header: "Чек"): Средний размер сделки? — варианты:
   - до 100к ₽ (B2C / SMB)
   - 100к-1М ₽ (SMB / средний B2B)
   - 1-10М ₽ (mid-market / enterprise)
   - 10М+ ₽ (enterprise / госконтракты)
Вопрос 4 (header: "CRM"): Где хранить CRM? — варианты:
   - Google Sheets (Recommended)
   - Notion (roadmap, пока не реализовано)
   - Local CSV (без облака)
Вопрос 5 (header: "Мессенджеры"): Какие мессенджеры синхронизировать? (multiSelect)
   - Telegram
   - WhatsApp (roadmap)
   - Slack (roadmap)
   - Никакие (только ручной ввод)
Вопрос 6 (header: "Стиль"): Стиль сообщений?
   - Прямой, без воды (Recommended для большинства B2B)
   - Тёплый, с small talk
   - Корпоративный, формальный
Вопрос 7 (header: "Поиск"): Какие API веб-поиска уже есть? (multiSelect)
   - Exa
   - Apify
   - Serper
   - Tavily
   - Brave Search
   - Только встроенный WebSearch
```

### Шаг 3 — Если выбран Google Sheets

3a. Спросить: "Есть ли уже service account JSON?"
   - Да → попросить путь к JSON
   - Нет → провести по шагам:
     1. https://console.cloud.google.com/ → новый проект
     2. APIs & Services → Library → Google Sheets API → Enable
     3. IAM & Admin → Service Accounts → Create
     4. Кликнуть на email → Keys → Add Key → JSON → скачать
     5. Спросить путь к скачанному файлу

3b. Прочитать `client_email` из JSON через Python:
```python
import json
with open(path) as f:
    sa = json.load(f)
print(sa['client_email'])
```
Показать пользователю и спросить: "Создавать новую таблицу или подключить существующую?"

3c-A. **Новая таблица**: запустить `python scripts/create-crm-sheet.py --service-account=<path> --title="<имя>"` — он создаёт таблицу со всеми листами по `templates/crm-template.json`, делает service account её владельцем, выводит ID и URL.

3c-B. **Существующая**: попросить ID таблицы (из URL). Объяснить что нужно открыть Share → добавить email service account как Editor → снять "Notify people".

### Шаг 4 — Если выбран Telegram

4a. Спросить: "Есть ли api_id и api_hash с https://my.telegram.org?"
   - Нет → провести: открыть my.telegram.org → API development tools → создать app → скопировать api_id и api_hash

4b. Запустить `python scripts/auth_telegram.py` (из `skills/sync-messenger/scripts/`) — пользователь вводит api_id, hash, потом код из ТГ → получает session string.

### Шаг 5 — Записать `.env`

Создать `~/.claude/skills/.shared/.env` с:
```env
PRODUCT_DESCRIPTION="..."
ICP_DESCRIPTION="..."
AVERAGE_DEAL_SIZE="..."
MESSAGE_STYLE="direct|warm|formal"

CRM_BACKEND="google_sheets"
CRM_SHEET_ID="..."
GOOGLE_SERVICE_ACCOUNT_PATH="..."

TELEGRAM_ENABLED="true|false"
TG_API_ID="..."
TG_API_HASH="..."
TG_SESSION="..."

WEB_SEARCH_CASCADE="exa,apify,websearch"  # только те что выбрал юзер

DIGEST_TIMEZONE="Europe/Moscow"
DIGEST_RED_ZONE_DAYS=14
```

### Шаг 6 — Создать `contacts.json` шаблон

Скопировать `skills/sync-messenger/contacts.example.json` → `~/.claude/skills/.shared/contacts.json`.

### Шаг 7 — Smoke test

```python
# Проверить что Google Sheets работает
python -c "
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
creds = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_SERVICE_ACCOUNT_PATH'],
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
svc = build('sheets', 'v4', credentials=creds)
meta = svc.spreadsheets().get(spreadsheetId=os.environ['CRM_SHEET_ID']).execute()
print('OK:', meta['properties']['title'], '— листов:', len(meta['sheets']))
"
```

Если ОК — поздравить и показать список доступных команд:

```
✅ Готово!

Доступные команды:
  /add-to-crm <input>   — добавить компанию/лида в CRM
  /meeting-notes <file> — обработать расшифровку встречи
  /sync-messenger Имя   — синк переписки в CRM
  /sync-messenger --all — синк всех приоритетных
  /daily-digest         — утренний дайджест

Дальше: открой contacts.json и добавь приоритетные ТГ-контакты.
```

## Чего НЕ делает crm-init

- Не вешает расписание — это делает пользователь сам через `/schedule`
- Не импортирует данные из старого CRM — миграция отдельной командой `/import-crm`
- Не настраивает Telegram-бота для приёма входящих — это `/setup-bot`
- Не лезет в OAuth — только service account

## Файлы создаваемые скиллом

- `~/.claude/skills/.shared/.env` — переменные окружения
- `~/.claude/skills/.shared/contacts.json` — шаблон
- (если new sheet) — Google Sheets с 7 листами по шаблону

## Если что-то пошло не так

- "invalid_grant" → service account JSON неверный или таблица не пошарена
- "Permission denied" в Google Sheets → email service account не в Share
- "Telethon AuthKeyError" → session string не сохранён или протух

Скилл должен ловить эти ошибки и предлагать конкретное исправление, не выходить молча.
