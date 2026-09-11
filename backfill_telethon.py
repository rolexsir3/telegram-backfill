"""
One-time backfill: forwards ALL existing posts from SOURCE_CHANNEL to
DEST_CHANNEL, oldest-first, preserving the "Forwarded from" tag.

Why this needs a different tool than forward_bot.py:
The Bot API has no method to list a channel's past messages at all --
a bot can only ever *see* new posts as they happen (via getUpdates).
To walk through history, you need a real Telegram client session,
which means logging in as a user account (not a bot) via Telethon.

Run this ONCE to catch up on old posts. Keep forward_bot.py running
separately (as the bot) to handle new posts going forward.

Setup:
1. Get api_id and api_hash from https://my.telegram.org
   (log in with your phone number -> "API development tools").
2. pip install -r requirements_backfill.txt
3. Make sure the Telegram account you log in with is a member of
   SOURCE_CHANNEL and has posting rights in DEST_CHANNEL.
4. Run this script. On first run it'll ask for your phone number and
   the login code Telegram sends you -- after that it saves a local
   session file so you won't be asked again.
"""

import asyncio
import os

from telethon import TelegramClient
from telethon.errors import FloodWaitError

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
SOURCE_CHANNEL = os.environ.get("SOURCE_CHANNEL", "@source_channel_username")
DEST_CHANNEL = os.environ.get("DEST_CHANNEL", "@dest_channel_username")

SESSION_NAME = "backfill_session"
DELAY_BETWEEN_FORWARDS = 1.5  # seconds -- keep this gentle to avoid flood limits


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH (from my.telegram.org) first.")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()  # prompts for phone number + login code on first run only

    source = await client.get_entity(SOURCE_CHANNEL)
    dest = await client.get_entity(DEST_CHANNEL)

    count = 0
    skipped = 0
    # reverse=True walks oldest-to-newest, so the destination channel
    # ends up in the same chronological order as the source
    async for message in client.iter_messages(source, reverse=True):
        try:
            await client.forward_messages(dest, message)
            count += 1
            if count % 20 == 0:
                print(f"Forwarded {count} messages so far...")
            await asyncio.sleep(DELAY_BETWEEN_FORWARDS)
        except FloodWaitError as e:
            print(f"Rate limited by Telegram, waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            skipped += 1
            print(f"Skipped message {message.id}: {e}")

    print(f"Done. Forwarded {count} messages, skipped {skipped}.")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
