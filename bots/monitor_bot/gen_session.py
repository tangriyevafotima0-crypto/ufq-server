"""
gen_session.py — StringSession generatsiya qiluvchi
Lokal va serverda ham ishlaydi.

Lokal: python gen_session.py
Server: setup_env.sh tomonidan avtomatik chaqiriladi
"""
import asyncio
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession


async def main():
    # Argumentlar: api_id api_hash phone output_file
    args = sys.argv[1:]

    if len(args) >= 3:
        API_ID   = int(args[0])
        API_HASH = args[1]
        PHONE    = args[2]
        OUTPUT   = args[3] if len(args) > 3 else None
    else:
        # Lokal interaktiv rejim
        API_ID   = int(input("API_ID: ").strip())
        API_HASH = input("API_HASH: ").strip()
        PHONE    = input("Telefon (+998...): ").strip()
        OUTPUT   = None

    async with TelegramClient(StringSession(), API_ID, API_HASH) as client:
        await client.start(phone=PHONE)
        session_str = client.session.save()
        me = await client.get_me()

        if OUTPUT:
            # Server rejimi — faqat session string faylga
            with open(OUTPUT, "w") as f:
                f.write(session_str)
            print(f"✅ Kirish muvaffaqiyatli: {me.first_name} (ID: {me.id})")
        else:
            # Lokal rejim — ekranga chiqarish
            print("\n" + "═" * 60)
            print("✅ SESSION_STRING:")
            print(session_str)
            print("═" * 60)
            print(f"\nHisob: {me.first_name} | ID: {me.id}")
            print("Bu ID ni OWNER_ID sifatida ham ishlating!")


asyncio.run(main())
