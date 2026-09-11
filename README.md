# Backfill Old Channel Posts

Forwards every existing post from one Telegram channel to another,
oldest-first, keeping the native "Forwarded from `<Channel>`" tag.

## Why this needs your account, not a bot

The Bot API has no method to list a channel's past messages — a bot can
only ever see new posts as they happen, never scroll back through history.
Reading history requires a real Telegram client session, which is what
Telethon (logging in with your own phone number) gives you.

The "Forwarded from" tag itself isn't something added in code — it's just
what Telegram shows automatically whenever a message is sent via a genuine
forward operation (as opposed to a plain copy), and that's what this script
does.

## Setup

1. **Get API credentials**: go to https://my.telegram.org, log in with
   your phone number, open "API development tools", and create an app to
   get an `api_id` and `api_hash`.
2. **Make sure your account has access**: you need to be a member of the
   source channel, and have posting rights (or admin) in the destination
   channel.
3. **Install and run:**

   ```bash
   pip install -r requirements_backfill.txt
   export TG_API_ID="12345678"
   export TG_API_HASH="your_api_hash"
   export SOURCE_CHANNEL="@source_channel_or_-100123..."
   export DEST_CHANNEL="@dest_channel_or_-100123..."
   python backfill_telethon.py
   ```

4. On first run it'll ask for your phone number and the login code
   Telegram texts you. After that it saves a local session file
   (`backfill_session.session`) so you won't be prompted again.

## Things to know

- **Order**: it walks oldest-to-newest, so the destination channel ends up
  in the same chronological order as the source.
- **Pacing**: it waits 1.5s between forwards to stay under Telegram's
  flood limits. For a channel with thousands of posts, expect this to take
  a while — that's intentional, going faster risks a temporary ban on
  forwarding.
- **Content-protected channels**: if the source channel has "Restrict
  Saving Content" enabled, Telegram blocks forwarding entirely. There's no
  workaround for this — it's a platform-level restriction.
- **Media groups (albums)**: each item in a multi-photo post gets forwarded
  individually rather than staying visually grouped. Let me know if you
  want grouping preserved — it's doable but needs some buffering logic.
- **Keep the session file private**: `backfill_session.session` is
  effectively a saved login to your Telegram account. Don't share it or
  commit it anywhere public.
- **Re-running**: this script doesn't track what it's already forwarded, so
  running it twice will duplicate everything. Run it once per backfill.
