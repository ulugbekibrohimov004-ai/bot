import asyncio
import logging
import sqlite3
import random
import sys
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ChatMemberStatus
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web

# ================= SOZLAMALAR =================
BOT_TOKEN = "8140288192:AAEUhTH1OXdNXSt6HM3I3JD8EsHvA6PXGOY"
# Admin ID ni raqam shaklida yozing (qo'shtirnoqsiz)
ADMIN_ID = 7201215484

# KANALLAR
KANAL_1 = "@Binary_Mind_Uz"
KANAL_1_LINK = "https://t.me/Binary_Mind_Uz"

KANAL_2 = "@kinome_k"
KANAL_2_LINK = "https://t.me/kinome_k"

# KINO BAZA
KINO_KANAL_USER = "kino_18_16"
KINO_BAZA_KANAL = "@kino_18_16"
ENG_OXIRGI_KINO_ID = 500

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class AdminAloqa(StatesGroup):
    xabar_kutish = State()

# --- MENYU ---
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎲 Tasodifiy kino"), KeyboardButton(text="🔗 Do'stlarni chaqirish")],
        [KeyboardButton(text="✍️ Adminga yozish"), KeyboardButton(text="📢 Kanalimiz")]
    ],
    resize_keyboard=True
)

# --- BAZA BILAN ISHLASH ---
def baza_ulanish():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)""")
    con.commit()
    return con, cur

def user_qushish(user_id):
    try:
        con = sqlite3.connect("users.db")
        cur = con.cursor()
        cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        con.commit()
        con.close()
    except: pass

def hamma_userlar():
    try:
        con = sqlite3.connect("users.db")
        cur = con.cursor()
        cur.execute("SELECT id FROM users")
        users = cur.fetchall()
        con.close()
        return [x[0] for x in users]
    except: return []

# --- OBUNA TEKSHIRISH (OPTIMALLASHTIRILGAN) ---
async def check_sub(user_id, channel_username):
    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except Exception:
        # Agar bot kanalga admin qilinmagan bo'lsa yoki xato chiqsa, False qaytadi
        return False

async def get_subscription_status(user_id):
    """
    Qaysi kanalga a'zo va qaysi biriga a'zo emasligini aniqlaydi.
    Qaytadi: (sub1_bool, sub2_bool)
    """
    sub1 = await check_sub(user_id, KANAL_1)
    sub2 = await check_sub(user_id, KANAL_2)
    return sub1, sub2

async def majburiy_obuna_xabari(message: Message, sub1, sub2, kino_kod=None):
    callback_text = f"check_{kino_kod}" if kino_kod else "check_no"
    
    # Tugmalarni dinamik yasaymiz
    rows = []
    
    # Agar 1-kanalga a'zo bo'lmasa, tugmani qo'shamiz
    if not sub1:
        rows.append([InlineKeyboardButton(text="1️⃣-kanalga a'zo bo'lish", url=KANAL_1_LINK)])
    
    # Agar 2-kanalga a'zo bo'lmasa, tugmani qo'shamiz
    if not sub2:
        rows.append([InlineKeyboardButton(text="2️⃣-kanalga a'zo bo'lish", url=KANAL_2_LINK)])
        
    # Tekshirish tugmasi doim turadi
    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data=callback_text)])

    tugmalar = InlineKeyboardMarkup(inline_keyboard=rows)

    await message.answer(
        f"⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>",
        reply_markup=tugmalar,
        parse_mode="HTML"
    )

async def send_movie(message: Message, kino_code):
    temp_msg = await message.answer(f"🔎 Kino qidirilmoqda... (Kod: {kino_code})")
    try:
        post_id = int(kino_code)
        await bot.copy_message(chat_id=message.chat.id, from_chat_id=KINO_BAZA_KANAL, message_id=post_id)
        await temp_msg.delete()
    except Exception:
        await temp_msg.edit_text("❌ Kino topilmadi yoki o'chirilgan.")

# ================= HANDLERLAR (TARTIBI MUHIM) =================

# 1. ADMIN COMMANDLARI
@dp.message(Command("me"))
async def me_handler(message: Message):
    await message.answer(f"🆔 Sizning ID: `{message.from_user.id}`", parse_mode="Markdown")

@dp.message(Command("stat"))
async def stat_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        users = hamma_userlar()
        await message.answer(f"📊 Jami foydalanuvchilar: {len(users)} ta")

@dp.message(Command("backup"))
async def backup_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        try:
            file = FSInputFile("users.db")
            await message.answer_document(file, caption="📁 Baza zaxira nusxasi")
        except:
            await message.answer("⚠️ Baza fayli topilmadi.")

@dp.message(Command("send"))
async def send_handler(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not message.reply_to_message:
        await message.answer("⚠️ Xabar yuborish uchun birorta xabarga REPLY qiling.")
        return

    users = hamma_userlar()
    sent_msg = await message.answer(f"🚀 Xabar yuborish boshlandi... ({len(users)} ta user)")
    count = 0
    
    # Xabarni sekinroq yuborish (bloklanmaslik uchun)
    for user in users:
        try:
            await message.reply_to_message.copy_to(chat_id=user)
            count += 1
            await asyncio.sleep(0.05) # Spamdan himoya
        except:
            pass # Bloklagan userlar uchun

    await sent_msg.edit_text(f"✅ Tarqatish tugadi.\nYetib bordi: {count} ta")

# 2. MENYU COMMANDLARI
@dp.message(F.text == "📢 Kanalimiz")
async def channel_info(message: Message):
    await message.answer(f"Bizning kanallarimiz:\n1. {KANAL_1_LINK}\n2. {KANAL_2_LINK}")

@dp.message(F.text == "🎲 Tasodifiy kino")
async def random_movie(message: Message):
    user_id = message.from_user.id
    sub1, sub2 = await get_subscription_status(user_id)
    if not (sub1 and sub2):
        await majburiy_obuna_xabari(message, sub1, sub2)
        return
    
    rand_code = random.randint(1, ENG_OXIRGI_KINO_ID)
    await message.answer(f"🎲 Tavakkal kod: **{rand_code}**")
    await send_movie(message, rand_code)

@dp.message(F.text == "🔗 Do'stlarni chaqirish")
async def share_link_handler(message: Message):
    bot_info = await bot.me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    share_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↗️ Do'stlarga yuborish", url=f"https://t.me/share/url?url={link}&text=Zo'r kino bot ekan, kirib ko'r:")]
    ])
    await message.answer("👇 Pastdagi tugmani bosing va do'stlaringizga yuboring:", reply_markup=share_button)

@dp.message(F.text == "✍️ Adminga yozish")
async def contact_admin(message: Message, state: FSMContext):
    await message.answer("📝 Xabaringizni yozib qoldiring:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminAloqa.xabar_kutish)

@dp.message(AdminAloqa.xabar_kutish)
async def forward_to_admin(message: Message, state: FSMContext):
    try:
        xabar = f"📨 <b>Yangi xabar!</b>\nKimdan: {message.from_user.full_name} (`{message.from_user.id}`)\n\nXabar:\n{message.text}"
        await bot.send_message(chat_id=ADMIN_ID, text=xabar, parse_mode="HTML")
        await message.answer("✅ Xabaringiz adminga yuborildi!", reply_markup=main_menu)
    except Exception as e:
        await message.answer("❌ Xatolik yuz berdi.", reply_markup=main_menu)
    await state.clear()

# 3. START VA KINO KODLARI (Eng oxirida bo'lishi kerak)
@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user_qushish(user_id) # Bazaga yozish
    
    arg = command.args
    sub1, sub2 = await get_subscription_status(user_id)

    # Agar ikkalasiga ham a'zo bo'lmasa yoki bittasiga a'zo bo'lmasa
    if not (sub1 and sub2):
        await majburiy_obuna_xabari(message, sub1, sub2, arg)
        return

    if arg and arg.isdigit():
        await send_movie(message, arg)
    else:
        await message.answer("✅ Xush kelibsiz! Kino kodini yuboring:", reply_markup=main_menu)

@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    text = message.text
    
    # 1. Admin userga javob yozayotgan bo'lsa (REPLY)
    if user_id == ADMIN_ID and message.reply_to_message:
        try:
            # Xabar ichidan ID ni qidirish (regex shart emas, oddiy usul)
            original_text = message.reply_to_message.text
            if "Kimdan:" in original_text:
                # Bot yuborgan shablon ichidan ID ni ajratib olish
                target_id = original_text.split('(`')[1].split('`)')[0]
                await bot.send_message(chat_id=target_id, text=f"☎️ <b>Admindan javob:</b>\n\n{text}", parse_mode="HTML")
                await message.answer("✅ Javob yuborildi.")
            else:
                await message.answer("⚠️ User ID topilmadi. Javob yozish uchun 'Adminga yozish' orqali kelgan xabarga reply qiling.")
        except:
            await message.answer("❌ Xatolik.")
        return

    # 2. Oddiy user kino so'rasa
    sub1, sub2 = await get_subscription_status(user_id)
    if not (sub1 and sub2):
        kod = text if text.isdigit() else None
        await majburiy_obuna_xabari(message, sub1, sub2, kod)
        return

    if text.isdigit():
        await send_movie(message, text)
    else:
        await message.answer("❌ Iltimos, faqat kino kodini yuboring yoki menyudan foydalaning.", reply_markup=main_menu)

# --- CALLBACK (OBUNANI TEKSHIRISH) ---
@dp.callback_query(F.data.startswith("check_"))
async def check_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split("_")[1]
    
    sub1, sub2 = await get_subscription_status(user_id)
    
    if sub1 and sub2:
        await callback.message.delete()
        if data != "no" and data.isdigit():
            await send_movie(callback.message, data)
        else:
            await callback.message.answer("✅ Obuna tasdiqlandi! Kodni yuborishingiz mumkin.", reply_markup=main_menu)
    else:
        # Hali ham a'zo emas, qaytadan yangilab ko'rsatamiz (balki bittasiga a'zo bo'lgandir)
        await callback.message.delete()
        await majburiy_obuna_xabari(callback.message, sub1, sub2, data if data != "no" else None)
        await callback.answer("❌ Hali to'liq a'zo bo'lmadingiz!", show_alert=True)

# 🔥 YANGI KINO XABARI (Kanal 1)
@dp.channel_post(F.chat.username == KINO_KANAL_USER)
async def new_movie_notification(message: Message):
    msg_id = message.message_id
    bot_info = await bot.me()
    xabar = (f"🔔 <b>YANGI KINO!</b>\n🆔 Kodi: <code>{msg_id}</code>\n"
             f"🔗 Link: https://t.me/{bot_info.username}?start={msg_id}")
    try: await bot.send_message(chat_id=ADMIN_ID, text=xabar, parse_mode="HTML")
    except: pass

# ================= SERVER VA BOT (BIRGA) =================

async def handle(request):
    return web.Response(text="Bot ishlmoqda...")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    baza_ulanish()
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.gather(dp.start_polling(bot), start_web_server())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtadi")
