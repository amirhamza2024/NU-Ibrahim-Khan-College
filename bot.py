import os
import asyncio
import aiohttp
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

hf_p1 = "hf_GmeHNjTPXPrgKQ"
hf_p2 = "RqVyObewSdFfeIXQjDUg"
HF_TOKEN = hf_p1 + hf_p2

# --- ২. Render Web Service এর জন্য Flask সার্ভার ---
app = Flask(__name__)

@app.route('/')
def home():
    return "FaceSwap Bot is running perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ৩. টেলিগ্রাম বট ও Hugging Face ফাংশন ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ইমেজ ডাউনলোড ফাংশন
async def download_image(url: str, save_path: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(save_path, 'wb') as f:
                    f.write(await resp.read())
                return True
    return False

# ফেস সোয়াপ প্রসেস (tonyassi স্পেসের সঠিক প্যারামিটার অর্ডার)
def process_face_swap(source_local_path: str, target_local_path: str):
    client = Client("tonyassi/face-swap", token=HF_TOKEN)
    # tonyassi স্পেসে: প্রথম ইনপুট Target, দ্বিতীয় ইনপুট Source
    result = client.predict(
        target_image=handle_file(target_local_path),
        source_image=handle_file(source_local_path),
        fn_index=0
    )
    if isinstance(result, tuple) or isinstance(result, list):
        return result[0]
    return result

class SwapStates(StatesGroup):
    waiting_for_source = State()
    waiting_for_target = State()

@dp.message(F.text == "/start")
async def start_cmd(message: types.Message):
    await message.answer("🎭 **FaceSwap Bot-এ স্বাগতম!**\n\nফেস সোয়াপ করতে **/swap** কমান্ড দিন।")

@dp.message(F.text == "/swap")
async def swap_cmd(message: types.Message, state: FSMContext):
    await message.answer("১️⃣ যার মুখ বসাতে চান (Source Face), তার পরিষ্কার ছবি পাঠান:")
    await state.set_state(SwapStates.waiting_for_source)

# প্রথম ছবি রিসিভ
@dp.message(SwapStates.waiting_for_source, F.photo)
async def get_source(message: types.Message, state: FSMContext):
    file = await bot.get_file(message.photo[-1].file_id)
    source_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    await state.update_data(source_url=source_url)
    
    await message.answer("✅ প্রথম ছবি পেয়েছি!\n\n২️⃣ এবার মূল ছবি (Target Body/Image) পাঠান যেটিতে মুখ বসবে:")
    await state.set_state(SwapStates.waiting_for_target)

# দ্বিতীয় ছবি রিসিভ ও সোয়াপ সম্পন্ন
@dp.message(SwapStates.waiting_for_target, F.photo)
async def get_target_and_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    source_url = data['source_url']
    
    file = await bot.get_file(message.photo[-1].file_id)
    target_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    await message.answer("⏳ ফেস সোয়াপ করা হচ্ছে, অনুগ্রহ করে ১৫-২০ সেকেন্ড অপেক্ষা করুন...")
    
    user_id = message.from_user.id
    source_path = f"src_{user_id}.jpg"
    target_path = f"tgt_{user_id}.jpg"
    
    try:
        await download_image(source_url, source_path)
        await download_image(target_url, target_path)
        
        loop = asyncio.get_event_loop()
        result_path = await loop.run_in_executor(
            None,
            process_face_swap,
            source_path,
            target_path
        )
        
        photo_to_send = FSInputFile(result_path)
        await message.answer_photo(photo=photo_to_send, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে: {str(e)}\n\n(টিপস: সোর্স ও টার্গেট ছবিতে যেন মুখ পরিষ্কারভাবে দেখা যায়)")
    finally:
        if os.path.exists(source_path):
            os.remove(source_path)
        if os.path.exists(target_path):
            os.remove(target_path)
    
    await state.clear()

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
