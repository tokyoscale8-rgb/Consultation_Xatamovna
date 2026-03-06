import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import gspread
from google.oauth2.service_account import Credentials
from config import BOT_TOKEN, DOCTOR_CHAT_ID, SPREADSHEET_ID, CREDENTIALS_FILE

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Bot va Dispatcher
bot = Bot(token=8603255120:AAFrLdxfv1uoPUzCGHh0w4ZQG0tmwMiRIUI)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# Google Sheets ulanish
def get_sheet():
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

# Klinikalar
KLINIKALAR = {
 "darmon": " Darmon Servis Klinikasi (Chilonzor tumani)",
 "assihat": " As Sihat Klinikasi (Yashnobod tumani)"
}

# FSM holatlari
class BemorForm(StatesGroup):
    ism = State()
    telefon = State()


    tugilgan_sana = State()
    shikoyat = State()
    klinika = State()

# ==================== START ====================
@dp.message(CommandStart())
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
 keyboard=[[KeyboardButton(text=" Qabulga yozilish")]],
        resize_keyboard=True
    )
    await message.answer(
 " Assalomu alaykum!\n\n"
        "Shifokor qabuliga yozilish uchun quyidagi tugmani bosing.",
        reply_markup=kb
    )

@dp.message(F.text == " Qabulga yozilish")
async def qabul_boshlash(message: types.Message, state: FSMContext):
    await state.set_state(BemorForm.ism)
    await message.answer(
 " Ismingiz va familiyangizni kiriting:\n"
        "(Masalan: Aliyev Jasur)"
    )

# ==================== ISM ====================
@dp.message(BemorForm.ism)
async def ism_handler(message: types.Message, state: FSMContext):
    await state.update_data(ism=message.text.strip())
    await state.set_state(BemorForm.telefon)
 await message.answer(" Telefon raqamingizni kiriting:\n(Masalan: +998901234567)")

# ==================== TELEFON ====================
@dp.message(BemorForm.telefon)
async def telefon_handler(message: types.Message, state: FSMContext):
    await state.update_data(telefon=message.text.strip())
    await state.set_state(BemorForm.tugilgan_sana)
 await message.answer(" Tug'ilgan sanangizni kiriting:\n(Masalan: 15.03.1990)")

# ==================== TUG'ILGAN SANA ====================
@dp.message(BemorForm.tugilgan_sana)
async def tugilgan_sana_handler(message: types.Message, state: FSMContext):
    await state.update_data(tugilgan_sana=message.text.strip())
    await state.set_state(BemorForm.shikoyat)
 await message.answer(" Muammo yoki shikoyatingizni qisqacha bayon qiling:")


# ==================== SHIKOYAT ====================
@dp.message(BemorForm.shikoyat)
async def shikoyat_handler(message: types.Message, state: FSMContext):
    await state.update_data(shikoyat=message.text.strip())
    await state.set_state(BemorForm.klinika)

    kb = InlineKeyboardMarkup(inline_keyboard=[
 [InlineKeyboardButton(text=" Darmon Servis (Chilonzor)", callback_data="klinika_darmon")],
 [InlineKeyboardButton(text=" As Sihat (Yashnobod)", callback_data="klinika_assihat")]
    ])
    await message.answer(
 " Qaysi klinikaga tashrif buyurishingiz qulayroq?",
        reply_markup=kb
    )

# ==================== KLINIKA TANLASH ====================
@dp.callback_query(F.data.startswith("klinika_"))
async def klinika_handler(callback: types.CallbackQuery, state: FSMContext):
    klinika_key = callback.data.replace("klinika_", "")
    klinika_nomi = KLINIKALAR.get(klinika_key, "Noma'lum")
    await state.update_data(klinika=klinika_nomi, klinika_key=klinika_key)

    data = await state.get_data()

    # Bemorga tasdiqlash xabari
    await callback.message.edit_text(
 f" Arizangiz qabul qilindi!\n\n"
 f" Ism: {data['ism']}\n"
 f" Telefon: {data['telefon']}\n"
 f" Tug'ilgan sana: {data['tugilgan_sana']}\n"
 f" Shikoyat: {data['shikoyat']}\n"
 f" Klinika: {klinika_nomi}\n\n"
 f" Shifokor qabul kunini tasdiqlashi bilan sizga xabar yuboramiz."
    )

    # Google Sheets ga saqlash
    bemor_id = await saqlash_google_sheets(data, callback.from_user.id)

    # Shifokorga xabar yuborish
    await shifokorga_xabar(data, callback.from_user.id, bemor_id)

    await state.clear()
    await callback.answer()

