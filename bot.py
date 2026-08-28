import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
import requests

# --- ১. টোকেন ও Segmind API Key কনফিগারেশন ---
BOT_TOKEN = "8938455906:AAGOr-_VXu7r6OPuEp3P5OI_aRt0Do7qX9o"

# Segmind API Key (Environment variable অথবা সরাসরি কি)
SEGMIND_KEY = os.environ.get("SEGMIND_KEY", "SG_fb61e977375076e3").strip()

# --- ২. Render Web Service-এর জন্য Flask সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "FaceSwap Bot is live and running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ৩. টেলিগ্রাম বট ও Segmind Direct API ফাংশন ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def run_segmind_swap(source_url: str, target_url: str):
    endpoint = "https://api.segmind.com/v1/hyperswap-image-faceswap-by-facefusion-labs"
    
    # 401 এরর এড়াতে x-api-key এবং Authorization দুটি হেডারই রাখা হয়েছে
    headers = {
        "x-api-key": SEGMIND_KEY,
        "Authorization": f"Bearer {SEGMIND_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "source_image": source_url,
        "target_image": target_url,
        "model_name": "hyperswap_1c",
        "output_format": "png",
        "output_quality": 95
    }

    response = requests.post(endpoint, json=payload, headers=headers, timeout=60)
    
    if response.status_code == 200:
        return response.content
    else:
        try:
            error_data = response.json()
            err_msg = error_data.get("detail", error_data.get("error", response.text))
        except Exception:
            err_msg = response.text
        raise Exception(f"Segmind Error ({response.status_code}): {err_msg}")

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

# প্রথম ছবি রিসিভ
@dp.message(SwapStates.waiting_for_source, F.photo)
async def get_source(message: types.Message, state: FSMContext):
    file = await bot.get_file(message.photo[-1].file_id)
    source_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(source_url=source_url)
    
    await message.answer("✅ প্রথম ছবি পেয়েছি!\n\n২️⃣ এবার মূল ছবি (Target Body/Image) পাঠান যেটিতে মুখ বসবে:")
    await state.set_state(SwapStates.waiting_for_target)

# দ্বিতীয় ছবি রিসিভ ও সোয়াপ প্রসেস
@dp.message(SwapStates.waiting_for_target, F.photo)
async def get_target_and_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    source_url = data['source_url']
    
    file = await bot.get_file(message.photo[-1].file_id)
    target_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    await message.answer("⏳ Segmind দিয়ে ফেস সোয়াপ করা হচ্ছে, মাত্র ৫-১০ সেকেন্ড অপেক্ষা করুন...")
    
    try:
        loop = asyncio.get_event_loop()
        image_bytes = await loop.run_in_executor(
            None,
            run_segmind_swap,
            source_url,
            target_url
        )
        
        photo_to_send = BufferedInputFile(image_bytes, filename="faceswap.png")
        await message.answer_photo(photo=photo_to_send, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে:\n{str(e)}")
    
    await state.clear()

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
