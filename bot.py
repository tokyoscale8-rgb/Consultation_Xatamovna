[05.03.2026 15:25] Admiral: #!/usr/bin/env python3

# -*- coding: utf-8 -*-

# “””
Shifokor uchun Telegram Bot - Bemor qabul eslatmalari

O’rnatish va ishga tushirish bo’yicha ko’rsatmalar pastda.
“””

import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
Application, CommandHandler, CallbackQueryHandler,
MessageHandler, filters, ContextTypes, ConversationHandler
)

# ============================================================

# ⚙️  SOZLAMALAR — faqat shu qismni o’zgartiring

# ============================================================

BOT_TOKEN = “8603255120:AAFrLdxfv1uoPUzCGHh0w4ZQG0tmwMiRIUI”   # @BotFather dan olingan token
DOCTOR_CHAT_ID = None   # Birinchi /start bosganda avtomatik to’ldiriladi

# ============================================================

logging.basicConfig(
format=”%(asctime)s - %(name)s - %(levelname)s - %(message)s”,
level=logging.INFO
)
logger = logging.getLogger(**name**)

# Conversation holatlari

(ASK_NAME, ASK_PHONE, ASK_DATE, ASK_TIME, ASK_NOTE, CONFIRM) = range(6)

# Bemorlar bazasi (xotira ichida; bot to’xtaganda saqlanmaydi)

# Doimiy saqlash uchun SQLite versiyasi ham qo’shilgan — pastga qarang

appointments = {}   # { id: { name, phone, date, time, note, reminded_1d, reminded_2h } }
next_id = 1

# ─────────────────────────────────────────────

# Yordamchi funksiyalar

# ─────────────────────────────────────────────

def get_appointment_text(ap: dict, show_id: bool = False) -> str:
lines = []
if show_id:
lines.append(f”🔢 ID: {ap[‘id’]}”)
lines += [
f”👤 Ism: {ap[‘name’]}”,
f”📞 Telefon: {ap[‘phone’]}”,
f”📅 Sana: {ap[‘date’]}”,
f”🕐 Vaqt: {ap[‘time’]}”,
]
if ap.get(“note”):
lines.append(f”📝 Izoh: {ap[‘note’]}”)
return “\n”.join(lines)

def main_menu_keyboard():
return InlineKeyboardMarkup([
[InlineKeyboardButton(“➕ Yangi bemor qo’shish”, callback_data=“add”)],
[InlineKeyboardButton(“📋 Barcha bemorlar”, callback_data=“list”)],
[InlineKeyboardButton(“📅 Bugungi qabullar”, callback_data=“today”)],
[InlineKeyboardButton(“🗑️ Bemor o’chirish”, callback_data=“delete_start”)],
])

# ─────────────────────────────────────────────

# /start

# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
global DOCTOR_CHAT_ID
DOCTOR_CHAT_ID = update.effective_chat.id   # faqat shifokor ishlatadi
await update.message.reply_text(
    "👨‍⚕️ *Shifokor qabul boti*\n\n"
    "Assalomu alaykum! Bemorlarni boshqarish uchun quyidagi menyudan foydalaning:",
    parse_mode="Markdown",
    reply_markup=main_menu_keyboard()
)

# ─────────────────────────────────────────────

# Bemor qo’shish — ConversationHandler

# ─────────────────────────────────────────────

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
await query.message.reply_text(“👤 Bemor ismini kiriting (To’liq ism):”)
return ASK_NAME

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[“name”] = update.message.text.strip()
await update.message.reply_text(“📞 Telefon raqamini kiriting (masalan: +998901234567):”)
return ASK_PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[“phone”] = update.message.text.strip()
await update.message.reply_text(
“📅 Qabul sanasini kiriting\nFormat: KK.OO.YYYY  (masalan: 15.06.2025):”
)
return ASK_DATE

async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text.strip()
try:
datetime.strptime(text, “%d.%m.%Y”)
except ValueError:
await update.message.reply_text(
“❌ Sana noto’g’ri formatda. Iltimos qaytadan kiriting (masalan: 15.06.2025):”
)
return ASK_DATE
context.user_data[“date”] = text
await update.message.reply_text(
“🕐 Qabul vaqtini kiriting\nFormat: SS:MM  (masalan: 14:30):”
)
return ASK_TIME

