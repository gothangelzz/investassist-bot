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
import requests
import yfinance as yf
from aiogram import Router
router = Router()




BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PREMIUM_FILE = os.path.join(BASE_DIR, "premium_users.json")
DB_FILE = os.path.join(BASE_DIR, "users.json")

BOT_TOKEN = ""

ADMIN_ID = 5586645694  # ваш Telegram ID



bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(router)
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


def load_premium_users():
    if not os.path.exists(PREMIUM_FILE):
        with open(PREMIUM_FILE, "w") as f:
            json.dump([], f)
        return []
    with open(PREMIUM_FILE, "r") as f:
        data = json.load(f)
        return [int(uid) for uid in data]  # важно, чтобы все были числа

# ====== /start только подписывает ======
@router.message(Command("start"))
async def start(message: Message):
    users = load_users()
    user_id = message.from_user.id

    if user_id not in users:
        users.append(user_id)
        asyncio.create_task(save_users(users))

    await message.answer("/help - если нужна помощь или задать вопрос.⚙️\n"
    "/disclaimer - дисклеймер (рекомендуется к прочтению).❗\n"
    "/subscribe - оформить премиум подписку за 149₽ или узнать действует ли подписка.🔔\n"
    "/subscribe_description - возможности премиум подписки.📄\n"
    "/premium_instruction - инструкция для премиум функций бота.📖\n"
    "/instruction - инструкция по использованию и формат ввода активов в (/income).📝\n\n"
    'Базовые функции бота:\n'
    "/income - рассчитать доход за 12 месяцев.📈\n"
    "/portfolio_type - определить тип портфеля.💼\n\n"
    "Премиум функции бота:\n"
    "/diversification - узнать диверсификацию портфеля.⚖️\n"
    "/risk - узнать насколько рискованный ваш портфель.⚠️\n"
    "/top - самые сильные и самые слабые активы портфеля.🔝\n"
    "/sharpe - коэффициент Шарпа.📊\n"
    "/tax- расчет налога с дохода вашего портфеля.🧾\n\n"
    "Бот будет отправлять рассылку с новостями и интересными моментами в мире инвестиций.📰"
    )



# ====== Команда подписки ======
@router.message(Command("subscribe"))
async def subscribe(message: Message):
    user_id = int(message.from_user.id)
    premium_users = load_premium_users()  # читаем файл прямо перед проверкой

    if user_id in premium_users:
        await message.answer("✅ Вы уже премиум подписчик!")
    else:
        await message.answer("Обратитесь в поддержку для оформления премиум подписки.")
    

# ====== /send делает рассылку только админу ======
@router.message(Command("send"))
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

@router.message(Command('help'))
async def help_command(message: Message):
    await message.answer('Помощь, вопросы и предложения:@diedofxan')

@router.message(Command('premium_instruction'))
async def subdesc_command(message: Message):
    await message.answer('Эти функции доступны только для платных подписчиков и позволяют анализировать ваш портфель более детально.\n\n'

'1️⃣ /diversification — проверка диверсификации портфеля\n'
 ' Анализирует долю каждой акции в портфеле.\n'
 ' Если один актив занимает более 30% от всех акций, бот выдаст предупреждение ⚠.\n'
 ' Позволяет понять, насколько ваш портфель сбалансирован.\n\n'

'2️⃣ /risk — оценка риска портфеля\n'
 ' Рассчитывает стандартное отклонение доходности портфеля.\n'
 ' Чем выше значение, тем более волатильный и рискованный портфель.\n'
 ' Бот классифицирует риск как:\n'
 ' Низкий — стабильный портфель, небольшие колебания\n'
 ' Средний — умеренный риск\n'
 ' Высокий — портфель с высокой волатильностью\n'
 ' Помогает оценить потенциальные колебания стоимости ваших активов.\n\n'

'3️⃣ /top — топ активы и слабые активы\n'
 ' Показывает 5 лучших активов по росту и 5 наименее доходных активов.\n'
 ' Помогает выявить сильные стороны портфеля и те позиции, которые снижают доходность.\n\n'

'4️⃣ /sharpe — коэффициент Шарпа\n'
 ' Показывает соотношение доходности портфеля к его риску.\n'
 ' Чем выше коэффициент Шарпа, тем эффективнее портфель: больше доход при меньшем риске.\n'
 ' Позволяет сравнивать разные портфели между собой.\n\n'

'5️⃣ /tax — расчет налога на доход\n'
 ' Считает примерный налог 13% с прибыли по всем активам, включая рост стоимости и дивиденды/купоны.\n'
 ' Помогает оценить, сколько вы реально заработаете после уплаты налога.\n\n'

"💡 Советы по использованию:\n"
  "Сначала рассчитайте портфель через /income.\n"
  "Проверяйте диверсификацию и риск перед принятием инвестиционных решений.\n"
  "Используйте /top и /sharpe для оптимизации портфеля.\n"
  'С /tax удобно оценивать налоговую нагрузку на инвестиции.\n')

