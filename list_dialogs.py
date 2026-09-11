"""
Diagnostic: lists every chat, group, and channel your logged-in account
can see, with its Telethon-recognized ID. Use this to find the correct
ID/username to put in SOURCE_CHANNEL / DEST_CHANNEL when get_entity()
can't find something.

Uses the same session file as backfill_telethon.py, so run it from the
same folder -- it will NOT ask you to log in again.
"""

import asyncio
import os

from telethon import TelegramClient

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")
SESSION_NAME = "backfill_session"


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH first.")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    print("\n--- Main chat list ---")
    async for dialog in client.iter_dialogs():
        kind = "channel" if dialog.is_channel else ("group" if dialog.is_group else "user")
        username = f"@{dialog.entity.username}" if getattr(dialog.entity, "username", None) else "(no username)"
        print(f"{dialog.id:>16}  {kind:<8}  {username:<25}  {dialog.name}")

    print("\n--- Archived chat list ---")
    async for dialog in client.iter_dialogs(folder=1):
        kind = "channel" if dialog.is_channel else ("group" if dialog.is_group else "user")
        username = f"@{dialog.entity.username}" if getattr(dialog.entity, "username", None) else "(no username)"
        print(f"{dialog.id:>16}  {kind:<8}  {username:<25}  {dialog.name}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
