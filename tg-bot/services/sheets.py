"""Google Sheets через Service Account. Только append/update — никогда delete."""
import logging
from datetime import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class SheetsClient:
    def __init__(self, service_account_path: str, sheet_id: str):
        creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
        self._svc = build('sheets', 'v4', credentials=creds, cache_discovery=False)
        self._sheet_id = sheet_id

    def _read_column_b(self, sheet_name: str) -> list[tuple[int, str]]:
        result = self._svc.spreadsheets().values().get(
            spreadsheetId=self._sheet_id,
            range=f"'{sheet_name}'!B:B",
        ).execute()
        rows = result.get('values', [])
        return [(i + 1, r[0].strip()) for i, r in enumerate(rows) if r and r[0]]

    def find_company_row(self, sheet_name: str, company: str) -> int | None:
        """Ищет строку с такой компанией. Возвращает row number (1-based) или None."""
        if not company:
            return None
        target = company.strip().lower()
        for row_num, name in self._read_column_b(sheet_name):
            if target in name.lower() or name.lower() in target:
                return row_num
        return None

    def append_history(self, sheet_name: str, row_num: int, history_entry: str, next_action: str | None):
        """Дописывает в "Историю взаимодействия" + опционально обновляет "Следующее действие"."""
        history_col_idx = self._find_column_index(sheet_name, ['История взаимодействия', 'История'])
        if history_col_idx is None:
            logger.warning('No history column in sheet %s', sheet_name)
            return
        history_col = _idx_to_letter(history_col_idx)

        current = self._svc.spreadsheets().values().get(
            spreadsheetId=self._sheet_id,
            range=f"'{sheet_name}'!{history_col}{row_num}",
        ).execute().get('values', [['']])[0][0]

        date_str = datetime.now().strftime('%d.%m.%Y')
        new_entry = f'[{date_str} TG-бот]: {history_entry}'
        updated = f'{new_entry}\n\n{current}' if current else new_entry

        self._svc.spreadsheets().values().update(
            spreadsheetId=self._sheet_id,
            range=f"'{sheet_name}'!{history_col}{row_num}",
            valueInputOption='RAW',
            body={'values': [[updated]]},
        ).execute()

        if next_action:
            action_col_idx = self._find_column_index(sheet_name, ['Следующее действие'])
            if action_col_idx is not None:
                action_col = _idx_to_letter(action_col_idx)
                self._svc.spreadsheets().values().update(
                    spreadsheetId=self._sheet_id,
                    range=f"'{sheet_name}'!{action_col}{row_num}",
                    valueInputOption='RAW',
                    body={'values': [[next_action]]},
                ).execute()

    def append_new_row(self, sheet_name: str, payload: dict):
        """Создаёт новую строку. payload — dict из Gemini-extraction."""
        headers = self._get_headers(sheet_name)
        row = [''] * len(headers)

        date_str = datetime.now().strftime('%d.%m.%Y')
        history = f'[{date_str} TG-бот]: {payload.get("history_entry", "")}'

        people = payload.get('people', []) or []
        first_person = people[0] if people else {}

        mapping = {
            'Название компании': payload.get('company', ''),
            'Этап воронки': 'новый',
            'Тип клиента': payload.get('type', ''),
            'ФИО ЛПР': first_person.get('name', ''),
            'ФИО контакта': first_person.get('name', ''),
            'Должность': first_person.get('role', ''),
            'История взаимодействия': history,
            'Следующее действие': payload.get('next_action', ''),
            'Дата касания': payload.get('next_action_date', ''),
            'Источник': 'TG-бот',
        }

        contact = first_person.get('contact', '') or ''
        if '@' in contact:
            mapping['Email'] = contact
        elif contact:
            mapping['Телефон'] = contact

        for i, header in enumerate(headers):
            if header in mapping and mapping[header]:
                row[i] = mapping[header]

        self._svc.spreadsheets().values().append(
            spreadsheetId=self._sheet_id,
            range=f"'{sheet_name}'!A1",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [row]},
        ).execute()

    def _get_headers(self, sheet_name: str) -> list[str]:
        result = self._svc.spreadsheets().values().get(
            spreadsheetId=self._sheet_id,
            range=f"'{sheet_name}'!1:1",
        ).execute()
        return result.get('values', [[]])[0]

    def _find_column_index(self, sheet_name: str, candidate_names: list[str]) -> int | None:
        headers = self._get_headers(sheet_name)
        for cand in candidate_names:
            for i, h in enumerate(headers):
                if h.strip().lower() == cand.strip().lower():
                    return i
        return None


def _idx_to_letter(idx: int) -> str:
    """0 → A, 25 → Z, 26 → AA"""
    s = ''
    n = idx
    while True:
        s = chr(ord('A') + n % 26) + s
        n = n // 26 - 1
        if n < 0:
            return s
