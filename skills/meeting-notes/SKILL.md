---
name: meeting-notes
description: Превратить расшифровку встречи (Yandex Konspekt, Whisper, любой текст или DOCX) в структурированный документ с тремя разделами — исходная транскрибация / саммари / выводы и action items. Сохраняет в нужную папку и опционально привязывает к строке CRM.
---

# Meeting Notes

Из сырой расшифровки → 3-секционный DOCX (или Google Doc).

## Использование

```
/meeting-notes <путь/к/расшифровке.docx>
/meeting-notes <путь/к/расшифровке.txt>
/meeting-notes "сырой текст"
/meeting-notes --link "Название компании"   # привязать к строке CRM
```

## Структура итога

Документ с тремя разделами:

### 1. Транскрибация (без изменений)
Исходный текст как есть. Без правок и сокращений. Это "источник правды" для всех последующих операций.

### 2. Саммари
- 5-10 пунктов с ключевыми моментами встречи
- Кто что сказал важного (с именами)
- Цифры, даты, обещания
- Решения принятые на встрече
- Открытые вопросы

### 3. Выводы и Action Items
- Что узнали нового про потребности клиента
- На какой стадии воронки сейчас
- Изменился ли ICP-fit или вероятность
- **Action items**: кто что должен сделать и до когда
- Следующие шаги (CTA)

## Pipeline

```
input.docx
  ↓ python-docx
plain text
  ↓ split into chunks (если очень длинный)
LLM: summary
LLM: conclusions
  ↓ python-docx generate
output.docx (3 sections)
  ↓ optional
move to ./meetings/done/
  ↓ optional --link
update CRM row "История взаимодействия"
```

## Конфиг (через .env)

```env
MEETINGS_INBOX="./meetings/inbox"
MEETINGS_DONE="./meetings/done"
MEETING_NOTES_STYLE="omnisim"   # имя стиля (см. styles/) или 'default'
AUTO_LINK_TO_CRM="false"        # пытаться сматчить компанию автоматом
```

## Стили оформления

Папка `styles/` содержит шаблоны брендирования:
- `default.json` — нейтральный, чёрный текст
- `corporate-blue.json` — синий, как у большинства B2B
- Можно добавить свой через `/crm-init` или вручную

Пример стиля:
```json
{
  "title_color": "#1A1A2E",
  "h2_color": "#16548E",
  "body_color": "#2D2D2D",
  "footer_color": "#666666",
  "title_size": 18,
  "h2_size": 13,
  "body_size": 11
}
```

## Скрипт

`scripts/process-meeting.py` — основная Python-логика:

```bash
python scripts/process-meeting.py <input> --summary <summary.txt> --conclusions <conclusions.txt> [--style default] [--output path]
```

Summary и conclusions генерирует Claude в основной сессии и передаёт как файлы. Скрипт собирает финальный DOCX.

## Кейс: Яндекс Конспект

Яндекс присылает расшифровки звонков на email — DOCX-вложение. Workflow:

1. Скачать вложение в `./meetings/inbox/`
2. `/meeting-notes ./meetings/inbox/имя-файла.docx`
3. Готовый структурированный документ оказывается в `./meetings/done/`

Опционально: настроить почтовое правило что вложения от noreply@yandex.ru → автосохраняются в inbox.

## Связанные скиллы

- `/add-to-crm` — добавить компанию упомянутую на встрече
- `/sync-messenger` — догнать что обсуждалось в чате до/после встречи
- `/daily-digest` — учесть результаты встречи в плане на завтра