async def ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text.strip()
try:
datetime.strptime(text, “%H:%M”)
except ValueError:
await update.message.
[05.03.2026 15:25] Admiral: reply_text(
“❌ Vaqt noto’g’ri formatda. Iltimos qaytadan kiriting (masalan: 14:30):”
)
return ASK_TIME
context.user_data[“time”] = text
await update.message.reply_text(
“📝 Qo’shimcha izoh kiriting (kasallik, muammo, va h.k.)\n”
“Agar izoh bo’lmasa — /skip yozing:”
)
return ASK_NOTE

async def ask_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[“note”] = update.message.text.strip()
return await show_confirm(update, context)

async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
context.user_data[“note”] = “”
return await show_confirm(update, context)

async def show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
d = context.user_data
text = (
“✅ *Tasdiqlang:*\n\n”
f”👤 Ism: {d[‘name’]}\n”
f”📞 Telefon: {d[‘phone’]}\n”
f”📅 Sana: {d[‘date’]}\n”
f”🕐 Vaqt: {d[‘time’]}\n”
f”📝 Izoh: {d.get(‘note’) or ‘—’}”
)
kb = InlineKeyboardMarkup([
[InlineKeyboardButton(“✅ Saqlash”, callback_data=“save_ap”),
InlineKeyboardButton(“❌ Bekor qilish”, callback_data=“cancel_ap”)]
])
await update.message.reply_text(text, parse_mode=“Markdown”, reply_markup=kb)
return CONFIRM

async def save_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE):
global next_id
query = update.callback_query
await query.answer()
d = context.user_data
ap = {
    "id": next_id,
    "name": d["name"],
    "phone": d["phone"],
    "date": d["date"],
    "time": d["time"],
    "note": d.get("note", ""),
    "reminded_1d": False,
    "reminded_2h": False,
}
appointments[next_id] = ap
next_id += 1

await query.message.reply_text(
    f"✅ Bemor muvaffaqiyatli saqlandi!\n\n{get_appointment_text(ap, show_id=True)}",
    reply_markup=main_menu_keyboard()
)
context.user_data.clear()
return ConversationHandler.END

async def cancel_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
await query.message.reply_text(“❌ Bekor qilindi.”, reply_markup=main_menu_keyboard())
context.user_data.clear()
return ConversationHandler.END

# ─────────────────────────────────────────────

# Ro’yxat ko’rish

# ─────────────────────────────────────────────

async def list_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if not appointments:
    await query.message.reply_text(
        "📋 Hozircha hech qanday bemor yo'q.",
        reply_markup=main_menu_keyboard()
    )
    return

# Sanaga qarab tartiblash
sorted_ap = sorted(
    appointments.values(),
    key=lambda x: datetime.strptime(f"{x['date']} {x['time']}", "%d.%m.%Y %H:%M")
)

text = "📋 *Barcha bemorlar:*\n\n"
for ap in sorted_ap:
    text += get_appointment_text(ap, show_id=True) + "\n" + "─" * 25 + "\n"

await query.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ─────────────────────────────────────────────

# Bugungi qabullar

# ─────────────────────────────────────────────

async def today_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
today_str = datetime.now().strftime("%d.%m.%Y")
today_list = [
    ap for ap in appointments.values() if ap["date"] == today_str
]
today_list.sort(key=lambda x: x["time"])

if not today_list:
    await query.message.reply_text(
        f"📅 Bugun ({today_str}) qabul yo'q.",
        reply_markup=main_menu_keyboard()
    )
    return

text = f"📅 *Bugungi qabullar ({today_str}):*\n\n"
for ap in today_list:
    text += get_appointment_text(ap, show_id=True) + "\n" + "─" * 25 + "\n"

await query.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ─────────────────────────────────────────────

# Bemor o’chirish

# ─────────────────────────────────────────────

async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
if not appointments:
    await query.message.reply_text("📋 O'chiriladigan bemor yo'q.", reply_markup=main_menu_keyboard())
    return

