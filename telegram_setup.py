"""Read recent private chat IDs from your own bot without printing its token."""
import tomllib
from pathlib import Path
from services import get_telegram_chats, friendly_error

if __name__ == "__main__":
    settings = tomllib.loads(Path('.streamlit/secrets.toml').read_text(encoding='utf-8-sig'))
    try:
        chats = get_telegram_chats(settings.get('TELEGRAM_BOT_TOKEN', ''))
        if not chats:
            print('Open your bot in Telegram, send /start, then run this helper again.')
        for chat_id, name in chats.items():
            print(f'{name}: chat ID {chat_id}')
    except Exception as error:
        print(friendly_error(error, service='Telegram'))
