import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "8603255120:AAFrLdxfv1uoPUzCGHh0w4ZQG0tmwMiRIUI"
DOCTOR_CHAT_ID = None

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

ASK_NAME, ASK_PHONE, ASK_DATE, ASK_CLINIC, ASK_NOTE, CONFIRM = range(6)

CLINICS = {
    "clinic_1": "Darmon Servis klinikasi (Chilonzor tumani)",
    "clinic_2": "As Sihat klinikasi (Yashnobod tumani)",
}

appointments = {}
next_id = 1

def ap_text(ap, show_id=False):
    lines = []
    if show_id:
        lines.append("ID: " + str(ap["id"]))
    lines.append("Ism: " + ap["name"])
    lines.append("Bemorning yoshi: " + ap["age"])
    lines.append("Tel: " + ap["phone"])
    lines.append("Bemorni bezovta qiloyatgan muammo haqida qisqacha ma'lumot bering: " + ap["information"])
    lines.append("Klinika: " + ap["clinic"])
    if ap.get("note"):
        lines.append("Izoh: " + ap["note"])
    return "\n".join(lines)

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Shifokor qabuliga yozilish", callback_data="add")],
      


    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DOCTOR_CHAT_ID
    DOCTOR_CHAT_ID = update.effective_chat.id
    await update.message.reply_text("Shifokor qabul boti\n\nMenyudan tanlang:", reply_markup=menu())

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Bemor ismini kiriting:")
    return ASK_NAME

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Telefon raqamini kiriting:")
    return ASK_PHONE


async def got_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("Noto'g'ri format. Qaytadan kiriting (masalan: 15.06.2025):")
        return ASK_DATE
    context.user_data["date"] = text
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Darmon Servis klinikasi (Chilonzor)", callback_data="clinic_1")],
        [InlineKeyboardButton("As Sihat klinikasi (Yashnobod)", callback_data="clinic_2")],
    ])
    await update.message.reply_text("Qabul joyini tanlang:", reply_markup=kb)
    return ASK_CLINIC

async def got_clinic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    clinic_key = update.callback_query.data
    context.user_data["clinic"] = CLINICS[clinic_key]


    await update.callback_query.message.reply_text("Izoh kiriting yoki /skip yozing:")
    return ASK_NOTE

async def got_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note"] = update.message.text.strip()
    return await show_confirm(update, context)

async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note"] = ""
    return await show_confirm(update, context)

async def show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data
    text = (
        "Tasdiqlang:\n\n"
        "Ism: " + d["name"] + "\n"
        "Tel: " + d["phone"] + "\n"
        "Sana: " + d["date"] + "\n"
        "Klinika: " + d["clinic"] + "\n"
        "Izoh: " + (d.get("note") or "-")
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Saqlash", callback_data="save"),
         InlineKeyboardButton("Bekor", callback_data="cancel")]
    ])
    await update.message.reply_text(text, reply_markup=kb)
    return CONFIRM

async def save_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    await update.callback_query.answer()
    d = context.user_data
    ap = {
        "id": next_id,
        "name": d["name"],
        "phone": d["phone"],
        "date": d["date"],
        "clinic": d["clinic"],
        "note": d.get("note", ""),
        "r1d": False,
        "r2h": False,
    }
    appointments[next_id] = ap


    next_id += 1
    await update.callback_query.message.reply_text("Bemor saqlandi!\n\n" + ap_text(ap, show_id=True), reply_markup=menu())
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Bekor qilindi.", reply_markup=menu())
    context.user_data.clear()
    return ConversationHandler.END

async def list_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not appointments:
        await update.callback_query.message.reply_text("Hozircha bemor yoq.", reply_markup=menu())
        return
    items = sorted(appointments.values(), key=lambda x: datetime.strptime(x["date"], "%d.%m.%Y"))
    text = "Barcha bemorlar:\n\n"
    for ap in items:
        text += ap_text(ap, show_id=True) + "\n" + "-" * 20 + "\n"
    await update.callback_query.message.reply_text(text, reply_markup=menu())

async def today_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    today = datetime.now().strftime("%d.%m.%Y")
    items = [ap for ap in appointments.values() if ap["date"] == today]
    if not items:
        await update.callback_query.message.reply_text("Bugun qabul yoq.", reply_markup=menu())
        return
    text = "Bugungi qabullar (" + today + "):\n\n"
    for ap in items:
        text += ap_text(ap, show_id=True) + "\n" + "-" * 20 + "\n"
    await update.callback_query.message.reply_text(text, reply_markup=menu())

async def del_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not appointments:
        await update.callback_query.message.reply_text("Ochiriladigan bemor yoq.", reply_markup=menu())
        return
    buttons = []
    for ap in appointments.values():
        label = "#" + str(ap["id"]) + " - " + ap["name"] + " (" + ap["date"] + ")"
        buttons.append([InlineKeyboardButton(label, callback_data="d_" + str(ap["id"]))])


    buttons.append([InlineKeyboardButton("Orqaga", callback_data="back")])
    await update.callback_query.message.reply_text("Ochirmoqchi bo'lgan bemorni tanlang:", reply_markup=InlineKeyboardMarkup(buttons))

async def del_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ap_id = int(update.callback_query.data.split("_")[1])
    if ap_id in appointments:
        ap = appointments.pop(ap_id)
        await update.callback_query.message.reply_text(ap["name"] + " o'chirildi.", reply_markup=menu())
    else:
        await update.callback_query.message.reply_text("Bemor topilmadi.", reply_markup=menu())

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Asosiy menyu:", reply_markup=menu())

async def reminders(app):
    while True:
        await asyncio.sleep(300)
        now = datetime.now()
        for ap in list(appointments.values()):
            try:
                ap_dt = datetime.strptime(ap["date"], "%d.%m.%Y")
            except ValueError:
                continue
            diff_hours = (ap_dt - now).total_seconds() / 3600
            if not ap["r1d"] and 23.8 <= diff_hours <= 24.2:
                if DOCTOR_CHAT_ID:
                    await app.bot.send_message(DOCTOR_CHAT_ID, "1 KUN OLDINGI ESLATMA\n\n" + ap_text(ap) + "\n\nErtaga qabul bor!")
                ap["r1d"] = True
            if not ap["r2h"] and 1.8 <= diff_hours <= 2.2:
                if DOCTOR_CHAT_ID:
                    await app.bot.send_message(DOCTOR_CHAT_ID, "2 SOAT OLDINGI ESLATMA\n\n" + ap_text(ap) + "\n\nBugun qabul bor!")
                ap["r2h"] = True

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern="^add$")],
        states={
            ASK_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            ASK_PHONE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_phone)],


            ASK_DATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, got_date)],
            ASK_CLINIC: [CallbackQueryHandler(got_clinic, pattern="^clinic_")],
            ASK_NOTE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, got_note),
                         CommandHandler("skip", skip_note)],
            CONFIRM:    [CallbackQueryHandler(save_ap, pattern="^save$"),
                         CallbackQueryHandler(cancel_ap, pattern="^cancel$")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(list_ap, pattern="^list$"))
    app.add_handler(CallbackQueryHandler(today_ap, pattern="^today$"))
    app.add_handler(CallbackQueryHandler(del_start, pattern="^del_start$"))
    app.add_handler(CallbackQueryHandler(del_confirm, pattern=r"^d_\d+$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))

    loop = asyncio.get_event_loop()
    loop.create_task(reminders(app))

    print("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
