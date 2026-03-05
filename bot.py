import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

BOT_TOKEN = "BU_YERGA_TOKEN_KIRITING"
DOCTOR_CHAT_ID = None

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Bemor uchun holatlar
ASK_NAME, ASK_AGE, ASK_PROBLEM, ASK_CLINIC, DONE = range(5)

CLINICS = {
    "clinic_1": "Darmon Servis klinikasi (Chilonzor tumani)",
    "clinic_2": "As-Sihat klinikasi (Yashnobod tumani)",
}

applications = {}
next_id = 1

def app_text(ap, show_id=False):
    lines = []
    if show_id:
        lines.append("Ariza ID: " + str(ap["id"]))
    lines.append("Ism: " + ap["name"])
    lines.append("Yosh: " + ap["age"])
    lines.append("Muammo: " + ap["problem"])
    lines.append("Klinika: " + ap["clinic"])
    lines.append("Vaqt: " + ap["time"])
    if ap.get("status"):
        lines.append("Holat: " + ap["status"])
    return "\n".join(lines)

def doctor_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Yangi arizalar", callback_data="new_apps")],
        [InlineKeyboardButton("Barcha arizalar", callback_data="all_apps")],


        [InlineKeyboardButton("Arizani tasdiqlash", callback_data="confirm_start")],
        [InlineKeyboardButton("Arizani rad etish", callback_data="reject_start")],
    ])

# ─── SHIFOKOR ───────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DOCTOR_CHAT_ID
    user = update.effective_user
    text = update.message.text

    # Shifokor /start doktor deb kiradi
    if text and "doktor" in text.lower():
        DOCTOR_CHAT_ID = update.effective_chat.id
        await update.message.reply_text(
            "Shifokor paneliga xush kelibsiz!\n\nMenyudan tanlang:",
            reply_markup=doctor_menu()
        )
        return ConversationHandler.END

    # Bemor uchun
    await update.message.reply_text(
        "Assalomu alaykum!\n\nSizni shifokor qabuliga yozish uchun bir nechta savol beramiz.\n\nBoshlaymizmi? Iltimos, to'liq ism-sharifingizni kiriting:"
    )
    return ASK_NAME

async def new_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    items = [ap for ap in applications.values() if ap.get("status") == "Yangi"]
    if not items:
        await update.callback_query.message.reply_text("Yangi ariza yoq.", reply_markup=doctor_menu())
        return
    text = "Yangi arizalar:\n\n"
    for ap in items:
        text += app_text(ap, show_id=True) + "\n" + "-" * 25 + "\n"
    await update.callback_query.message.reply_text(text, reply_markup=doctor_menu())

async def all_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    if not applications:
        await update.callback_query.message.reply_text("Hozircha ariza yoq.", reply_markup=doctor_menu())
        return
    text = "Barcha arizalar:\n\n"
    for ap in sorted(applications.values(), key=lambda x: x["id"]):


        text += app_text(ap, show_id=True) + "\n" + "-" * 25 + "\n"
    await update.callback_query.message.reply_text(text, reply_markup=doctor_menu())

async def confirm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    items = [ap for ap in applications.values() if ap.get("status") == "Yangi"]
    if not items:
        await update.callback_query.message.reply_text("Tasdiqlanadigan ariza yoq.", reply_markup=doctor_menu())
        return
    buttons = []
    for ap in items:
        label = "#" + str(ap["id"]) + " - " + ap["name"]
        buttons.append([InlineKeyboardButton(label, callback_data="conf_" + str(ap["id"]))])
    buttons.append([InlineKeyboardButton("Orqaga", callback_data="back")])
    await update.callback_query.message.reply_text("Qaysi arizani tasdiqlaysiz?", reply_markup=InlineKeyboardMarkup(buttons))

async def confirm_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ap_id = int(update.callback_query.data.split("_")[1])
    if ap_id not in applications:
        await update.callback_query.message.reply_text("Ariza topilmadi.", reply_markup=doctor_menu())
        return

    ap = applications[ap_id]
    ap["status"] = "Tasdiqlandi"

    # Shifokorga xabar
    await update.callback_query.message.reply_text(
        "#" + str(ap_id) + " ariza tasdiqlandi.\n\n" + app_text(ap, show_id=True),
        reply_markup=doctor_menu()
    )

    # Bemorga xabar yuborish (agar chat_id saqlangan bo'lsa)
    if ap.get("chat_id"):
        try:
            await update.get_bot().send_message(
                ap["chat_id"],
                "Hurmatli " + ap["name"] + ",\n\n"
                "Shifokor sizning arizangizni qabul qildi.\n\n"
                "Qabul joyi: " + ap["clinic"] + "\n\n"
                "Tez orada qabul sanasi va vaqti to'g'risida xabar beriladi.\n\n"
                "Savollar uchun aloqaga chiqing."
            )
        except Exception:
            pass


