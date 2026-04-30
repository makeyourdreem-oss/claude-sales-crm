"""
Синхронизация Telegram-переписок → саммари → CRM (Google Sheets).

Usage:
    python sync_telegram.py --contact "Имя"
    python sync_telegram.py --all
    python sync_telegram.py --since 2026-04-15 --dry-run

Требует .env с:
    TG_API_ID, TG_API_HASH, TG_SESSION
    GOOGLE_SERVICE_ACCOUNT_PATH
    CRM_SHEET_ID
И contacts.json в текущей папке.

Саммари этот скрипт НЕ генерит — выгружает raw сообщения в JSON, который
LLM в основной сессии читает и саммаризирует. Результат пишется в CRM
отдельным шагом через update_crm.py (или напрямую через MCP).
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from telethon.tl.types import Message
except ImportError as e:
    print(f'ERROR: pip install telethon python-dotenv ({e})', file=sys.stderr)
    sys.exit(1)


def load_contacts(filter_name: str | None) -> list[dict]:
    path = Path('contacts.json')
    if not path.exists():
        print('ERROR: contacts.json not found in cwd', file=sys.stderr)
        sys.exit(1)
    data = json.loads(path.read_text(encoding='utf-8'))
    contacts = data.get('contacts', [])
    if filter_name:
        contacts = [c for c in contacts if filter_name.lower() in c.get('name', '').lower()]
    return contacts


def load_last_sync(name: str) -> datetime | None:
    path = Path('.last_sync.json')
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    iso = data.get(name)
    return datetime.fromisoformat(iso) if iso else None


def save_last_sync(name: str, dt: datetime):
    path = Path('.last_sync.json')
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    data[name] = dt.isoformat()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


async def fetch_messages(client: TelegramClient, contact: dict, since: datetime) -> list[dict]:
    identifier = contact.get('telegram') or contact.get('phone')
    if not identifier:
        return []
    try:
        entity = await client.get_entity(identifier)
    except Exception as e:
        print(f'  ! cannot resolve {identifier}: {e}', file=sys.stderr)
        return []

    out = []
    async for msg in client.iter_messages(entity, limit=500):
        if not isinstance(msg, Message) or not msg.text:
            continue
        msg_date = msg.date.replace(tzinfo=timezone.utc)
        if msg_date < since:
            break
        out.append({
            'date': msg_date.isoformat(),
            'from_me': msg.out,
            'text': msg.text,
        })
    out.reverse()  # chronological
    return out


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--contact')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--since')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--output', default='./sync_output.json')
    args = ap.parse_args()

    if not args.all and not args.contact:
        ap.error('--all or --contact required')

    load_dotenv()
    api_id = os.getenv('TG_API_ID')
    api_hash = os.getenv('TG_API_HASH')
    session = os.getenv('TG_SESSION')
    if not all([api_id, api_hash, session]):
        print('ERROR: TG_API_ID, TG_API_HASH, TG_SESSION required in .env', file=sys.stderr)
        sys.exit(1)

    contacts = load_contacts(args.contact if not args.all else None)
    print(f'Syncing {len(contacts)} contact(s)')

    results = {}
    async with TelegramClient(StringSession(session), int(api_id), api_hash) as client:
        for contact in contacts:
            name = contact['name']
            since = (
                datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
                if args.since
                else (load_last_sync(name) or datetime.now(timezone.utc) - timedelta(days=14))
            )
            print(f'  → {name} since {since.date()}')
            messages = await fetch_messages(client, contact, since)
            print(f'    {len(messages)} new messages')
            results[name] = {
                'contact': contact,
                'since': since.isoformat(),
                'messages': messages,
            }
            if not args.dry_run and messages:
                save_last_sync(name, datetime.now(timezone.utc))

    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nDumped to {args.output}')
    print('\nNext: feed this file to Claude — it will summarize and append to CRM "История взаимодействия".')


if __name__ == '__main__':
    asyncio.run(main())
