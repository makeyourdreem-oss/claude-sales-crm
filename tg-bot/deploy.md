# Деплой бота на VPS

## Предусловия

- VPS с Ubuntu/Debian, root или sudo
- Docker + Docker Compose
- Открытый исходящий 443 (Telegram + Gemini + Google API)

## 1. Установка Docker (если нет)

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# logout/login
```

## 2. Клонировать репо

```bash
git clone https://github.com/makeyourdreem-oss/claude-sales-crm.git
cd claude-sales-crm/tg-bot
```

## 3. Положить service account JSON

```bash
mkdir -p secrets
# Скопируй свой service-account.json сюда:
scp service-account.json user@vps:/path/to/claude-sales-crm/tg-bot/secrets/
chmod 600 secrets/service-account.json
```

## 4. Создать бота в Telegram

1. Напиши @BotFather → `/newbot`
2. Имя: что хочешь (например "My CRM")
3. Username: должен заканчиваться на `bot` (например `marat_crm_bot`)
4. Скопируй полученный token

## 5. Узнать свой Telegram user ID

Напиши @userinfobot — он пришлёт твой ID (число).

## 6. Получить Gemini API ключ

https://aistudio.google.com/app/apikey → Create API key → скопировать

## 7. Заполнить .env

```bash
cp .env.example .env
nano .env
```

Заполни:
- `TELEGRAM_BOT_TOKEN` — из шага 4
- `ALLOWED_USER_IDS` — твой ID из шага 5
- `GEMINI_API_KEY` — из шага 6
- `CRM_SHEET_ID` — ID твоей CRM таблицы
- `GOOGLE_SERVICE_ACCOUNT_PATH` — оставь `/app/secrets/service-account.json`
- `PRODUCT_DESCRIPTION`, `ICP_DESCRIPTION` — для контекста парсинга

## 8. Запустить

```bash
docker compose up -d --build
```

Проверить логи:

```bash
docker compose logs -f
```

Должно появиться:
```
[INFO] Starting bot. Allowed users: {123456789}
[INFO] Bot polling…
```

## 9. Тестировать

В Telegram найди своего бота, напиши `/start`. Должен поприветствовать.

Отправь любое голосовое или текст — должен прислать превью.

## 10. Обновление

```bash
cd claude-sales-crm
git pull
cd tg-bot
docker compose up -d --build
```

## Лимиты бота

- Аудио: до 20MB (~30 минут разговора в нормальном качестве)
- Документы: до 20MB
- Pending превью протухают через 1 час

## Логи

```bash
docker compose logs -f bot   # tail
docker compose logs --tail=200 bot   # последние 200
```

Логи также пишутся в `./logs/`.

## Stop / restart

```bash
docker compose stop
docker compose restart
docker compose down   # остановить и удалить контейнер
```

## Безопасность

- `.env` НЕ коммитить (в .gitignore)
- `secrets/` НЕ коммитить (в .gitignore)
- Если бот скомпрометирован: @BotFather → revoke token + замени в .env + restart

## Troubleshooting

**Бот не отвечает на /start**:
- Проверь `docker compose logs` — есть ли ошибки
- Проверь что TELEGRAM_BOT_TOKEN корректный
- Проверь что VPS имеет интернет (`curl https://api.telegram.org`)

**"Не получилось обработать" на голосовое**:
- Логи покажут ошибку Gemini (квота / неверный ключ / 5xx)
- Проверь Gemini ключ через `curl`

**"Ошибка записи в Sheets"**:
- Проверь что service account email добавлен в Share таблицы как Editor
- Проверь что листы есть (Лиды/Сделки/Беклог)
- Проверь что путь к JSON в .env корректный
