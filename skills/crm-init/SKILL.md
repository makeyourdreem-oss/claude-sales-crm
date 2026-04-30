---
name: crm-init
description: Интерактивный мастер настройки CRM — задаёт вопросы про продукт/ICP/мессенджеры/стиль, создаёт Google Sheets под пользователя и формирует .env с настройками. Запускается один раз при первом использовании toolkit.
---

# CRM Init — мастер первого запуска

Запускай **один раз** при первой установке toolkit.

## Что спрашивает

1. **Продукт/услуга** — что продаёшь? (свободный текст 1-2 предложения)
2. **ICP** — кто идеальный клиент? (отрасль, размер, должность ЛПР)
3. **Средний чек** — порядок (для ICP-скоринга)
4. **CRM backend**:
   - (Recommended) Google Sheets — нужен Service Account JSON
   - Notion — нужен API token
   - Local CSV — без облака
5. **Мессенджеры** — какие синхронизировать? (Telegram сейчас; WhatsApp/Slack в roadmap)
6. **Стиль сообщений**:
   - Прямой, без воды
   - Тёплый, с small talk
   - Корпоративный, формальный
7. **Каскад веб-поиска** — какие API доступны? (Exa, Apify, Serper, Brave, Tavily — выбрать что есть)

## Что создаёт

### `.env` в корне CLAUDE_DIR/skills/.shared/

```env
# Personal context
PRODUCT_DESCRIPTION="..."
ICP_DESCRIPTION="..."
AVERAGE_DEAL_SIZE="..."
MESSAGE_STYLE="direct"  # direct|warm|formal

# CRM backend
CRM_BACKEND="google_sheets"  # google_sheets|notion|csv
CRM_SHEET_ID="..."
GOOGLE_SERVICE_ACCOUNT_PATH="..."

# Messengers
TELEGRAM_ENABLED="true"
TG_API_ID="..."
TG_API_HASH="..."
TG_SESSION="..."

# Web search cascade (priority order)
WEB_SEARCH_CASCADE="exa,apify,websearch"
```

### Google Sheets (если выбран этот backend)

Создаёт таблицу с вкладками:
- **Лиды** — холодные, в проработке
- **Сделки** — активные, после первого контакта
- **Клиенты** — закрытые сделки, для апсейла
- **Партнёры** — рекомендатели, лидоген
- **Конкуренты** — рынок и позиционирование
- **Беклог** — задачи и идеи
- **Контакты** — люди (отдельно от компаний)

Колонки CRM-вкладок (Лиды/Сделки/Клиенты):
| # | Колонка |
|---|---|
| 1 | Название компании |
| 2 | Этап воронки |
| 3 | Приоритет (P0-P3 / ICP-score) |
| 4 | Тип клиента |
| 5 | ФИО ЛПР |
| 6 | Должность |
| 7 | Email |
| 8 | Телефон |
| 9 | Telegram/мессенджер |
| 10 | Информация о компании |
| 11 | Потребности |
| 12 | История взаимодействия |
| 13 | Следующее действие |
| 14 | Дата следующего касания |
| 15 | Ссылки/файлы |
| 16 | Источник |
| 17 | Сумма сделки |
| 18 | Вероятность |

### `contacts.json` шаблон

Пустой шаблон с одним примером — пользователь дозаполняет руками или через `/add-to-crm`.

## Шаги мастера (для Claude)

```
ШАГ 1. Поприветствовать, объяснить что будет
ШАГ 2. Задать 7 вопросов (пользоваться AskUserQuestion для структурированных)
ШАГ 3. Если CRM_BACKEND = google_sheets:
   3a. Если SERVICE_ACCOUNT_PATH не указан — провести по созданию через console.cloud.google.com
   3b. Запросить email сервисного аккаунта, объяснить как Share таблицу
   3c. Создать новую spreadsheet через API с шаблонными вкладками
ШАГ 4. Если TELEGRAM_ENABLED = true:
   4a. Объяснить как получить api_id/hash на my.telegram.org
   4b. Запустить scripts/auth_telegram.py для получения session string
ШАГ 5. Записать .env
ШАГ 6. Записать contacts.json с примером
ШАГ 7. Запустить smoke-test: read 1 cell from sheet, list 1 dialog from TG
ШАГ 8. Поздравить, показать список доступных команд
```

## Связанные скиллы

- После онбординга — пользователь сразу может пользоваться `/add-to-crm`, `/meeting-notes`, `/daily-digest`
- `/sync-messenger` — после первой ручной валидации `contacts.json`
