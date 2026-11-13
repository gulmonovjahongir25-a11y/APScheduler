import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from google import genai
from google.genai import types as genai_types
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TELEGRAM_BOT_TOKEN = "9181868681:AAGhzLP4NjEw_Xrm49sQeyR4i6pKamgM6do"
GEMINI_API_KEY = "AQ.Ab8RN6JkDCAaO3mtXbh6JJyUuwbgi6rM6ju38GuO119wUpF1dw"

client = genai.Client(api_key=GEMINI_API_KEY)
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_sessions = {}
active_users = set()

SYSTEM_INSTRUCTION = """Sen Matematika Milliy Sertifikatidan A+ daraja olishga tayyorlaydigan professional mentorsan.
BAZADAGI REAL TESTLAR VA REJA: Hosila, integral, stereometriya va progressiyaning birinchi prinsipdan isbotlash talab qilinadigan murakkab masalalari.
QOIDALAR:
1. Ruxsat kutmasdan doim o'zing tashabbusni ushla va 1-savolni darhol ber.
2. Formulalarni va yechimni tushunarli matn yoki LaTeX formatida tushuntir."""

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    
    chat = client.chats.create(
        model="gemini-2.5-flash", 
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.6
        )
    )
    user_sessions[user_id] = chat
    
    response = chat.send_message("Milliy Sertifikat real test bazasidan hoziroq 1-kunning isbot yoki hisob-kitob masalasini ber.")
    await message.answer(response.text)

@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)
    
    if user_id not in user_sessions:
        chat = client.chats.create(model="gemini-2.5-flash", config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.6))
        user_sessions[user_id] = chat
    else:
        chat = user_sessions[user_id]

    response = chat.send_message(message.text)
    await message.answer(response.text)

# Ovozli xabarlarni qayta ishlash (Gemini Multimodal orqali)
@dp.message(F.voice)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    active_users.add(user_id)

    if user_id not in user_sessions:
        chat = client.chats.create(model="gemini-2.5-flash", config=genai_types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTION, temperature=0.6))
        user_sessions[user_id] = chat
    else:
        chat = user_sessions[user_id]

    # Telegramdan ovozli faylni yuklab olish
    voice = message.voice
    file = await bot.get_file(voice.file_id)
    local_file = f"voice_{user_id}.oga"
    await bot.download_file(file.file_path, local_file)

    try:
        await message.answer("🎙 Ovozli xabaringiz tahlil qilinmoqda...")
        
        # Gemini faylni to'g'ridan-to'g'ri o'qib tahlil qilishi uchun yuklaymiz
        audio_file_ref = client.files.upload(file=local_file)
        
        # Chat orqali audio faylni yuborib javob olamiz
        response = chat.send_message([
            audio_file_ref, 
            "Mana mening ovozli javobim/savolim. Uni o'qib tahlil qil va keyingi masalani ber."
        ])
        
        await message.answer(response.text)
    except Exception as e:
        await message.answer(f"❌ Ovozli xabarni o'qishda xatolik: {e}")
    finally:
        if os.path.exists(local_file):
            os.remove(local_file)

async def send_daily_reminders():
    reminder_text = "⏰ *Kunlik eslatma!* Matematika Milliy Sertifikati uchun bugungi mashq vaqti keldi. Qani, navbatdagi masalani boshlaymiz!"
    for user_id in active_users:
        try:
            await bot.send_message(user_id, reminder_text)
        except Exception:
            pass

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_reminders, 'cron', hour=20, minute=0)
    scheduler.start()

    print("Bot ovozli xabar va scheduler bilan to'liq ishga tushdi...")
    await dp.main_loop() if hasattr(dp, 'main_loop') else await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
