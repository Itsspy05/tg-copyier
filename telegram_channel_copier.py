
from telethon.sync import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio
import os
import json
import sys

# --- Custom HTML entity converter for Telegram messages ---
import html
def get_message_text_with_entities(text, entities, fmt):
    if not entities:
        return html.escape(text or "")
    result = ""
    last_offset = 0
    for ent in sorted(entities, key=lambda e: e.offset):
        # Add text before entity
        result += html.escape(text[last_offset:ent.offset])
        ent_text = html.escape(text[ent.offset:ent.offset+ent.length])
        if ent.__class__.__name__ == 'MessageEntityBold':
            result += f"<b>{ent_text}</b>"
        elif ent.__class__.__name__ == 'MessageEntityItalic':
            result += f"<i>{ent_text}</i>"
        elif ent.__class__.__name__ == 'MessageEntityCode':
            result += f"<code>{ent_text}</code>"
        elif ent.__class__.__name__ == 'MessageEntityPre':
            result += f"<pre>{ent_text}</pre>"
        elif ent.__class__.__name__ == 'MessageEntityTextUrl':
            result += f'<a href="{html.escape(ent.url)}">{ent_text}</a>'
        elif ent.__class__.__name__ == 'MessageEntityUrl':
            result += f'<a href="{ent_text}">{ent_text}</a>'
        elif ent.__class__.__name__ == 'MessageEntityMentionName':
            result += ent_text
        elif ent.__class__.__name__ == 'MessageEntityMention':
            result += ent_text
        elif ent.__class__.__name__ == 'MessageEntityUnderline':
            result += f'<u>{ent_text}</u>'
        elif ent.__class__.__name__ == 'MessageEntityStrike':
            result += f'<s>{ent_text}</s>'
        else:
            result += ent_text
        last_offset = ent.offset + ent.length
    result += html.escape(text[last_offset:])
    return result

# ✅ CONFIGURATION FROM config.json
CONFIG_FILE = 'config.json'
if not os.path.exists(CONFIG_FILE):
    print(f"❌ {CONFIG_FILE} not found. Please create it with your api_id, api_hash, phone_number, source_channel, destination_channel.")
    sys.exit(1)
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)
try:
    api_id = config['api_id']
    api_hash = config['api_hash']
    phone_number = config['phone_number']
    source_channel = config['source_channel']
    destination_channel = config['destination_channel']
except KeyError as e:
    print(f"❌ Missing key in config.json: {e}")
    sys.exit(1)

last_id_file = 'last_message_id.txt'
client = TelegramClient('devspy_session', api_id, api_hash)

async def main():
    await client.connect()
    if not await client.is_user_authorized():
        try:
            await client.send_code_request(phone_number)
            code = input('📩 Enter the OTP sent to your Telegram: ')
            await client.sign_in(phone_number, code)
        except Exception as e:
            if 'PhoneNumberBannedError' in str(type(e)):
                print("❌ This phone number is banned by Telegram. Please use a different number.")
                sys.exit(1)
            print(f"❌ Error during sign-in: {e}")
            return

    source = await client.get_entity(source_channel)
    dest = await client.get_entity(destination_channel)

    last_id = 0
    if os.path.exists(last_id_file):
        with open(last_id_file, 'r') as f:
            content = f.read().strip()
            if content.isdigit():
                last_id = int(content)

    total_copied = 0
    limit = 100

    # If last_id is 0, start from the very first message (ID 1)
    if last_id == 0:
        last_id = 1
        print("Starting from the very first message (ID 1)")

    while True:
        history = await client(GetHistoryRequest(
            peer=source,
            limit=limit,
            offset_date=None,
            offset_id=0,
            max_id=0,
            min_id=last_id,
            add_offset=0,
            hash=0
        ))

        messages = history.messages
        if not messages:
            print("✅ All messages copied.")
            break

        messages = sorted(messages, key=lambda x: x.id)

        # Grouped media handling: group by group_id
        grouped = {}
        for msg in messages:
            group_id = getattr(msg, 'grouped_id', None)
            if group_id:
                grouped.setdefault(group_id, []).append(msg)
            else:
                grouped[msg.id] = [msg]

        for group in grouped.values():
            # If group has more than one message, it's a media group
            if len(group) > 1:
                media_files = []
                caption = None
                for m in group:
                    if m.media:
                        media_files.append(m.media)
                    if m.message and not caption:
                        # Convert entities to HTML for caption
                        if m.entities:
                            caption = get_message_text_with_entities(m.message, m.entities, 'html')
                        else:
                            caption = m.message
                try:
                    await client.send_file(dest, media_files, caption=caption or "", parse_mode='html')
                    print(f"✅ Sent media group IDs: {[m.id for m in group]}")
                    last_id = max(m.id for m in group)
                    total_copied += len(group)
                    with open(last_id_file, 'w') as f:
                        f.write(str(last_id))
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"❌ Error sending media group {[m.id for m in group]}: {e}")
                    continue
            else:
                msg = group[0]
                if not getattr(msg, 'message', None) and not getattr(msg, 'media', None):
                    continue
                try:
                    if msg.media:
                        # Convert entities to HTML for caption
                        caption = msg.message
                        if msg.entities:
                            caption = get_message_text_with_entities(msg.message, msg.entities, 'html')
                        await client.send_file(dest, msg.media, caption=caption or "", parse_mode='html')
                    elif msg.message:
                        # Convert entities to HTML for text
                        text = msg.message
                        if msg.entities:
                            text = get_message_text_with_entities(msg.message, msg.entities, 'html')
                        await client.send_message(dest, text, parse_mode='html', link_preview=True)
                    else:
                        await client.forward_messages(dest, msg)
                    print(f"✅ Sent message ID: {msg.id}")
                    last_id = msg.id
                    total_copied += 1
                    with open(last_id_file, 'w') as f:
                        f.write(str(last_id))
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"❌ Error sending message ID {msg.id}: {e}")
                    continue

    print(f"🎉 Done! Total messages copied: {total_copied}")

with client:
    client.loop.run_until_complete(main())