async def reject_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    items = [ap for ap in applications.values() if ap.get("status") == "Yangi"]
    if not items:
        await update.callback_query.message.reply_text("Rad etiladigan ariza yoq.", reply_markup=doctor_menu())
        return
    buttons = []
    for ap in items:
        label = "#" + str(ap["id"]) + " - " + ap["name"]
        buttons.append([InlineKeyboardButton(label, callback_data="rej_" + str(ap["id"]))])
    buttons.append([InlineKeyboardButton("Orqaga", callback_data="back")])
    await update.callback_query.message.reply_text("Qaysi arizani rad etasiz?", reply_markup=InlineKeyboardMarkup(buttons))

async def reject_ap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ap_id = int(update.callback_query.data.split("_")[1])
    if ap_id not in applications:
        await update.callback_query.message.reply_text("Ariza topilmadi.", reply_markup=doctor_menu())
        return

    ap = applications[ap_id]
    ap["status"] = "Rad etildi"

    await update.callback_query.message.reply_text(
        "#" + str(ap_id) + " ariza rad etildi.",
        reply_markup=doctor_menu()
    )

    if ap.get("chat_id"):
        try:
            await update.get_bot().send_message(
                ap["chat_id"],
                "Hurmatli " + ap["name"] + ",\n\n"
                "Afsuski, hozirda qabul uchun joy mavjud emas.\n"
                "Iltimos, keyinroq qayta murojaat qiling."
            )
        except Exception:
            pass

async def back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Asosiy menyu:", reply_markup=doctor_menu())


# ─── BEMOR ───────────────────────────────────────

async def got_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text.strip()
    await update.message.reply_text("Yoshingizni kiriting (masalan: 35):")
    return ASK_AGE

async def got_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = update.message.text.strip()
    await update.message.reply_text("Sizni qiynayotgan muammo haqida qisqacha ma'lumot bering:")
    return ASK_PROBLEM

async def got_problem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["problem"] = update.message.text.strip()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("Darmon Servis klinikasi (Chilonzor)", callback_data="clinic_1")],
        [InlineKeyboardButton("As-Sihat klinikasi (Yashnobod)", callback_data="clinic_2")],
    ])
    await update.message.reply_text("Ko'rik uchun qaysi klinika sizga qulayroq?", reply_markup=kb)
    return ASK_CLINIC

async def got_clinic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global next_id
    await update.callback_query.answer()

    clinic_key = update.callback_query.data
    context.user_data["clinic"] = CLINICS[clinic_key]

    d = context.user_data
    ap = {
        "id": next_id,
        "name": d["name"],
        "age": d["age"],
        "problem": d["problem"],
        "clinic": d["clinic"],
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "status": "Yangi",
        "chat_id": update.effective_chat.id,
    }
    applications[next_id] = ap
    next_id += 1

    # Bemorga tasdiqlash xabari


    await update.callback_query.message.reply_text(
        "Hurmatli " + d["name"] + ",\n\n"
        "Muvaffaqiyatli qabulga yozildingiz!\n\n"
        "Ariza ma'lumotlari:\n"
        "Ism: " + d["name"] + "\n"
        "Yosh: " + d["age"] + "\n"
        "Klinika: " + d["clinic"] + "\n\n"
        "Shifokor arizangizni ko'rib chiqqanidan so'ng, qabul sanasi va vaqti to'g'risida "
        "sizga alohida xabar yuboriladi.\n\n"
        "Sabrli kutganingiz uchun rahmat!"
    )

    # Shifokorga yangi ariza xabari
    if DOCTOR_CHAT_ID:
        try:
            await update.get_bot().send_message(
                DOCTOR_CHAT_ID,
                "YANGI ARIZA KELDI!\n\n" + app_text(ap, show_id=True),
                reply_markup=doctor_menu()
            )
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END

# ─── MAIN ───────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, got_name)],
            ASK_AGE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, got_age)],
            ASK_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_problem)],
            ASK_CLINIC:  [CallbackQueryHandler(got_clinic, pattern="^clinic_")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(new_apps,      pattern="^new_apps$"))
    app.add_handler(CallbackQueryHandler(all_apps,      pattern="^all_apps$"))
    app.add_handler(CallbackQueryHandler(confirm_start, pattern="^confirm_start$"))


    app.add_handler(CallbackQueryHandler(confirm_ap,    pattern=r"^conf_\d+$"))
    app.add_handler(CallbackQueryHandler(reject_start,  pattern="^reject_start$"))
    app.add_handler(CallbackQueryHandler(reject_ap,     pattern=r"^rej_\d+$"))
    app.add_handler(CallbackQueryHandler(back,          pattern="^back$"))

    print("Bot ishga tushdi!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
