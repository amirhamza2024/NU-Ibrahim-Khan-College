import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import replicate

# --- ১. আপনার টোকেন দুটো এখানে বসান ---
BOT_TOKEN = "8938455906:AAGOr-_VXu7r6OPuEp3P5OI_aRt0Do7qX9o"
os.environ["REPLICATE_API_TOKEN"] = "r8_eqQ9oj4H0gZkzRJZvxgDiFAI1aVmgIg3JBcCR"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ইউজারের ধাপ সংরক্ষণের জন্য স্টেট
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

# দ্বিতীয় ছবি নেওয়া এবং সোয়াপ সম্পন্ন করা
@dp.message(SwapStates.waiting_for_target, F.photo)
async def get_target_and_process(message: types.Message, state: FSMContext):
    data = await state.get_data()
    source_url = data['source_url']
    
    file = await bot.get_file(message.photo[-1].file_id)
    target_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    
    await message.answer("⏳ ফেস সোয়াপ করা হচ্ছে, দয়া করে ১০-১৫ সেকেন্ড অপেক্ষা করুন...")
    
    try:
        # Replicate এর cdingram/face-swap মডেল
        output = replicate.run(
            "cdingram/face-swap:d1d6ea8c8be89d664a07a457526f7128109dee7030fdac424788d762c71ed111",
            input={
                "swap_image": source_url,   # যার মুখ বসবে
                "input_image": target_url   # মূল টার্গেট ছবি
            }
        )
        
        # আউটপুট URL পাঠানো
        result_url = str(output)
        await message.answer_photo(photo=result_url, caption="✨ আপনার সোয়াপ করা ছবি তৈরি!")
    except Exception as e:
        await message.answer(f"❌ কোনো সমস্যা হয়েছে: {str(e)}")
    
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