# ==================== GOOGLE SHEETS GA SAQLASH ====================
async def saqlash_google_sheets(data: dict, user_id: int) -> int:
    try:


        sheet = get_sheet()
        all_records = sheet.get_all_values()
        bemor_id = len(all_records)  # ID = qatorlar soni

        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        row = [
            bemor_id,
            data['ism'],
            data['telefon'],
            data['tugilgan_sana'],
            data['shikoyat'],
            data['klinika'],
            str(user_id),
            now,       # Ariza vaqti
            "",        # Qabul sanasi (shifokor to'ldiradi)
            "",        # Qabul vaqti (shifokor to'ldiradi)
            "Kutilmoqda"  # Status
        ]
        sheet.append_row(row)
        logger.info(f"Bemor #{bemor_id} Google Sheets ga saqlandi.")
        return bemor_id
    except Exception as e:
        logger.error(f"Google Sheets xatosi: {e}")
        return 0

# ==================== SHIFOKORGA XABAR ====================
async def shifokorga_xabar(data: dict, user_id: int, bemor_id: int):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
 text=" Qabul kunini belgilash",
            callback_data=f"belgilash_{bemor_id}_{user_id}"
        )]
    ])
    text = (
 f" <b>YANGI BEMOR ARIZA QOLDIRDI!</b>\n\n"
 f" Bemor ID: #{bemor_id}\n"
 f" Ism: {data['ism']}\n"
 f" Telefon: {data['telefon']}\n"
 f" Tug'ilgan sana: {data['tugilgan_sana']}\n"
 f" Shikoyat: {data['shikoyat']}\n"
 f" Klinika: {data['klinika']}\n\n"
 f" Qabul kunini belgilash uchun tugmani bosing."
    )
    await bot.send_message(DOCTOR_CHAT_ID, text, parse_mode="HTML", reply_markup=kb)

# ==================== SHIFOKOR: QABUL KUNINI BELGILASH ====================
class QabulBelgilash(StatesGroup):


    sana = State()
    vaqt = State()

doctor_states = {}  # {doctor_chat_id: {bemor_id, user_id}}