@router.message(Command('subscribe_description'))
async def subscribe_description_command(message: Message):
    await message.answer('Платная подписка дает возможность пользоваться расширенным функционалом бота. ' \
    'Все новые премиум-подписчики смогут вступить в закрытый чат с такими же энтузиастами в сфере инвестиций и технологий, а также общаться с автором канала и бота напрямую. ' \
    'Также есть возможность получить премиум-подписку через реферальную программу. ' \
    'Подробнее можно узнать в поддержке или в канале.')

@router.message(Command('disclaimer'))
async def disclaimer_command(message: Message):
    await message.answer("Бот не является инвестиционным консультантом."
    "Информация носит образовательный и аналитический характер и не является призывом к покупке или продаже активов.")
  

@router.message(Command('instruction'))
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
        "Фонды: ETF1:10:120:8, ETF2:5:100:6\n\n"
        "Дробные числа вводяться через точки. Пример: 3.14\n"
        "Названия активов не обязательны, но для удобства рекомендуем все же называть ваши активы.")

class IncomeStates(StatesGroup):
    waiting_assets = State()

# ====== /income ======
@router.message(Command("income"))
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
@router.message(IncomeStates.waiting_assets)
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

# ====== Рассчет итоговой суммы ======
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

# ====== ОПРЕДЕЛЕНИЕ ТИПА ПОРТФЕЛЯ ======
@router.message(Command("portfolio_type"))
async def portfolio_type(message: Message):
    user_id = message.from_user.id
    
    if user_id not in user_portfolios:
        return await message.answer("Сначала рассчитайте портфель через /income")

    portfolio = user_portfolios[user_id]

    total_sum = 0
    stocks_sum = 0

    # считаем сумму всех активов и сумму акций
    for category, assets in portfolio.items():
        for a in assets:
            total_sum += a["final_value"]
            if category == "Акции":
                stocks_sum += a["final_value"]

    if total_sum == 0:
        return await message.answer("Ошибка: сумма портфеля равна 0")

    stock_percent = (stocks_sum / total_sum) * 100

    # определяем тип портфеля
    if stock_percent > 75:
        ptype = "Агрессивный портфель. " \
        "Подходит для стратегий с повышенным уровнем риска."
    elif 50 < stock_percent <= 75:
        ptype = "Сбалансированный акционный портфель. " \
        "Подходит для инвесторов, предпочитающих баланс между рискованными акциями и защитными активами."
    elif 25 < stock_percent <= 50:
        ptype = "Защитный портфель с долей акций. " \
        "Подходит для инвесторов, желающих сохранить свои деньги, но при этом иметь в портфеле ускоряющие рост акции."
    else:
        ptype = "Защитный портфель. " \
        "Подходит для инвесторов, желающих получать небольшой доход от относительно безопасных активов и консервативных инструментов."

    await message.answer(
        f"📊 *Тип портфеля*: **{ptype}**\n"
        f"Доля акций(с учетом роста за 12 месяцев): {stock_percent:.2f}%"
        , parse_mode="Markdown"
    )


# ====== ПРОВЕРКА ДИВЕРСИФИКАЦИИ ПОРТФЕЛЯ ======
@router.message(Command("diversification"))
async def diversification(message: Message):
    user_id = message.from_user.id
    premium_users = load_premium_users()

    if user_id not in premium_users:
        return await message.answer("⛔ Эта функция доступна только премиум-пользователям.")

    if user_id not in user_portfolios:
        return await message.answer("Сначала рассчитайте портфель через /income")

    portfolio = user_portfolios[user_id]
    stocks = portfolio.get("Акции", [])

    if not stocks:
        return await message.answer("В вашем портфеле нет акций, диверсификация не требуется.")

    total_stocks_sum = sum(a["final_value"] for a in stocks)

    warning_list = []

    for a in stocks:
        percent = (a["final_value"] / total_stocks_sum) * 100
        if percent > 30:
            name = a["name"] if a["name"] else "Без названия"
            warning_list.append(f"⚠ Актив {name} занимает {percent:.1f}% от всех акций")

    if not warning_list:
        return await message.answer("✅ Портфель диверсифицирован. Ни один актив не превышает 30%(с учетом роста за 12 месяцев).")

    warnings = "\n".join(warning_list)
    await message.answer(f"❗ Портфель НЕ диверсифицирован(с учетом роста за 12 месяцев):\n{warnings}")




