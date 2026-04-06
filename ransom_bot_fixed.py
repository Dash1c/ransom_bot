import json
import os
import asyncio
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8658698050:AAGL2QE7LS_RfEHM1ZwvLOoQ4Xg_Xxjt_Zk"
ALLOWED_USERS = [651953211, 1901955703, 1793833215]

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DATA_FILE = "/app/data/ransom_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"clients": {}, "blacklist": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# States
class AddPurchase(StatesGroup):
    fio = State()
    frame_number = State()
    phone = State()
    total_amount = State()
    weeks = State()
    first_payment = State()
    first_payment_days = State()

class MakePayment(StatesGroup):
    amount = State()
    days = State()

class RemoveFromBlacklist(StatesGroup):
    amount = State()
    days = State()

# Главное меню
def main_keyboard():
    kb = [
        [KeyboardButton(text="➕ Добавить выкуп")],
        [KeyboardButton(text="📋 Список всех выкупов")],
        [KeyboardButton(text="⏳ Ожидают решения")],
        [KeyboardButton(text="⛔ Чёрный список (ЧС)")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Клавиатура только с кнопкой "Назад"
def back_keyboard():
    kb = [[KeyboardButton(text="🔙 Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def active_clients_keyboard():
    data = load_data()
    kb = []
    today = datetime.now().date()
    for cid, client in data["clients"].items():
        if client.get("in_blacklist"):
            continue
        deadline_date = datetime.fromisoformat(client["deadline"]).date()
        if deadline_date > today:
            kb.append([InlineKeyboardButton(text=client["fio"], callback_data=f"active_{cid}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def pending_clients_keyboard():
    data = load_data()
    kb = []
    today = datetime.now().date()
    for cid, client in data["clients"].items():
        if client.get("in_blacklist"):
            continue
        deadline_date = datetime.fromisoformat(client["deadline"]).date()
        notified = client.get("notified", False)
        if deadline_date <= today and notified:
            kb.append([InlineKeyboardButton(text=client["fio"], callback_data=f"pending_{cid}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def blacklist_keyboard():
    data = load_data()
    kb = []
    for bid, bl_entry in data["blacklist"].items():
        kb.append([InlineKeyboardButton(text=bl_entry["fio"], callback_data=f"bl_{bid}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def client_detail_keyboard(client_id, is_pending=False):
    if is_pending:
        kb = [
            [InlineKeyboardButton(text="💰 Внести оплату", callback_data=f"pay_pending_{client_id}")],
            [InlineKeyboardButton(text="🚫 В ЧС", callback_data=f"to_blacklist_{client_id}")]
        ]
    else:
        kb = [
            [InlineKeyboardButton(text="💰 Внести оплату", callback_data=f"pay_active_{client_id}")],
            [InlineKeyboardButton(text="🚫 В ЧС", callback_data=f"to_blacklist_{client_id}")]
        ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def blacklist_detail_keyboard(blacklist_id):
    kb = [
        [InlineKeyboardButton(text="✅ Убрать из ЧС", callback_data=f"unblack_{blacklist_id}")],
        [InlineKeyboardButton(text="🗑 Удалить навсегда", callback_data=f"del_black_{blacklist_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        await message.answer("❌ Доступ запрещён.")
        return
    await message.answer("👋 Привет! Выбери действие:", reply_markup=main_keyboard())

@dp.message(F.text == "🔙 Назад")
async def go_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔙 Возврат в главное меню.", reply_markup=main_keyboard())

@dp.message(F.text == "➕ Добавить выкуп")
async def add_purchase_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ALLOWED_USERS:
        return
    await state.clear()
    await message.answer("📝 Введите ФИО клиента:", reply_markup=back_keyboard())
    await state.set_state(AddPurchase.fio)

@dp.message(AddPurchase.fio)
async def add_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer("🔢 Введите номер рамы:", reply_markup=back_keyboard())
    await state.set_state(AddPurchase.frame_number)

@dp.message(AddPurchase.frame_number)
async def add_frame(message: types.Message, state: FSMContext):
    await state.update_data(frame_number=message.text)
    await message.answer("📞 Введите номер телефона клиента:", reply_markup=back_keyboard())
    await state.set_state(AddPurchase.phone)

@dp.message(AddPurchase.phone)
async def add_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("💰 Введите общую сумму выкупа (в рублях):", reply_markup=back_keyboard())
    await state.set_state(AddPurchase.total_amount)

@dp.message(AddPurchase.total_amount)
async def add_total(message: types.Message, state: FSMContext):
    try:
        await state.update_data(total_amount=int(message.text))
        await message.answer("📅 Введите срок выкупа (в НЕДЕЛЯХ):", reply_markup=back_keyboard())
        await state.set_state(AddPurchase.weeks)
    except ValueError:
        await message.answer("❌ Введите число! Сколько рублей?", reply_markup=back_keyboard())

@dp.message(AddPurchase.weeks)
async def add_weeks(message: types.Message, state: FSMContext):
    try:
        await state.update_data(weeks=int(message.text))
        await message.answer("💵 Введите сумму первого взноса:", reply_markup=back_keyboard())
        await state.set_state(AddPurchase.first_payment)
    except ValueError:
        await message.answer("❌ Введите число! Сколько недель?", reply_markup=back_keyboard())

@dp.message(AddPurchase.first_payment)
async def add_first_payment(message: types.Message, state: FSMContext):
    try:
        await state.update_data(first_payment=int(message.text))
        await message.answer("📆 На сколько дней хватит первого взноса?", reply_markup=back_keyboard())
        await state.set_state(AddPurchase.first_payment_days)
    except ValueError:
        await message.answer("❌ Введите число! Сумма первого взноса?", reply_markup=back_keyboard())

@dp.message(AddPurchase.first_payment_days)
async def add_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
        user_data = await state.update_data(first_payment_days=days)
        user_data = await state.get_data()
        
        client_id = f"client_{int(datetime.now().timestamp())}"
        deadline = datetime.now() + timedelta(days=user_data["first_payment_days"])
        
        new_client = {
            "fio": user_data["fio"],
            "frame_number": user_data["frame_number"],
            "phone": user_data["phone"],
            "total_amount": user_data["total_amount"],
            "weeks": user_data["weeks"],
            "first_payment": user_data["first_payment"],
            "first_payment_days": user_data["first_payment_days"],
            "paid": user_data["first_payment"],
            "deadline": deadline.isoformat(),
            "in_blacklist": False,
            "notified": False,
            "created_at": datetime.now().isoformat()
        }
        
        db = load_data()
        db["clients"][client_id] = new_client
        save_data(db)
        
        await message.answer(
            f"✅ Клиент {user_data['fio']} добавлен!\n📅 Следующая дата оплаты: {deadline.strftime('%Y-%m-%d')}",
            reply_markup=main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число! На сколько дней?", reply_markup=back_keyboard())

@dp.message(F.text == "📋 Список всех выкупов")
async def list_active_purchases(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    kb = active_clients_keyboard()
    if not kb.inline_keyboard:
        await message.answer("📭 Активных выкупов нет.", reply_markup=main_keyboard())
    else:
        await message.answer("📋 Активные выкупы:", reply_markup=kb)

@dp.message(F.text == "⏳ Ожидают решения")
async def list_pending(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    kb = pending_clients_keyboard()
    if not kb.inline_keyboard:
        await message.answer("✅ Нет клиентов, ожидающих решения.", reply_markup=main_keyboard())
    else:
        await message.answer("⏳ Клиенты с истекшим сроком:", reply_markup=kb)

@dp.message(F.text == "⛔ Чёрный список (ЧС)")
async def show_blacklist(message: types.Message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    kb = blacklist_keyboard()
    if not kb.inline_keyboard:
        await message.answer("📭 ЧС пуст.", reply_markup=main_keyboard())
    else:
        await message.answer("⛔ Клиенты в ЧС:", reply_markup=kb)

@dp.callback_query(F.data.startswith("active_"))
async def show_active_client(callback: types.CallbackQuery):
    client_id = callback.data.split("_", 1)[1]
    db = load_data()
    client = db["clients"].get(client_id)
    if not client or client.get("in_blacklist"):
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return
    
    paid = client["paid"]
    total = client["total_amount"]
    remaining = total - paid
    deadline_date = datetime.fromisoformat(client["deadline"]).date()
    text = (
        f"👤 ФИО: {client['fio']}\n"
        f"🔢 Номер рамы: {client['frame_number']}\n"
        f"📞 Телефон: {client['phone']}\n"
        f"💰 Выкуп: {paid}/{total} руб.\n"
        f"📉 Осталось: {remaining} руб.\n"
        f"📅 Дедлайн: {deadline_date}"
    )
    await callback.message.edit_text(text, reply_markup=client_detail_keyboard(client_id, is_pending=False))
    await callback.answer()

@dp.callback_query(F.data.startswith("pending_"))
async def show_pending_client(callback: types.CallbackQuery):
    client_id = callback.data.split("_", 1)[1]
    db = load_data()
    client = db["clients"].get(client_id)
    if not client or client.get("in_blacklist"):
        await callback.answer("❌ Клиент не найден", show_alert=True)
        return
    
    paid = client["paid"]
    total = client["total_amount"]
    remaining = total - paid
    deadline_date = datetime.fromisoformat(client["deadline"]).date()
    text = (
        f"⚠️ ПРОСРОЧКА!\n\n"
        f"👤 ФИО: {client['fio']}\n"
        f"🔢 Рама: {client['frame_number']}\n"
        f"📞 Телефон: {client['phone']}\n"
        f"💰 Оплачено: {paid}/{total} руб.\n"
        f"📉 Осталось: {remaining} руб.\n"
        f"📅 Дедлайн истёк: {deadline_date}"
    )
    await callback.message.edit_text(text, reply_markup=client_detail_keyboard(client_id, is_pending=True))
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_active_"))
async def start_payment_active(callback: types.CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 2)[2]
    await state.update_data(client_id=client_id)
    await callback.message.answer("💵 Введите сумму:", reply_markup=back_keyboard())
    await state.set_state(MakePayment.amount)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_pending_"))
async def start_payment_pending(callback: types.CallbackQuery, state: FSMContext):
    client_id = callback.data.split("_", 2)[2]
    await state.update_data(client_id=client_id)
    await callback.message.answer("💵 Введите сумму:", reply_markup=back_keyboard())
    await state.set_state(MakePayment.amount)
    await callback.answer()

@dp.message(MakePayment.amount)
async def process_payment_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        await state.update_data(payment_amount=amount)
        await message.answer("📆 На сколько дней хватит?", reply_markup=back_keyboard())
        await state.set_state(MakePayment.days)
    except ValueError:
        await message.answer("❌ Введите число!", reply_markup=back_keyboard())

@dp.message(MakePayment.days)
async def process_payment_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
        data = await state.get_data()
        client_id = data["client_id"]
        payment_amount = data["payment_amount"]
        
        db = load_data()
        client = db["clients"].get(client_id)
        if not client:
            await message.answer("❌ Клиент не найден", reply_markup=main_keyboard())
            await state.clear()
            return
        
        client["paid"] += payment_amount
        new_deadline = datetime.now() + timedelta(days=days)
        client["deadline"] = new_deadline.isoformat()
        client["notified"] = False
        
        if client["paid"] >= client["total_amount"]:
            fio = client["fio"]
            total_amount = client["total_amount"]
            del db["clients"][client_id]
            save_data(db)
            await message.answer(f"🎉 ВЫКУП ЗАВЕРШЁН! {fio} полностью выплатил {total_amount} руб.", reply_markup=main_keyboard())
            await state.clear()
            return
        
        save_data(db)
        
        remaining = client["total_amount"] - client["paid"]
        await message.answer(
            f"✅ Принято {payment_amount} руб.\n💰 Осталось: {remaining} руб.\n📅 Новый дедлайн: {new_deadline.strftime('%Y-%m-%d')}",
            reply_markup=main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число дней!", reply_markup=back_keyboard())

@dp.callback_query(F.data.startswith("to_blacklist_"))
async def add_to_blacklist(callback: types.CallbackQuery):
    client_id = callback.data.split("_", 2)[2]
    db = load_data()
    client = db["clients"].get(client_id)
    
    if not client:
        await callback.answer("❌ Клиент не найден")
        return
    
    bl_entry = {
        "fio": client["fio"],
        "phone": client["phone"],
        "frame_number": client["frame_number"],
        "total_amount": client["total_amount"],
        "paid": client["paid"],
        "removed_at": datetime.now().isoformat()
    }
    db["blacklist"][client_id] = bl_entry
    del db["clients"][client_id]
    save_data(db)
    
    await callback.message.edit_text(f"🚫 {bl_entry['fio']} добавлен в ЧС.")
    await callback.answer()

@dp.callback_query(F.data.startswith("bl_"))
async def show_blacklist_entry(callback: types.CallbackQuery):
    blacklist_id = callback.data.split("_", 1)[1]
    db = load_data()
    entry = db["blacklist"].get(blacklist_id)
    
    if not entry:
        await callback.answer("❌ Запись не найдена")
        return
    
    text = (
        f"👤 ФИО: {entry['fio']}\n"
        f"📞 Телефон: {entry['phone']}\n"
        f"🔢 Рама: {entry['frame_number']}\n"
        f"💰 Успел оплатить: {entry['paid']}/{entry['total_amount']} руб.\n"
        f"🗓 Добавлен в ЧС: {entry['removed_at'][:10]}"
    )
    await callback.message.edit_text(text, reply_markup=blacklist_detail_keyboard(blacklist_id))
    await callback.answer()

@dp.callback_query(F.data.startswith("unblack_"))
async def unblacklist(callback: types.CallbackQuery, state: FSMContext):
    blacklist_id = callback.data.split("_", 1)[1]
    await state.update_data(blacklist_id=blacklist_id)
    await callback.message.answer("💰 Введите сумму для возврата из ЧС:", reply_markup=back_keyboard())
    await state.set_state(RemoveFromBlacklist.amount)
    await callback.answer()

@dp.message(RemoveFromBlacklist.amount)
async def unblacklist_amount(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text)
        await state.update_data(amount=amount)
        await message.answer("📆 На сколько дней хватит?", reply_markup=back_keyboard())
        await state.set_state(RemoveFromBlacklist.days)
    except ValueError:
        await message.answer("❌ Введите число!", reply_markup=back_keyboard())

@dp.message(RemoveFromBlacklist.days)
async def unblacklist_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
        data = await state.get_data()
        blacklist_id = data["blacklist_id"]
        amount = data["amount"]
        
        db = load_data()
        bl_entry = db["blacklist"].pop(blacklist_id, None)
        
        if not bl_entry:
            await message.answer("❌ Запись не найдена", reply_markup=main_keyboard())
            await state.clear()
            return
        
        deadline = datetime.now() + timedelta(days=days)
        client = {
            "fio": bl_entry["fio"],
            "phone": bl_entry["phone"],
            "frame_number": bl_entry["frame_number"],
            "total_amount": bl_entry["total_amount"],
            "paid": amount,
            "deadline": deadline.isoformat(),
            "in_blacklist": False,
            "notified": False,
            "created_at": datetime.now().isoformat(),
            "first_payment": amount,
            "first_payment_days": days,
            "weeks": 0
        }
        db["clients"][blacklist_id] = client
        save_data(db)
        
        remaining = bl_entry["total_amount"] - amount
        await message.answer(
            f"✅ {bl_entry['fio']} возвращён из ЧС!\n💰 Внесено: {amount} руб.\n📉 Осталось: {remaining} руб.\n📅 Новый дедлайн: {deadline.strftime('%Y-%m-%d')}",
            reply_markup=main_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число дней!", reply_markup=back_keyboard())

@dp.callback_query(F.data.startswith("del_black_"))
async def delete_blacklist_entry(callback: types.CallbackQuery):
    blacklist_id = callback.data.split("_", 2)[2]
    db = load_data()
    
    if blacklist_id in db["blacklist"]:
        fio = db["blacklist"][blacklist_id]["fio"]
        del db["blacklist"][blacklist_id]
        save_data(db)
        await callback.message.edit_text(f"🗑 {fio} удалён из ЧС навсегда.")
    else:
        await callback.answer("❌ Запись не найдена")
    await callback.answer()

from datetime import datetime, timedelta, timezone

async def check_deadlines():
    # Создаём московский часовой пояс (UTC+3)
    MOSCOW_TZ = timezone(timedelta(hours=3))
    
    while True:
        # Берём текущее время по Москве
        now_moscow = datetime.now(MOSCOW_TZ)
        
        # Следующий запуск в 20:00 по Москве
        next_run = now_moscow.replace(hour=20, minute=0, second=0, microsecond=0)
        if now_moscow >= next_run:
            next_run += timedelta(days=1)
        
        wait_seconds = (next_run - now_moscow).total_seconds()
        await asyncio.sleep(wait_seconds)
        
        db = load_data()
        # Сегодняшняя дата по Москве
        today = now_moscow.date()
        
        for user_id in ALLOWED_USERS:
            for cid, client in db["clients"].items():
                if client.get("in_blacklist"):
                    continue
                
                # Дедлайн из JSON — нужно тоже перевести в московскую дату для сравнения
                deadline_date = datetime.fromisoformat(client["deadline"]).date()
                
                # Сравниваем с московской датой
                if deadline_date == today and not client.get("notified", False):
                    paid = client["paid"]
                    total = client["total_amount"]
                    remaining = total - paid
                    text = (
                        f"⚠️ СЕГОДНЯ ДЕНЬ ОПЛАТЫ!\n\n"
                        f"👤 Клиент: {client['fio']}\n"
                        f"📞 Телефон: {client['phone']}\n"
                        f"💰 Долг: {remaining} руб. (всего {total} руб.)\n"
                        f"📅 Дедлайн: {client['deadline'][:10]}"
                    )
                    kb = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="💰 Внести оплату", callback_data=f"pay_pending_{cid}")],
                        [InlineKeyboardButton(text="🚫 В ЧС", callback_data=f"to_blacklist_{cid}")]
                    ])
                    await bot.send_message(user_id, text, reply_markup=kb)
                    
                    client["notified"] = True
                    save_data(db)

async def main():
    asyncio.create_task(check_deadlines())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())