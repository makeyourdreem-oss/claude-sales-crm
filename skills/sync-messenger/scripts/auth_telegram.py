"""
Запусти один раз для получения TG_SESSION строки.
После получения — добавь её в .env как TG_SESSION.

Получи api_id и api_hash на https://my.telegram.org → API development tools.
"""
import asyncio
import sys

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print('ERROR: pip install telethon', file=sys.stderr)
    sys.exit(1)


async def main():
    print('Получи api_id и api_hash на https://my.telegram.org')
    api_id = input('TG_API_ID: ').strip()
    api_hash = input('TG_API_HASH: ').strip()

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        await client.start()
        session_string = client.session.save()
        print()
        print('=== ТВОЯ TG_SESSION (скопируй в .env) ===')
        print(session_string)
        print('==========================================')
        print()
        me = await client.get_me()
        print(f'Авторизован как: {me.first_name} (@{me.username})')


if __name__ == '__main__':
    asyncio.run(main())
