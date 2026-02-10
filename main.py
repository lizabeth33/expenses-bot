import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from db import (
    init_db,
    add_expense,
    get_stats,
    get_balance,
    set_balance,
    add_to_balance,
)

import os

bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())


# ---------- STATES ----------
class ExpenseState(StatesGroup):
    category = State()
    amount = State()


class BalanceState(StatesGroup):
    action = State()
    amount = State()


class StatsState(StatesGroup):
    days = State()


# ---------- CATEGORIES ----------
CATEGORIES = {
    "🏠 Дом": "Дом",
    "🍔 Еда": "Еда",
    "🏡 Аренда жилья": "Аренда жилья",
    "🚗 Транспорт": "Транспорт",
    "💼 Работа": "Работа",
    "💻 Техника": "Техника",
    "🐾 Животные": "Животные",
    "🛂 Виза": "Виза",
}


# ---------- MENUS ----------
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Расход")],
            [KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="💰 Баланс")],
        ],
        resize_keyboard=True,
    )


def categories_menu():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=k)] for k in CATEGORIES.keys()],
        resize_keyboard=True,
    )


def balance_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить к балансу")],
            [KeyboardButton(text="🔄 Новый баланс")],
        ],
        resize_keyboard=True,
    )


# ---------- START ----------
@dp.message(Command("start"))
async def start(message: Message):
    bal = get_balance(message.from_user.id)
    await message.answer(
        f"Привет 👋\nТекущий баланс: {bal:.2f}",
        reply_markup=main_menu(),
    )


# ---------- ADD EXPENSE ----------
@dp.message(F.text == "➕ Расход")
async def expense_start(message: Message, state: FSMContext):
    await state.set_state(ExpenseState.category)
    await message.answer("Выбери категорию:", reply_markup=categories_menu())


@dp.message(ExpenseState.category)
async def expense_category(message: Message, state: FSMContext):
    if message.text not in CATEGORIES:
        await message.answer("Выбери категорию кнопкой.")
        return

    await state.update_data(category=CATEGORIES[message.text])
    await state.set_state(ExpenseState.amount)
    await message.answer("Введи сумму:")


@dp.message(ExpenseState.amount)
async def expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except:
        await message.answer("Введи число.")
        return

    data = await state.get_data()
    user_id = message.from_user.id

    add_expense(user_id, amount, data["category"])
    add_to_balance(user_id, -amount)

    bal = get_balance(user_id)

    await message.answer(
        f"✅ Расход добавлен\nБаланс: {bal:.2f}",
        reply_markup=main_menu(),
    )
    await state.clear()


# ---------- BALANCE ----------
@dp.message(F.text == "💰 Баланс")
async def balance_start(message: Message, state: FSMContext):
    bal = get_balance(message.from_user.id)
    await state.set_state(BalanceState.action)
    await message.answer(
        f"Баланс: {bal:.2f}\nВыбери действие:",
        reply_markup=balance_menu(),
    )


@dp.message(BalanceState.action)
async def balance_action(message: Message, state: FSMContext):
    if message.text not in ["➕ Добавить к балансу", "🔄 Новый баланс"]:
        await message.answer("Выбери кнопку.")
        return

    await state.update_data(action=message.text)
    await state.set_state(BalanceState.amount)
    await message.answer("Введи сумму:")


@dp.message(BalanceState.amount)
async def balance_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
    except:
        await message.answer("Введи число.")
        return

    data = await state.get_data()
    user_id = message.from_user.id

    if data["action"] == "➕ Добавить к балансу":
        add_to_balance(user_id, amount)
    else:
        set_balance(user_id, amount)

    bal = get_balance(user_id)

    await message.answer(
        f"💰 Баланс обновлён: {bal:.2f}",
        reply_markup=main_menu(),
    )
    await state.clear()


# ---------- STATS ----------
@dp.message(F.text == "📊 Статистика")
async def stats_start(message: Message, state: FSMContext):
    await state.set_state(StatsState.days)
    await message.answer("За сколько дней показать статистику? (например 7)")


@dp.message(StatsState.days)
async def stats_show(message: Message, state: FSMContext):
    try:
        days = int(message.text)
    except:
        await message.answer("Введи число дней.")
        return

    stats = get_stats(message.from_user.id, days)

    if not stats:
        await message.answer("Нет данных за этот период.")
        await state.clear()
        return

    total = sum(stats.values())
    text = f"📊 Статистика за {days} дней\n\nИтого: {total:.2f}\n\n"

    for cat, amount in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        percent = (amount / total) * 100
        bars = "█" * int(percent / 5)
        text += f"{cat}: {amount:.2f} ({percent:.1f}%)\n{bars}\n\n"

    await message.answer(text, reply_markup=main_menu())
    await state.clear()


# ---------- RUN ----------
async def main():
    init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":

    asyncio.run(main())
