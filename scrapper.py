import asyncio
import base64
import re
from telethon import TelegramClient, events
from telethon.tl.types import InputPeerChannel, InputPeerChat

# Configuration
API_ID = 33982887
API_HASH = 'f2c191d8603cd17ff6c4f8b914c24885'
BOT_TOKEN = '8560540262:AAG_zP723hrB-SNuNQwpswASIqoQrnrAcwU'  # From @BotFather
SESSION_NAME = 'scraper_bot'

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
client.start(bot_token=BOT_TOKEN)

# Regex to find potential Base64 strings (adjust as needed)
BASE64_REGEX = re.compile(r'[A-Za-z0-9+/]+={0,2}')

def decode_cc(base64_str):
    try:
        # Add padding if missing
        missing_padding = len(base64_str) % 4
        if missing_padding:
            base64_str += '=' * (4 - missing_padding)
        decoded = base64.b64decode(base64_str).decode('utf-8')
        # Validate format
        if '|' in decoded and len(decoded.split('|')) == 4:
            return decoded
    except Exception:
        pass
    return None

@client.on(events.NewMessage(pattern='/scr'))
async def handle_scrape(event):
    # Parse command: /scr @vip_scrapper1 500
    args = event.message.text.split()
    if len(args) != 3:
        await event.reply('Usage: /scr [@username|link] [amount]')
        return

    target = args[1]
    try:
        amount = int(args[2])
    except ValueError:
        await event.reply('Invalid amount. Provide a number.')
        return

    await event.reply(f'[+] Starting scrape of {target} for {amount} items...')

    # Resolve target entity
    try:
        if 't.me/' in target:
            target = target.split('t.me/')[-1]
        entity = await client.get_entity(target)
    except Exception as e:
        await event.reply(f'[-] Failed to resolve target: {e}')
        return

    # Scrape messages
    scraped_data = []
    try:
        async for message in client.iter_messages(entity, limit=amount):
            if message.text:
                matches = BASE64_REGEX.findall(message.text)
                for match in matches:
                    decoded = decode_cc(match)
                    if decoded:
                        scraped_data.append(decoded)
                        if len(scraped_data) >= amount:
                            break
            if len(scraped_data) >= amount:
                break
    except Exception as e:
        await event.reply(f'[-] Scrape error: {e}')
        return

    # Output
    if not scraped_data:
        await event.reply('[-] No valid data found.')
        return

    # Save to file
    filename = f'scraped_{target.replace("/", "_")}.txt'
    with open(filename, 'w') as f:
        for item in scraped_data:
            f.write(item + '\n')

    # Send file
    await client.send_file(
        event.chat_id,
        filename,
        caption=f'[+] Scraped {len(scraped_data)} items.'
    )

# Start the bot
print("Bot running...")
client.run_until_disconnected()