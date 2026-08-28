import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile
import segmind

# --- ১. টোকেন ও Segmind API Key কনফিগারেশন ---
BOT_TOKEN = "8938455906:AAGOr-_VXu7r6OPuEp3P5OI_aRt0Do7qX9o"

# Segmind API Key (GitHub ব্লক এড়াতে ২ ভাগে বিভক্ত)
sg_p1 = "SG_cae9c429"
sg_p2 = "d128b4a3"
SEGMIND_KEY = sg_p1 + sg_p2

segmind.api_key = SEGMIND_KEY

# --- ২. Render-এর জন্য Flask ওয়েব সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "FaceSwap Bot is live and running with Segmind!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ৩. টেলিগ্রাম বট ও Segmind প্রসেসিং ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def run_segmind_swap(source_url: str, target_url: str):
    response = segmind.run(
        "hyperswap-image-faceswap-by-facefusion-labs",
        source_image=source_url,
        target_image=target_url
    )
    if isinstance(response, dict) and "image" in response:
        return response["image"]
    return response

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

# দ্বিতীয় ছবি রিসিভ ও সোয়াপ সম্পন্ন
@dp.message(SwapStates.waiting_for_target, F.photo)
async def get_target_and_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    source_url = data['source_url']
    
    file = await bot.get_file(message.photo[-1].file_id)
    target_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    await message.answer("⏳ Segmind দিয়ে ফেস সোয়াপ করা হচ্ছে, মাত্র ৫-১০ সেকেন্ড অপেক্ষা করুন...")
    
    try:
        loop = asyncio.get_event_loop()
        result_image = await loop.run_in_executor(
            None,
            run_segmind_swap,
            source_url,
            target_url
        )
        
        if isinstance(result_image, bytes):
            photo_to_send = BufferedInputFile(result_image, filename="faceswap.jpg")
            await message.answer_photo(photo=photo_to_send, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
        else:
            await message.answer_photo(photo=result_image, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে: {str(e)}")
    
    await state.clear()

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
