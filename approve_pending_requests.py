"""
One-time sweep: approves ALL currently pending join requests for a
channel/group, looping until Telegram reports none are left.

Telegram's bulk-approve call only clears roughly 100 requests per
call, so this repeats it until the API returns "nothing left pending".
For a backlog of a few thousand, expect this to take a few minutes.

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
4. Set CHANNEL and run. Safe to re-run -- it just picks up whatever
   is still pending.
"""

import asyncio
import os

from telethon import TelegramClient, functions, types
from telethon.errors import FloodWaitError
from telethon.errors.rpcerrorlist import HideRequesterMissingError

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

# Pause between bulk-approve rounds. Keep this gentle -- approving
# thousands of members quickly is exactly the pattern Telegram's
# anti-spam watches for.
DELAY_BETWEEN_ROUNDS = 3


def log(msg):
    print(msg, flush=True)


async def has_pending(client, chat):
    """Authoritative check: is there at least one join request still
    pending? Used to confirm we're actually done, rather than trusting
    HideRequesterMissingError alone (see note in main loop)."""
    res = await client(functions.messages.GetChatInviteImportersRequest(
        peer=chat,
        link=None,
        q="",
        offset_date=0,
        offset_user=types.InputUserEmpty(),
        limit=1,
        requested=True,
    ))
    return bool(res.importers)


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
    log("Each round clears up to ~100. This loops until a fresh check confirms none left.")

    total_rounds = 0
    timeouts = 0
    MAX_ROUNDS = 5000  # safety cap only
    finished = False

    while total_rounds < MAX_ROUNDS:
        try:
            await client(functions.messages.HideAllChatJoinRequestsRequest(
                peer=chat,
                approved=True,
            ))
            total_rounds += 1
            timeouts = 0
            log(f"Round {total_rounds} cleared (~{total_rounds * 100} approved so far)...")
        except HideRequesterMissingError:
            # This fires both when the backlog is genuinely empty AND
            # when a client-side timeout caused Telethon to silently
            # retry a request that had already succeeded. Either way,
            # don't trust it alone -- the explicit check below decides.
            pass
        except FloodWaitError as e:
            log(f"Rate limited, waiting {e.seconds}s before continuing...")
            await asyncio.sleep(e.seconds)
            continue
        except (TimeoutError, asyncio.TimeoutError):
            timeouts += 1
            if timeouts > 10:
                log("Too many consecutive timeouts from Telegram -- stopping. Re-run later to continue.")
                break
            log(f"Telegram timed out (attempt {timeouts}/10), retrying in 10s...")
            await asyncio.sleep(10)
            continue
        except Exception as e:
            log(f"Unexpected error after {total_rounds} rounds: {e}")
            log("Re-run the script to continue where this left off.")
            break

        await asyncio.sleep(DELAY_BETWEEN_ROUNDS)
        try:
            still_pending = await has_pending(client, chat)
        except Exception as e:
            log(f"Could not verify remaining count ({e}) -- assuming more may be pending, retrying...")
            still_pending = True

        if not still_pending:
            finished = True
            break

    if finished:
        log(f"Done after {total_rounds} rounds. All pending join requests approved.")
    elif total_rounds >= MAX_ROUNDS:
        log(f"Stopped at the {MAX_ROUNDS}-round safety cap. Re-run to continue.")
    else:
        log(f"Stopped early after {total_rounds} rounds -- re-run to approve the rest.")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