buttons = []
for ap in appointments.values():
[05.03.2026 15:25] Admiral: label = f"#{ap['id']} — {ap['name']} ({ap['date']} {ap['time']})"
    buttons.append([InlineKeyboardButton(label, callback_data=f"del_{ap['id']}")])
buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="back")])

await query.message.reply_text(
    "🗑️ O'chirmoqchi bo'lgan bemorni tanlang:",
    reply_markup=InlineKeyboardMarkup(buttons)
)

async def delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
ap_id = int(query.data.split("_")[1])
if ap_id in appointments:
    ap = appointments.pop(ap_id)
    await query.message.reply_text(
        f"🗑️ *{ap['name']}* ({ap['date']} {ap['time']}) o'chirildi.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
else:
    await query.message.reply_text("❌ Bemor topilmadi.", reply_markup=main_menu_keyboard())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
query = update.callback_query
await query.answer()
await query.message.reply_text(“🏠 Asosiy menyu:”, reply_markup=main_menu_keyboard())

# ─────────────────────────────────────────────

# ⏰ Eslatma yuboruvchi background task

# ─────────────────────────────────────────────

async def send_reminders(app: Application):
“”“Har 5 daqiqada ishlaydi va eslatmalarni tekshiradi.”””
while True:
await asyncio.sleep(300)   # 5 daqiqa
now = datetime.now()
    for ap_id, ap in list(appointments.items()):
        try:
            ap_dt = datetime.strptime(f"{ap['date']} {ap['time']}", "%d.%m.%Y %H:%M")
        except ValueError:
            continue

        diff_minutes = (ap_dt - now).total_seconds() / 60

        # 1 kun oldin (1440 daqiqa ±10 daqiqa)
        if not ap["reminded_1d"] and 1430 <= diff_minutes <= 1450:
            msg = (
                "🔔 *1 KUN OLDINGI ESLATMA*\n\n"
                f"{get_appointment_text(ap)}\n\n"
                "⏰ Ertaga qabul bor!"
            )
            if DOCTOR_CHAT_ID:
                await app.bot.send_message(DOCTOR_CHAT_ID, msg, parse_mode="Markdown")
            ap["reminded_1d"] = True

        # 2 soat oldin (120 daqiqa ±10 daqiqa)
        if not ap["reminded_2h"] and 110 <= diff_minutes <= 130:
            msg = (
                "🚨 *2 SOAT OLDINGI ESLATMA*\n\n"
                f"{get_appointment_text(ap)}\n\n"
                "⏰ Qabul 2 soatdan keyin boshlanadi!"
            )
            if DOCTOR_CHAT_ID:
                await app.bot.send_message(DOCTOR_CHAT_ID, msg, parse_mode="Markdown")
            ap["reminded_2h"] = True

# ─────────────────────────────────────────────

# Botni ishga tushirish

# ─────────────────────────────────────────────

def main():
app = Application.builder().token(BOT_TOKEN).build()
# Bemor qo'shish suhbati
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_start, pattern="^add$")],
    states={
        ASK_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
        ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
        ASK_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
        ASK_TIME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time)],
        ASK_NOTE:  [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_note),
            CommandHandler("skip", skip_note),
        ],
        CONFIRM:   [CallbackQueryHandler(save_appointment, pattern="^save_ap$"),
                    CallbackQueryHandler(cancel_ap, pattern="^cancel_ap$")],
    },
    fallbacks=[CommandHandler("start", start)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(list_appointments,   pattern="^list$"))
app.add_handler(CallbackQueryHandler(today_appointments,  pattern="^today$"))
app.add_handler(CallbackQueryHandler(delete_start,        pattern="^delete_start$"))
app.add_handler(CallbackQueryHandler(delete_confirm,      pattern=r"^del_\d+$"))
app.add_handler(CallbackQueryHandler(back_to_menu,        pattern="^back$"))

# Eslatma vazifasini background da ishga tushirish
[05.03.2026 15:25] Admiral: loop = asyncio.get_event_loop()
loop.create_task(send_reminders(app))

print("✅ Bot ishga tushdi! To'xtatish uchun Ctrl+C bosing.")
app.run_polling(allowed_updates=Update.ALL_TYPES)

if name == “**main**”:
main()
