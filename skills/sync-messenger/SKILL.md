---
name: sync-messenger
description: Синхронизировать переписки из Telegram в CRM — для одного контакта или всех приоритетных. Тянет сообщения с прошлой синхронизации, делает саммари, дописывает в "Историю взаимодействия" соответствующей строки. Read-only по мессенджеру — никогда не пишет от твоего имени.
---

# Sync Messenger → CRM

Тянет переписки → саммари → CRM.

## Команды

```
/sync-messenger <имя или фрагмент>     # один контакт
/sync-messenger --all                  # все из contacts.json
/sync-messenger --since 2026-04-15     # за период
/sync-messenger --dry-run              # показать но не записывать
```

## Поддерживаемые мессенджеры

- ✅ **Telegram** через Telethon (api_id + hash + session string)
- ⏳ **WhatsApp** — в roadmap (через whatsapp-web.js или Evolution API)
- ⏳ **Slack** — в roadmap (через bot user OAuth)
- ⏳ **Discord** — в roadmap

Сейчас работает только Telegram.

## Pipeline

1. **Загрузить контакты** из `contacts.json` (или один по фильтру `<имя>`)
2. **Подключиться к Telegram** через Telethon
3. **Тянуть сообщения** с момента last_sync (или 14 дней при первом запуске)
4. **Саммари каждой беседы**:
   - Кто что сказал ключевого (обещания, цифры, даты)
   - Action items (кто должен сделать что)
   - Изменился ли статус сделки
5. **Обновить CRM**:
   - Append в "История взаимодействия": `[DD.MM.YYYY мессенджер]: <саммари>`
   - Если есть action item для пользователя — обновить "Следующее действие"
6. **Сохранить last_sync** в `.last_sync.json` для каждого контакта

## Конфиг

`contacts.json`:
```json
{
  "contacts": [
    {
      "name": "Имя контакта",
      "telegram": "@username_or_phone",
      "phone": "+...",
      "crm_company": "Название компании в CRM",
      "crm_sheet": "Сделки",
      "priority": 1,
      "notes": "контекст"
    }
  ]
}
```

`.env`:
```env
TG_API_ID=...
TG_API_HASH=...
TG_SESSION=<session_string>
GOOGLE_SERVICE_ACCOUNT_PATH=...
CRM_SHEET_ID=...
```

## Первый запуск

```bash
python scripts/auth_telegram.py
```

Запросит api_id и api_hash → попросит код из Telegram → выведет session string → положить в .env как TG_SESSION.

Получить api_id/hash: https://my.telegram.org → API development tools.

## Скрипт

`scripts/sync_telegram.py`:

```bash
python scripts/sync_telegram.py --contact "Имя"
python scripts/sync_telegram.py --all
python scripts/sync_telegram.py --since 2026-04-15 --dry-run
```

## Принципы безопасности

1. **Read-only** — никогда не отправляет сообщения от твоего имени
2. **Никогда не перезаписывает** CRM — только append
3. **При неоднозначности** маппинга компании — спрашивает
4. **Session string** — хранится только локально, никогда не коммитится

## Когда автоматизировать

После первого ручного теста и валидации качества саммари — можно повесить в `/schedule`:

```
schedule create:
  cron: "0 5 * * 1-5"        # пн-пт 08:00 МСК (за час до утреннего дайджеста)
  command: /sync-messenger --all
```

Тогда `/daily-digest` уже видит свежие переписки.

## Связанные скиллы

- `/daily-digest` — потребляет результаты sync-а
- `/add-to-crm` — для новых лидов из переписок (если в чате упомянули незнакомую компанию)
