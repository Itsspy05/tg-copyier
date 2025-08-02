# Telegram Channel Message Copier

This script copies all messages (including media) from one Telegram channel to another using Telethon.

## Requirements
- Python 3.7+
- Telethon
- asyncio

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Update the script with your own `api_id`, `api_hash`, `phone_number`, `source_channel`, and `destination_channel`.
3. Run the script:
   ```bash
   python telegram_channel_copier.py
   ```

## Notes
- The script saves the last copied message ID in `last_message_id.txt` to avoid duplicates.
- You must be an admin in the destination channel.
- Keep your API credentials secure.
