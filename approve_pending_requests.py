"""
One-time sweep: approves ALL currently pending join requests for a
channel/group in a single call.

Why this needs your personal account (like backfill_telethon.py) and
not the bot:
The official Bot API only tells a bot about join requests as they
happen live (via updates) -- there's no Bot API method to list or
bulk-approve a backlog that already existed before the bot started
watching. Clearing an existing backlog requires a raw client API call
that real admin accounts can make directly.

Setup:
1. Same api_id / api_hash as backfill_telethon.py (from
   https://my.telegram.org). If you already have backfill_session.session
   from that script, this reuses it -- no need to log in again.
2. pip install -r requirements_backfill.txt (same telethon dependency)
3. Make sure this account is an admin of the chat with rights to
   manage join requests.
4. Set CHANNEL and run once. Use join_request_bot.py (the bot)
   afterward for anything new going forward.
"""

import asyncio
import os

from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError

API_ID = int(os.environ.get("TG_API_ID", "0"))
API_HASH = os.environ.get("TG_API_HASH", "")


def _resolve_channel(value):
    """Numeric strings (IDs) must become int, or Telethon treats them
    as a username/phone lookup instead of a raw peer ID."""
    try:
        return int(value)
    except ValueError:
        return value


CHANNEL = _resolve_channel(os.environ.get("CHANNEL", "@your_channel_username"))

# Reuses the same session file as backfill_telethon.py if present --
# no separate login needed if you already ran that script.
SESSION_NAME = "backfill_session"


def log(msg):
    print(msg, flush=True)


async def main():
    if not API_ID or not API_HASH:
        raise SystemExit("Set TG_API_ID and TG_API_HASH first.")

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()

    log("Fetching your dialog list so the channel can be resolved...")
    await client.get_dialogs()

    try:
        chat = await client.get_entity(CHANNEL)
    except ValueError:
        raise SystemExit(
            f"Could not find {CHANNEL} among your dialogs. Make sure this "
            "account is an admin of it, and the ID/username is correct."
        )

    log(f"Approving all pending join requests for {CHANNEL}...")
    total_rounds = 0
    MAX_ROUNDS = 1000  # safety cap -- 1000 rounds x ~100/round is far more than any real backlog
    while total_rounds < MAX_ROUNDS:
        total_rounds += 1
        try:
            await client(functions.messages.HideAllChatJoinRequestsRequest(
                peer=chat,
                approved=True,
            ))
        except FloodWaitError as e:
            log(f"Rate limited, waiting {e.seconds}s...")
            await asyncio.sleep(e.seconds)
            continue
        except Exception as e:
            log(f"Failed: {e}")
            break

        # hideAllChatJoinRequests only clears up to 100 per call, so
        # check whether any are still pending and loop until none are.
        await asyncio.sleep(1)
        remaining = await client(functions.messages.GetChatInviteImportersRequest(
            peer=chat,
            link=None,
            q="",
            offset_date=0,
            offset_user=types.InputUserEmpty(),
            limit=1,
            requested=True,
        ))
        log(f"Round {total_rounds}: cleared a batch, {len(remaining.importers)} still pending check...")
        if not remaining.importers:
            break

    if total_rounds >= MAX_ROUNDS:
        log(f"Stopped after {MAX_ROUNDS} rounds as a safety limit -- there may still be requests pending. Re-run the script to continue.")
    else:
        log("Done. No pending join requests remain.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