# ====== 1. /tax — расчёт налога ======
@router.message(Command("tax"))
async def tax_cmd(message: Message):
    user_id = message.from_user.id
    premium_users = load_premium_users()

    if user_id not in premium_users:
        return await message.answer("❌ Эта функция доступна только для платных подписчиков.")

    if user_id not in user_portfolios:
        return await message.answer("Сначала рассчитайте портфель через /income")

    portfolio = user_portfolios[user_id]
    total_tax = 0.0
    tax_rate = 13 / 100  # Налог 13%

    for category, assets in portfolio.items():
        for asset in assets:
            qty = asset.get("quantity", 0)
            price = asset.get("price", 0)
            growth = asset.get("growth", 0)
            div = asset.get("dividend", 0)

            profit = qty * price * (growth / 100) + qty * div
            total_tax += profit * tax_rate

    await message.answer(f"💰 Примерный налог с дохода портфеля: {total_tax:.2f} ₽")


# ====== 2. /risk — риск портфеля ======
@router.message(Command("risk"))
async def risk_cmd(message: Message):
    user_id = message.from_user.id
    premium_users = load_premium_users()

    if user_id not in premium_users:
        return await message.answer("❌ Эта функция доступна только для платных подписчиков.")

    if user_id not in user_portfolios:
        return await message.answer("Сначала рассчитайте портфель через /income")

    import statistics

    portfolio = user_portfolios[user_id]

    # собираем финальные стоимости всех активов
    all_values = []
    for assets in portfolio.values():
        for a in assets:
            all_values.append(a["final_value"])

    if len(all_values) < 2:
        return await message.answer("Недостаточно данных для расчёта риска")

    # стандартное отклонение
    std_dev = statistics.stdev(all_values)

    # относительный риск в процентах
    mean_value = statistics.mean(all_values)
    relative_risk = (std_dev / mean_value) * 100

    # определяем категорию риска
    if relative_risk < 10:
        risk_level = "Низкий"
    elif relative_risk < 25:
        risk_level = "Средний"
    else:
        risk_level = "Высокий"

    await message.answer(
        f"📉 Риск портфеля:\n"
        f"• Стандартное отклонение: {std_dev:.2f}\n"
        f"• Относительный риск: {relative_risk:.2f}%\n"
        f"• Уровень риска: {risk_level}"
    )

# ====== 3. /sharpe — коэффициент Шарпа ======
@router.message(Command("sharpe"))
async def sharpe_cmd(message: Message):
    user_id = message.from_user.id

    premium_users = load_premium_users()

    if user_id not in premium_users:
        return await message.answer("⛔ Эта функция доступна только премиум-пользователям.")

    if user_id not in user_portfolios:
        return await message.answer("❗ Сначала добавьте портфель через /income.")

    portfolio = user_portfolios[user_id]

    growths = []
    for category in portfolio.values():
        for asset in category:
            growths.append(asset["growth"])

    if len(growths) < 2:
        return await message.answer("Для Шарпа нужно минимум 2 актива.")

    mean = sum(growths) / len(growths)
    variance = sum((g - mean) ** 2 for g in growths) / len(growths)
    std = variance ** 0.5

    if std == 0:
        return await message.answer("Коэффициент Шарпа = ∞ (риск близок к нулю).")

    sharpe = mean / std

    await message.answer(
        f"📈 *Коэффициент Шарпа:* {sharpe:.3f}",
        parse_mode="Markdown"
    )


# ====== 4. /top — лучшие и худшие активы ======
@router.message(Command("top"))
async def top_cmd(message: Message):
    user_id = message.from_user.id
    premium_users = load_premium_users()

    if user_id not in premium_users:
        return await message.answer("❌ Эта функция доступна только для платных подписчиков.")

    if user_id not in user_portfolios:
        return await message.answer("Сначала рассчитайте портфель через /income")

    portfolio = user_portfolios[user_id]
    all_assets = []

    # Собираем все активы в один список
    for category, assets in portfolio.items():
        for a in assets:
            all_assets.append({
                "name": a.get("name", "Без названия"),
                "final_value": a["final_value"]
            })

    if not all_assets:
        return await message.answer("В вашем портфеле нет активов.")

    total_value = sum(a["final_value"] for a in all_assets)
    
    # Сортировка топовых и слабых активов
    top_assets = sorted(all_assets, key=lambda x: x["final_value"], reverse=True)[:5]
    weak_assets = sorted(all_assets, key=lambda x: x["final_value"])[:5]

    # Формируем текст
    msg = "🏆 Топ активы:\n"
    for a in top_assets:
        percent = (a["final_value"] / total_value) * 100
        msg += f"• {a['name']} — {percent:.1f}%\n"

    msg += "\n⚠️ Самые слабые активы:\n"
    for a in weak_assets:
        percent = (a["final_value"] / total_value) * 100
        msg += f"• {a['name']} — {percent:.1f}%\n"

    await message.answer(msg)


# ====== Запуск бота ======
async def main():
    print("active")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())