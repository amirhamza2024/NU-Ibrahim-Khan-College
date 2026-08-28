import os
import asyncio
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from replicate.client import Client

# --- ১. টোকেন সেটআপ ---
BOT_TOKEN = "8938455906:AAGOr-_VXu7r6OPuEp3P5OI_aRt0Do7qX9o"  # আপনার আসল বট টোকেন দিন
REPLICATE_API_TOKEN = "r8_7KCb6JDluZHbZSHhzvGIezEnkEmlqvz0J4IHN"                     # আপনার Replicate টোকেন দিন

# --- ২. Flask সার্ভার (Render এর Port Binding এর জন্য) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running!"

def run_flask():
    # Render নিজে থেকে PORT ভ্যারিয়েবল পাঠায়, না পেলে ডিফল্ট 8080 নিবে
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- ৩. টেলিগ্রাম বট সেটআপ ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
replicate_client = Client(api_token=REPLICATE_API_TOKEN)

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
        output = replicate_client.run(
            "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
            input={
                "swap_image": source_url,
                "input_image": target_url
            }
        )
        
        result_url = str(output)
        await message.answer_photo(photo=result_url, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে: {str(e)}")
    
    await state.clear()

# --- ৪. মেইন ফাংশন ---
async def main():
    keep_alive()  # ব্যাকগ্রাউন্ডে Flask সার্ভার চালু করবে
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
