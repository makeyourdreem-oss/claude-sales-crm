"""
Создаёт новую Google Sheets со структурой из templates/crm-template.json,
шарит на email пользователя как Editor.

Usage:
    python create-crm-sheet.py --service-account=<path> --title="My CRM" [--owner-email=user@example.com]

Outputs spreadsheet ID and URL — добавь ID в .env как CRM_SHEET_ID.
"""
import argparse
import json
import sys
from pathlib import Path

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print('ERROR: pip install google-api-python-client google-auth', file=sys.stderr)
    sys.exit(1)


SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


def load_template() -> dict:
    """Loads templates/crm-template.json from package root."""
    here = Path(__file__).resolve()
    # crm-init/scripts/ → crm-init/ → skills/ → repo root → templates/
    repo_root = here.parents[3]
    template_path = repo_root / 'templates' / 'crm-template.json'
    if not template_path.exists():
        print(f'ERROR: template not found at {template_path}', file=sys.stderr)
        sys.exit(1)
    return json.loads(template_path.read_text(encoding='utf-8'))


def create_spreadsheet(svc_sheets, title: str, sheets_spec: list[dict]) -> dict:
    body = {
        'properties': {'title': title},
        'sheets': [
            {'properties': {'title': sheet['name']}}
            for sheet in sheets_spec
        ],
    }
    return svc_sheets.spreadsheets().create(body=body, fields='spreadsheetId,spreadsheetUrl,sheets.properties').execute()


def write_headers(svc_sheets, sheet_id: str, sheets_spec: list[dict]):
    data = []
    for sheet in sheets_spec:
        data.append({
            'range': f"'{sheet['name']}'!A1",
            'values': [sheet['columns']],
        })
    svc_sheets.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={'valueInputOption': 'RAW', 'data': data},
    ).execute()


def freeze_header_rows(svc_sheets, sheet_id: str, sheet_props: list[dict]):
    requests = []
    for prop in sheet_props:
        requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': prop['sheetId'],
                    'gridProperties': {'frozenRowCount': 1},
                },
                'fields': 'gridProperties.frozenRowCount',
            }
        })
        requests.append({
            'repeatCell': {
                'range': {'sheetId': prop['sheetId'], 'startRowIndex': 0, 'endRowIndex': 1},
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.95, 'green': 0.95, 'blue': 0.95},
                    }
                },
                'fields': 'userEnteredFormat(textFormat,backgroundColor)',
            }
        })
    if requests:
        svc_sheets.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests': requests}).execute()


def share_with_email(svc_drive, sheet_id: str, email: str):
    permission = {
        'type': 'user',
        'role': 'writer',
        'emailAddress': email,
    }
    svc_drive.permissions().create(
        fileId=sheet_id,
        body=permission,
        sendNotificationEmail=False,
        fields='id',
    ).execute()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--service-account', required=True, help='Path to service account JSON')
    ap.add_argument('--title', default='Sales CRM', help='Spreadsheet title')
    ap.add_argument('--owner-email', help='Email to share spreadsheet with as Editor (your personal Google account)')
    args = ap.parse_args()

    sa_path = Path(args.service_account)
    if not sa_path.exists():
        print(f'ERROR: service account JSON not found: {sa_path}', file=sys.stderr)
        sys.exit(1)

    creds = service_account.Credentials.from_service_account_file(str(sa_path), scopes=SCOPES)
    svc_sheets = build('sheets', 'v4', credentials=creds)
    svc_drive = build('drive', 'v3', credentials=creds)

    template = load_template()
    sheets_spec = template['sheets']

    print(f'Creating spreadsheet "{args.title}" with {len(sheets_spec)} sheets...')
    result = create_spreadsheet(svc_sheets, args.title, sheets_spec)
    sheet_id = result['spreadsheetId']
    sheet_url = result['spreadsheetUrl']

    print('Writing headers...')
    write_headers(svc_sheets, sheet_id, sheets_spec)

    print('Formatting headers (bold + frozen)...')
    freeze_header_rows(svc_sheets, sheet_id, [s['properties'] for s in result['sheets']])

    if args.owner_email:
        print(f'Sharing with {args.owner_email} as Editor...')
        share_with_email(svc_drive, sheet_id, args.owner_email)

    print()
    print('=== READY ===')
    print(f'Spreadsheet ID: {sheet_id}')
    print(f'URL: {sheet_url}')
    print()
    print('Add to .env:')
    print(f'  CRM_SHEET_ID="{sheet_id}"')
    if not args.owner_email:
        sa_email = json.loads(sa_path.read_text(encoding='utf-8'))['client_email']
        print()
        print(f'⚠️ Service account is the owner. Share manually:')
        print(f'   1. Open {sheet_url}')
        print(f'   2. Click "Share"')
        print(f'   3. Add your personal email as Editor')
        print(f'   (Service account email: {sa_email})')


if __name__ == '__main__':
    main()
