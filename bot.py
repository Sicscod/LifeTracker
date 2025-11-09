import os
import json
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DATA_FILE = "finance_data.json"

INCOME_CATEGORIES = ["Зарплата", "Подарки", "Подработка", "Инвестиции", "Другое"]
EXPENSE_CATEGORIES = ["Еда", "Транспорт", "Развлечения", "Одежда", "Коммунальные", "Другое"]

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить доход")],
        [KeyboardButton(text="Добавить расход")],
        [KeyboardButton(text="Показать статистику")],
    ],
    resize_keyboard=True
)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f, ensure_ascii=False, indent=4)

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

class IncomeStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()

class ExpenseStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_amount = State()

class StatsStates(StatesGroup):
    waiting_for_period = State()

# ---------- START ----------
@dp.message(Command("start"))
async def start(message: types.Message):
    data = load_data()
    user_id = str(message.from_user.id)
    income_total = sum(item.get("amount", 0) for item in data.get(user_id, {}).get("income", []))
    expense_total = sum(item.get("amount", 0) for item in data.get(user_id, {}).get("expenses", []))
    balance = income_total - expense_total

    balance_text = f"Ваш текущий баланс: {balance:.2f} ₸\n\n" if balance >= 0 else f"Вы в долгу: {balance:.2f} ₸\n\n"

    await message.answer(
        f"{balance_text}Привет! Я твой финансовый помощник.\n"
        "Ты можешь добавлять доходы, расходы и смотреть статистику по категориям.",
        reply_markup=main_kb
    )


# ---------- ДОХОД ----------
@dp.message(lambda m: m.text == "Добавить доход")
async def add_income_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in INCOME_CATEGORIES],
        resize_keyboard=True
    )
    await message.answer("Выбери категорию дохода:", reply_markup=kb)
    await state.set_state(IncomeStates.waiting_for_category)

@dp.message(IncomeStates.waiting_for_category)
async def add_income_category(message: types.Message, state: FSMContext):
    if message.text not in INCOME_CATEGORIES:
        await message.answer("Выберите категорию из списка!")
        return
    await state.update_data(category=message.text)
    await message.answer("Введите сумму дохода:")
    await state.set_state(IncomeStates.waiting_for_amount)

@dp.message(IncomeStates.waiting_for_amount)
async def add_income_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = load_data()
        user_id = str(message.from_user.id)
        if user_id not in data:
            data[user_id] = {"income": [], "expenses": []}
        user_data = await state.get_data()
        category = user_data["category"]
        data[user_id]["income"].append({
            "category": category,
            "amount": amount,
            "date": datetime.now().isoformat()
        })
        save_data(data)
        await message.answer(f"Доход в {amount:.2f} ₸ добавлен в категорию {category}.", reply_markup=main_kb)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

# ---------- РАСХОД ----------
@dp.message(lambda m: m.text == "Добавить расход")
async def add_expense_start(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in EXPENSE_CATEGORIES],
        resize_keyboard=True
    )
    await message.answer("Выбери категорию расхода:", reply_markup=kb)
    await state.set_state(ExpenseStates.waiting_for_category)

@dp.message(ExpenseStates.waiting_for_category)
async def add_expense_category(message: types.Message, state: FSMContext):
    if message.text not in EXPENSE_CATEGORIES:
        await message.answer("Выберите категорию из списка!")
        return
    await state.update_data(category=message.text)
    await message.answer("Введите сумму расхода:")
    await state.set_state(ExpenseStates.waiting_for_amount)

@dp.message(ExpenseStates.waiting_for_amount)
async def add_expense_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = load_data()
        user_id = str(message.from_user.id)
        if user_id not in data:
            data[user_id] = {"income": [], "expenses": []}
        user_data = await state.get_data()
        category = user_data["category"]
        data[user_id]["expenses"].append({
            "category": category,
            "amount": amount,
            "date": datetime.now().isoformat()
        })
        save_data(data)
        await message.answer(f"Расход в {amount:.2f} ₸ добавлен в категорию {category}.", reply_markup=main_kb)
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число!")

# ---------- СТАТИСТИКА ----------
@dp.message(lambda m: m.text == "Показать статистику")
async def choose_period(message: types.Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="За неделю")],
            [KeyboardButton(text="За месяц")],
            [KeyboardButton(text="За год")],
        ],
        resize_keyboard=True
    )
    await message.answer("Выбери период для статистики:", reply_markup=kb)
    await state.set_state(StatsStates.waiting_for_period)

@dp.message(StatsStates.waiting_for_period)
async def show_statistics(message: types.Message, state: FSMContext):
    period_text = message.text
    now = datetime.now()
    
    if period_text == "За неделю":
        start_date = now - timedelta(days=7)
    elif period_text == "За месяц":
        start_date = now - timedelta(days=30)
    elif period_text == "За год":
        start_date = now - timedelta(days=365)
    else:
        await message.answer("Выберите один из предложенных периодов!")
        return

    data = load_data()
    user_id = str(message.from_user.id)
    if user_id not in data or (not data[user_id]["income"] and not data[user_id]["expenses"]):
        await message.answer("Нет данных для отображения.", reply_markup=main_kb)
        await state.clear()
        return

    text = f"📊 Статистика за {period_text}:\n\n"

    # Доходы
    income_total = sum(
        item.get("amount", 0) for item in data[user_id]["income"]
        if item.get("date") and datetime.fromisoformat(item["date"]) >= start_date
    )
    text += "💰 Доходы:\n"
    for cat in INCOME_CATEGORIES:
        cat_sum = sum(
            item.get("amount", 0) for item in data[user_id]["income"]
            if item.get("category") == cat and item.get("date") and datetime.fromisoformat(item["date"]) >= start_date
        )
        text += f"{cat}: {cat_sum:.2f} ₸\n"
    text += f"Итого: {income_total:.2f} ₸\n\n"

    # Расходы
    expense_total = sum(
        item.get("amount", 0) for item in data[user_id]["expenses"]
        if item.get("date") and datetime.fromisoformat(item["date"]) >= start_date
    )
    text += "🛒 Расходы:\n"
    for cat in EXPENSE_CATEGORIES:
        cat_sum = sum(
            item.get("amount", 0) for item in data[user_id]["expenses"]
            if item.get("category") == cat and item.get("date") and datetime.fromisoformat(item["date"]) >= start_date
        )
        text += f"{cat}: {cat_sum:.2f} ₸\n"
    text += f"Итого: {expense_total:.2f} ₸\n\n"

    text += f"Баланс: {income_total - expense_total:.2f} ₸"

    await message.answer(text, reply_markup=main_kb)
    await state.clear()

# ---------- RUN ----------
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
