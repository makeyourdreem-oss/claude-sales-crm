# Setup Google Sheets с Service Account

Используем service account вместо OAuth — токены не протухают.

## Шаги (10 минут)

### 1. Создать проект в Google Cloud
1. https://console.cloud.google.com/
2. Создать новый проект (или использовать существующий)

### 2. Включить Google Sheets API
1. APIs & Services → Library → найти "Google Sheets API" → Enable

### 3. Создать Service Account
1. IAM & Admin → Service Accounts → Create Service Account
2. Имя любое (например `claude-crm`)
3. Skip "Grant access" — это не нужно
4. Done

### 4. Создать JSON-ключ
1. Кликнуть на созданный service account
2. Вкладка **Keys** → Add Key → Create new key → **JSON** → Create
3. Файл скачается. Сохрани в безопасное место (например `~/.config/claude-crm/service-account.json`)
4. **НЕ коммить в git!**

### 5. Открыть таблицу для service account
1. Скопировать email service account (вид: `xxx@project-name.iam.gserviceaccount.com`)
2. Открыть свою CRM Google Sheets
3. Share → вставить email → **Editor** → снять "Notify people" → Send
4. Готово, теперь скрипт видит таблицу

### 6. Прописать в .env
```env
GOOGLE_SERVICE_ACCOUNT_PATH="/absolute/path/to/service-account.json"
CRM_SHEET_ID="<id из URL таблицы>"
```

ID таблицы — это длинная строка между `/d/` и `/edit` в URL.

## Проверка

```bash
python -c "
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

creds = service_account.Credentials.from_service_account_file(
    os.environ['GOOGLE_SERVICE_ACCOUNT_PATH'],
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
svc = build('sheets', 'v4', credentials=creds)
meta = svc.spreadsheets().get(spreadsheetId=os.environ['CRM_SHEET_ID']).execute()
print('OK:', meta['properties']['title'])
"
```

Если выводит название таблицы — всё работает.

## Безопасность

- JSON-ключ = доступ к таблице. Если утёк — иди в Google Cloud Console → IAM & Admin → Service Accounts → нажми Delete на ключе и сгенери новый
- Service account имеет ровно те права, какие даны через Share. Можно дать Viewer для read-only режима
- Никогда не коммить JSON в git (наш `.gitignore` уже блокирует)
