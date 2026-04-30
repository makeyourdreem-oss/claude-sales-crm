# Архитектура

## Принципы

1. **Skills как первый класс** — основная логика в SKILL.md, а не в Python. Python только для I/O (API, файлы).
2. **Service account вместо OAuth** — токены не протухают, не отвлекают.
3. **Никаких конфиденциальных данных в репо** — `.gitignore` блокирует JSON, .env, session.
4. **Каскад веб-поиска** — fallback цепочка вместо одного hardcoded API.
5. **Read-only по мессенджерам** — никогда не отправляем сообщения от имени пользователя.
6. **Append-only по CRM** — никогда не перезаписываем существующие данные, только дополняем.

## Слои

```
┌────────────────────────────────────────────────────────────┐
│  USER                                                      │
│  /add-to-crm   /sync-messenger   /meeting-notes  /digest   │
└────────────┬───────────────────────────────────────────────┘
             │
┌────────────▼───────────────────────────────────────────────┐
│  CLAUDE CODE — Skill Orchestration                         │
│  (читает SKILL.md, вызывает Python-скрипты, пишет в Sheets)│
└────────────┬───────────────────────────────────────────────┘
             │
   ┌─────────┼──────────┬──────────────┬──────────────┐
   ▼         ▼          ▼              ▼              ▼
┌─────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐
│ TG  │ │ Email/  │ │ Web      │ │ DOCX/PDF   │ │  Google  │
│Tele-│ │ inbox   │ │ search   │ │ readers    │ │  Sheets  │
│thon │ │         │ │ cascade  │ │            │ │  (SA)    │
└─────┘ └─────────┘ └──────────┘ └────────────┘ └──────────┘
```

## Web Search Cascade

Заданный в `WEB_SEARCH_CASCADE` порядок:

```
exa → apify → serper → brave → websearch
```

Триггер переключения:
- 402 / "credits limit"
- Пустой результат
- 5xx / timeout

Логика реализуется в скилле `/add-to-crm` (а не в Python — потому что Claude как orchestrator решает когда переключиться).

## CRM-операции

Всегда через service account JSON. Никогда через OAuth user flow.

Разрешённые операции:
- `read` — чтение всех листов
- `append` — добавление новых строк
- `update_cell` — обновление одной ячейки (для статусов)
- `find` — поиск дубликатов перед записью

Запрещённые операции (НИКОГДА не делать):
- `delete_sheet`
- `clear_sheet`
- `delete_rows` (диапазон)
- `replace_all`

Это hardcoded правило в каждом SKILL.md и в memory пользователя.

## Идемпотентность синка

`sync-messenger` хранит `.last_sync.json` — словарь `{contact_name: iso_datetime}`. При следующем запуске тянет только новое.

Если хочешь пересинхронизировать с нуля — удали `.last_sync.json` или используй `--since YYYY-MM-DD`.

## Расширение

Чтобы добавить новый коннектор (WhatsApp, Slack, Discord):

1. Создать `skills/sync-<name>/SKILL.md`
2. Реализовать `scripts/sync_<name>.py` с тем же интерфейсом что у sync_telegram.py:
   - вход: `contacts.json` + `--since` + `--all` или `--contact`
   - выход: `sync_output.json` с одинаковой структурой
3. Saamari + запись в CRM реиспользуют общий код через скилл `/add-to-crm`

## Что хранится локально и что — в облаке

| Что | Где |
|---|---|
| CRM-данные | Google Sheets (облако) |
| Service account JSON | Локально (`.env`) |
| Telegram session string | Локально (`.env`) |
| `.last_sync.json` | Локально (рядом со скиллом) |
| Расшифровки встреч | Локально (`./meetings/`) |
| `contacts.json` | Локально (рядом со скиллом) |
| Скиллы (SKILL.md) | Локально (`~/.claude/skills/`) или в репо |
