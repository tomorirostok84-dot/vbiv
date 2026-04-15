import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
TOKEN = "8628802648:AAE2hslnPkxMETpuJPTMjM55L71zDmQxuSc"
GROUP_FROM = -1003845204224  # Группа А (Откуда просят)
GROUP_TO = -1003539495686    # Группа Б (Где дают номер)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class BotStates(StatesGroup):
    waiting_for_number = State()
    waiting_for_code = State()

# 1. Ловим сообщение "номер" в Группе А и кидаем кнопку в Группу Б
@dp.message(F.chat.id == GROUP_FROM)
async def handle_request(message: types.Message):
    if message.text and ("номер" in message.text.lower() or any(c.isdigit() for c in message.text)):
        builder = InlineKeyboardBuilder()
        # Привязываем ID того, кто просит, к кнопке
        builder.button(text="Ввести номер", callback_data=f"take_{message.from_user.id}")
        
        await bot.send_message(
            GROUP_TO, 
            f"📩 **Нужен номер!**\nДля пользователя: @{message.from_user.username or 'User'}", 
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )

# 2. Обработка нажатия кнопки "Ввести номер" в Группе Б
@dp.callback_query(F.data.startswith("take_"))
async def start_input(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_number)
    try:
        await bot.send_message(callback.from_user.id, "Введите номер телефона, который вы хотите дать:")
        await callback.answer("Бот написал вам в личные сообщения!", show_alert=True)
    except Exception:
        await callback.answer("❌ Сначала запустите бота (нажмите Старт в боте)!", show_alert=True)

# 3. Принимаем номер в ЛС и отправляем в Группу А
@dp.message(BotStates.waiting_for_number, F.chat.type == "private")
async def process_number(message: types.Message, state: FSMContext):
    phone = message.text
    builder = InlineKeyboardBuilder()
    # Привязываем ID того, кто ДАЛ номер, чтобы у него потом просить код
    builder.button(text="Нужен код", callback_data=f"nc_{message.from_user.id}")
    
    await bot.send_message(
        GROUP_FROM, 
        f"✅ **Поступил номер:** `{phone}`\nНажмите кнопку ниже, если нужен код.", 
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await message.answer("Номер передан. Когда потребуется код, я пришлю запрос сюда.")
    await state.clear()

# 4. Нажатие кнопки "Нужен код" в Группе А
@dp.callback_query(F.data.startswith("nc_"))
async def request_code(callback: types.CallbackQuery):
    provider_id = int(callback.data.split("_")[1])
    
    # Устанавливаем состояние ожидания кода для того, кто давал номер
    state_ctx = dp.fsm.get_context(bot, user_id=provider_id, chat_id=provider_id)
    await state_ctx.set_state(BotStates.waiting_for_code)
    
    try:
        await bot.send_message(provider_id, "🔔 **Запросили код!** Введите его прямо сюда:")
        await callback.answer("Запрос кода отправлен!")
    except Exception:
        await callback.answer("Ошибка: бот не может написать пользователю", show_alert=True)

# 5. Принимаем код в ЛС и отправляем в Группу А
@dp.message(BotStates.waiting_for_code, F.chat.type == "private")
async def process_code(message: types.Message, state: FSMContext):
    code = message.text
    await bot.send_message(GROUP_FROM, f"🔑 **КОД ДЛЯ НОМЕРА:** `{code}`", parse_mode="Markdown")
    await message.answer("Код успешно передан!")
    await state.clear()

# Запуск
async def main():
    print("Бот запущен и готов к работе!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот выключен")
                   
