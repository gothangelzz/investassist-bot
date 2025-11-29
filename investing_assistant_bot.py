from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
import asyncio
import json
import os
import feedparser
from dotenv import load_dotenv
import logging
import requests
import transformers 
import pipeline
import yfinance as yf
logging.basicConfig(level=logging.INFO, filename="bot.log")

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")  # токен Telegram

ADMIN_ID = 5586645694  # ваш Telegram ID


DB_FILE = "users.json"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher()
CATEGORIES = ["Акции", "Облигации", "Фонды"]
user_portfolios = {}  # {user_id: {"Акции": [], "Облигации": [], "Фонды": []}}

# ===== Работа с базой пользователей =====
def load_users():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(DB_FILE, "w") as f:
        json.dump(users, f)


# ====== /start только подписывает ======
@dp.message(Command("start"))
async def start(message: Message):
    users = load_users()
    user_id = message.from_user.id

    if user_id not in users:
        users.append(user_id)
        save_users(users)

    await message.answer("/income - рассчитать доход за 12 месяцев📈\n"
    "/help - если нужна помощь или задать вопрос⚙️\n"
    "/instruction - инструкция по использованию и формат ввода активов в (/income)\n"
    "/disclaimer - дисклеймер(рекомендуется к прочтению)❗\n\n"
    "Бот будет отправлять рассылку с новостями и интересными моментами в мире инвестиций📰"
    )

# ====== /send делает рассылку только админу ======
@dp.message(Command("send"))
async def send_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔ Нет прав!")

    text = message.text.replace("/send", "").strip()

    if not text:
        return await message.answer(
            "❗ Использование: `/send текст сообщения`", parse_mode="Markdown"
        )

    users = load_users()
    sent = 0

    for user in users:
        try:
            await bot.send_message(user, text)
            sent += 1
        except:
            pass

    await message.answer(f"📨 Сообщение отправлено {sent} пользователям.")

@dp.message(Command('help'))
async def help_command(message: Message):
    await message.answer('Помощь, вопросы и предложения: @diedofxan')

@dp.message(Command('disclaimer'))
async def disclaimer_command(message: Message):
    await message.answer("Бот не является инвестиционным консультантом."
    "Информация носит образовательный и аналитический характер и не является призывом к покупке или продаже активов.\n\n"

    "Бот работает на основе ИИ."  )

@dp.message(Command('instruction'))
async def instruction_command(message: Message):
    await message.answer("Форматы ввода:\n"
        "- Акции: количество:цена:рост(%):дивиденды\n"
        "- Облигации: количество:цена:рост(%):купоны\n"
        "- Фонды: количество:цена:рост(%) (без дивидендов/купонов)\n"
        "Можно вводить несколько активов через запятую.\n"
        "Пропуск категории: /skip\n"
        "Примеры:\n"
        "Акции: SBER:10:150:12:5, GAZP:5:200:10:4\n"
        "Облигации: OFZ-26214:10:1000:8:50, RU000A100XH0:5:950:7:40\n"
        "Фонды: ETF1:10:120:8, ETF2:5:100:6")

class IncomeStates(StatesGroup):
    waiting_assets = State()

# ====== /income ======
@dp.message(Command("income"))
async def income_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_portfolios[user_id] = {cat: [] for cat in CATEGORIES}
    await state.update_data(current_category_index=0)
    await message.answer(
        "Начнем ввод вашего портфеля💼"
    )
    await ask_next_category(message, state)

# ====== Запрос следующей категории ======
async def ask_next_category(message: Message, state: FSMContext):
    data = await state.get_data()
    idx = data.get("current_category_index", 0)

    if idx >= len(CATEGORIES):
        await calculate_and_send(message)
        await state.clear()
        return

    category = CATEGORIES[idx]
    await state.update_data(current_category=category)
    await message.answer(f"Введите активы для категории *{category}* через запятую или /skip:", parse_mode="Markdown")
    await state.set_state(IncomeStates.waiting_assets)

# ====== Обработка ввода активов ======
@dp.message(IncomeStates.waiting_assets)
async def process_assets(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    idx = data.get("current_category_index", 0)
    category = CATEGORIES[idx]

    if message.text.strip().lower() == "/skip":
        await state.update_data(current_category_index=idx + 1)
        await ask_next_category(message, state)
        return

    entries = message.text.split(",")
    assets = []

    for entry in entries:
        try:
            parts = entry.strip().split(":")
            if category == "Фонды":
                # Формат для фондов: [название(необязательно)]:кол-во:цена:рост(%)
                if len(parts) == 3:  # без названия
                    qty, price, growth = parts
                    name = ""
                else:
                    name, qty, price, growth = parts
                div = 0.0
            else:
                # Формат для акций и облигаций: [название(необязательно)]:кол-во:цена:рост(%):див/купон
                if len(parts) == 4:  # без названия
                    qty, price, growth, div = parts
                    name = ""
                else:
                    name, qty, price, growth, div = parts

            qty = float(qty)
            price = float(price)
            growth = float(growth)
            div = float(div)

            final_value = qty * price * (1 + growth/100) + qty * div

            assets.append({
                "name": name,
                "quantity": qty,
                "price": price,
                "growth": growth,
                "dividend": div,
                "final_value": final_value
            })
        except:
            await message.answer(
                f"❗ Неправильный формат: {entry}\nПроверьте формат для этой категории."
            )
            return

    user_portfolios[user_id][category] = assets
    await state.update_data(current_category_index=idx + 1)
    await ask_next_category(message, state)

# ====== Рассчет итоговой суммы и ИИ ======
async def calculate_and_send(message: Message):
    user_id = message.from_user.id
    portfolio = user_portfolios[user_id]
    total_sum = 0.0
    portfolio_text_lines = []

    for category, assets in portfolio.items():
        for a in assets:
            total_sum += a["final_value"]
            name_display = f"{a['name']} " if a['name'] else ""
            portfolio_text_lines.append(
                f"{category} {name_display}×{a['quantity']} шт, цена {a['price']}, рост {a['growth']}%, дивиденды {a['dividend']}"
            )

    portfolio_text = "\n".join(portfolio_text_lines)



    reply = f"📊 Общая сумма портфеля за 12 месяцев: {total_sum:.2f}\n\n"
    await message.answer(reply)




# ====== Запуск бота ======
async def main():
    print("active")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())