@dp.callback_query(F.data.startswith("belgilash_"))
async def belgilash_handler(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    bemor_id = parts[1]
    user_id = parts[2]

    await state.set_state(QabulBelgilash.sana)
    await state.update_data(bemor_id=bemor_id, user_id=user_id)

    await callback.message.answer(
 f" Bemor #{bemor_id} uchun qabul sanasini kiriting:\n"
        f"(Masalan: 25.06.2025)"
    )
    await callback.answer()

@dp.message(QabulBelgilash.sana)
async def qabul_sana_handler(message: types.Message, state: FSMContext):
    await state.update_data(qabul_sana=message.text.strip())
    await state.set_state(QabulBelgilash.vaqt)
 await message.answer(" Qabul vaqtini kiriting:\n(Masalan: 10:00)")

@dp.message(QabulBelgilash.vaqt)
async def qabul_vaqt_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    bemor_id = data['bemor_id']
    user_id = int(data['user_id'])
    qabul_sana = data['qabul_sana']
    qabul_vaqt = message.text.strip()

    # Google Sheets ni yangilash
    bemor_malumoti = await yangilash_sheets(bemor_id, qabul_sana, qabul_vaqt)

    if bemor_malumoti:
        ism = bemor_malumoti['ism']
        klinika = bemor_malumoti['klinika']

        # Bemorga xabar
        await bot.send_message(
            user_id,
 f" <b>Qabulingiz tasdiqlandi!</b>\n\n"
 f" Hurmatli {ism},\n\n"
            f"Siz shifokor qabuliga muvaffaqiyatli yozildingiz:\n\n"


 f" Sana: <b>{qabul_sana}</b>\n"
 f" Vaqt: <b>{qabul_vaqt}</b>\n"
 f" Klinika: <b>{klinika}</b>\n\n"
 f"Vaqtida tashrif buyuring! ",
            parse_mode="HTML"
        )

        # Shifokorga to'liq xulosa
        await bot.send_message(
            DOCTOR_CHAT_ID,
 f" <b>QABUL TASDIQLANDI</b>\n\n"
 f" Bemor ID: #{bemor_id}\n"
 f" Ism: {ism}\n"
 f" Telefon: {bemor_malumoti['telefon']}\n"
 f" Tug'ilgan sana: {bemor_malumoti['tugilgan_sana']}\n"
 f" Shikoyat: {bemor_malumoti['shikoyat']}\n"
 f" Klinika: {klinika}\n"
 f" Qabul sanasi: <b>{qabul_sana}</b>\n"
 f" Qabul vaqti: <b>{qabul_vaqt}</b>",
            parse_mode="HTML"
        )

        # Eslatmalarni rejalashtirish
        await rejalashtirish_eslatmalar(bemor_id, ism, klinika, qabul_sana, qabul_vaqt, user_id)

 await message.answer(f" Bemor #{bemor_id} uchun qabul belgilandi va xabarlar yuborildi!")
    else:
 await message.answer(" Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")

    await state.clear()

# ==================== GOOGLE SHEETS YANGILASH ====================
async def yangilash_sheets(bemor_id: str, qabul_sana: str, qabul_vaqt: str) -> dict | None:
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        for i, row in enumerate(all_rows):
            if str(row[0]) == str(bemor_id):
                sheet.update_cell(i + 1, 9, qabul_sana)
                sheet.update_cell(i + 1, 10, qabul_vaqt)
                sheet.update_cell(i + 1, 11, "Tasdiqlangan")
                return {
                    'ism': row[1],
                    'telefon': row[2],
                    'tugilgan_sana': row[3],
                    'shikoyat': row[4],
                    'klinika': row[5]


                }
    except Exception as e:
        logger.error(f"Yangilash xatosi: {e}")
    return None

# ==================== ESLATMALAR REJALASHTIRISH ====================
async def rejalashtirish_eslatmalar(bemor_id, ism, klinika, qabul_sana, qabul_vaqt, user_id):
    try:
        qabul_dt = datetime.strptime(f"{qabul_sana} {qabul_vaqt}", "%d.%m.%Y %H:%M")

        # 1 kun oldin eslatma (shifokorga)
        bir_kun_oldin = qabul_dt - timedelta(days=1)
        if bir_kun_oldin > datetime.now():
            scheduler.add_job(
                eslatma_bir_kun,
                'date',
                run_date=bir_kun_oldin,
                args=[bemor_id, ism, klinika, qabul_sana, qabul_vaqt],
                id=f"1kun_{bemor_id}"
            )

        # 1 soat oldin eslatma (shifokorga)
        bir_soat_oldin = qabul_dt - timedelta(hours=1)
        if bir_soat_oldin > datetime.now():
            scheduler.add_job(
                eslatma_bir_soat,
                'date',
                run_date=bir_soat_oldin,
                args=[bemor_id, ism, klinika, qabul_sana, qabul_vaqt],
                id=f"1soat_{bemor_id}"
            )

        # Qabul tugagandan keyin "Ko'rikdan o'tkazildi" tugmasi
        scheduler.add_job(
            korik_tasdiqlash_yuborish,
            'date',
            run_date=qabul_dt,
            args=[bemor_id, ism, klinika, qabul_sana, qabul_vaqt, user_id],
            id=f"korik_{bemor_id}"
        )

        logger.info(f"Bemor #{bemor_id} uchun eslatmalar rejalashtirildi.")
    except Exception as e:
        logger.error(f"Rejalashtirish xatosi: {e}")

async def eslatma_bir_kun(bemor_id, ism, klinika, sana, vaqt):
    await bot.send_message(


        DOCTOR_CHAT_ID,
 f" <b>ERTANGI QABUL ESLATMASI</b>\n\n"
 f" Bemor ID: #{bemor_id}\n"
 f" Bemor: {ism}\n"
 f" Sana: {sana}\n"
 f" Vaqt: {vaqt}\n"
 f" Klinika: {klinika}",
        parse_mode="HTML"
    )

async def eslatma_bir_soat(bemor_id, ism, klinika, sana, vaqt):
    await bot.send_message(
        DOCTOR_CHAT_ID,
 f" <b>1 SOATDAN KEYIN QABUL!</b>\n\n"
 f" Bemor ID: #{bemor_id}\n"
 f" Bemor: {ism}\n"
 f" Sana: {sana}\n"
 f" Vaqt: {vaqt}\n"
 f" Klinika: {klinika}",
        parse_mode="HTML"
    )

async def korik_tasdiqlash_yuborish(bemor_id, ism, klinika, sana, vaqt, user_id):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
 text=" Ko'rikdan o'tkazildi",
            callback_data=f"korik_{bemor_id}_{user_id}"
        )]
    ])
    await bot.send_message(
        DOCTOR_CHAT_ID,
 f" <b>QABUL VAQTI KELDI</b>\n\n"
 f" Bemor: {ism}\n"
 f" Sana: {sana}\n"
 f" Vaqt: {vaqt}\n"
 f" Klinika: {klinika}\n\n"
        f"Bemorni ko'rikdan o'tkazgandan so'ng tasdiqlang:",
        parse_mode="HTML",
        reply_markup=kb
    )

# ==================== KO'RIK TASDIQLASH ====================
@dp.callback_query(F.data.startswith("korik_"))
async def korik_tasdiqlash(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    bemor_id = parts[1]
    user_id = int(parts[2])


    # Sheets da statusni yangilash
    try:
        sheet = get_sheet()
        all_rows = sheet.get_all_values()
        for i, row in enumerate(all_rows):
            if str(row[0]) == str(bemor_id):
                sheet.update_cell(i + 1, 11, "Ko'rikdan o'tdi")
                ism = row[1]
                break
    except Exception as e:
        logger.error(f"Ko'rik yangilash xatosi: {e}")
        ism = f"#{bemor_id}"

    await callback.message.edit_text(
 f" <b>Bemor #{bemor_id} ({ism}) ko'rikdan o'tkazildi!</b>\n\n"
 f" Status Google Sheets da yangilandi.",
        parse_mode="HTML"
    )
 await callback.answer(" Tasdiqlandi!")

# ==================== MAIN ====================
async def main():
    scheduler.start()
    logger.info("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
