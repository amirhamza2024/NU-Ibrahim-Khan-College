import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from gradio_client import Client, handle_file

# --- ১. টোকেন কনফিগারেশন ---
BOT_TOKEN = "8938455906:AAGOr-_VXu7r6OPuEp3P5OI_aRt0Do7qX9o"

# আপনার Hugging Face টোকেন
hf_p1 = "hf_GmeHNjTPXPrgKQ"
hf_p2 = "RqVyObewSdFfeIXQjDUg"
HF_TOKEN = hf_p1 + hf_p2

# --- ২. Render Web Service এর জন্য Flask সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "FaceSwap Bot is running with Hugging Face Token!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ৩. টেলিগ্রাম বট ও Hugging Face ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Hugging Face ক্লায়েন্টে আপনার টোকেন কানেক্ট করা হলো
hf_client = Client("tuan2308/face-swap", hf_token=HF_TOKEN)

class SwapStates(StatesGroup):
    waiting_for_source = State()
    waiting_for_target = State()

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    await message.answer("🎭 **FaceSwap Bot-এ স্বাগতম!**\n\nফেস সোয়াপ করতে **/swap** কমান্ড দিন।")

@dp.message(F.text == "/swap")
async def swap_cmd(message: types.Message, state: FSMContext):
    await message.answer("১️⃣ যার মুখ বসাতে চান (Source Face), তার ছবি পাঠান:")
    await state.set_state(SwapStates.waiting_for_source)

# প্রথম ছবি নেওয়া
@dp.message(SwapStates.waiting_for_source, F.photo)
async def get_source(message: types.Message, state: FSMContext):
    file = await bot.get_file(message.photo[-1].file_id)
    source_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(source_url=source_url)
    
    await message.answer("✅ প্রথম ছবি পেয়েছি!\n\n২️⃣ এবার মূল ছবি (Target Body/Image) পাঠান যেটিতে মুখ বসবে:")
    await state.set_state(SwapStates.waiting_for_target)

# দ্বিতীয় ছবি নেওয়া এবং ফেস সোয়াপ করা
@dp.message(SwapStates.waiting_for_target, F.photo)
async def get_target_and_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    source_url = data['source_url']
    
    file = await bot.get_file(message.photo[-1].file_id)
    target_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    await message.answer("⏳ ফেস সোয়াপ করা হচ্ছে, দয়া করে ১০-১৫ সেকেন্ড অপেক্ষা করুন...")
    
    try:
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None, 
            lambda: hf_client.predict(
                source_image=handle_file(source_url),
                target_image=handle_file(target_url),
                api_name="/predict"
            )
        )
        
        photo_to_send = FSInputFile(result_path)
        await message.answer_photo(photo=photo_to_send, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে: {str(e)}")
    
    await state.clear()

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
