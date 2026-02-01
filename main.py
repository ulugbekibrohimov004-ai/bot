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
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiohttp import web  # Web server uchun

# ================= SOZLAMALAR =================
BOT_TOKEN = "8140288192:AAEUhTH1OXdNXSt6HM3I3JD8EsHvA6PXGOY"
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

# Agar Render/Koyeb da ishlatsangiz PROXY shart emas, shuning uchun session olib tashlandi
# Agar PythonAnywhere bo'lsa, proxy qatorini qaytarish kerak bo'ladi.
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

# --- BAZA ---
def baza_ulanish():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY)""")
    con.commit()
    return con, cur

def user_qushish(user_id):
    con, cur = baza_ulanish()
    try:
        cur.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        con.commit()
    except: pass
    finally: con.close()

def hamma_userlar():
    con, cur = baza_ulanish()
    cur.execute("SELECT id FROM users")
    users = cur.fetchall()
    con.close()
    return [x[0] for x in users]

# --- OBUNA TEKSHIRISH ---
async def check_sub(user_id, channel_username):
    try:
        member = await bot.get_chat_member(chat_id=channel_username, user_id=user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR]
    except: return False

async def check_all_subs(user_id):
    sub1 = await check_sub(user_id, KANAL_1)
    sub2 = await check_sub(user_id, KANAL_2)
    return sub1 and sub2

async def majburiy_obuna_xabari(message: Message, kino_kod=None):
    callback_text = f"check_{kino_kod}" if kino_kod else "check_no"
    tugmalar = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1️⃣-kanalga a'zo bo'lish", url=KANAL_1_LINK)],
        [InlineKeyboardButton(text="2️⃣-kanalga a'zo bo'lish", url=KANAL_2_LINK)],
        [InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data=callback_text)],
    ])
    await message.answer(
        f"⛔️ <b>DIQQAT!</b>\n\nBotdan foydalanish uchun quyidagi <b>2 ta kanalga</b> a'zo bo'lishingiz SHART:",
        reply_markup=tugmalar, parse_mode="HTML"
    )

async def send_movie(message: Message, kino_code):
    temp_msg = await message.answer(f"🔎 Kino qidirilmoqda... (Kod: {kino_code})")
    try:
        post_id = int(kino_code)
        await bot.copy_message(chat_id=message.chat.id, from_chat_id=KINO_BAZA_KANAL, message_id=post_id)
        await temp_msg.delete()
    except Exception:
        await temp_msg.edit_text("❌ Kino topilmadi. Kodni tekshiring.")

# ================= HANDLERLAR =================
@dp.channel_post(F.chat.username == KINO_KANAL_USER)
async def new_movie_notification(message: Message):
    msg_id = message.message_id
    bot_info = await bot.me()
    xabar = (f"🔔 <b>YANGI KINO!</b>\n🆔 Kodi: <code>{msg_id}</code>\n"
             f"🔗 Link: https://t.me/{bot_info.username}?start={msg_id}")
    try: await bot.send_message(chat_id=ADMIN_ID, text=xabar, parse_mode="HTML")
    except: pass

@dp.message(CommandStart())
async def start_handler(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user_qushish(user_id)
    arg = command.args
    if not await check_all_subs(user_id):
        await majburiy_obuna_xabari(message, arg)
        return
    if arg and arg.isdigit():
        await send_movie(message, arg)
    else:
        await message.answer("✅ Xush kelibsiz! Kino kodini yozing:", reply_markup=main_menu)

@dp.message(F.text == "🔗 Do'stlarni chaqirish")
async def share_link_handler(message: Message):
    bot_info = await bot.me()
    link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    share_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↗️ Do'stlarga yuborish", url=f"https://t.me/share/url?url={link}&text=Zo'r kino bot ekan, kirib ko'r:")]
    ])
    await message.answer("👇 Pastdagi tugmani bosing va do'stlaringizni tanlang:", reply_markup=share_button)

@dp.message(Command("send"))
async def send_handler(message: Message):
    if message.from_user.id != ADMIN_ID: return
    if not message.reply_to_message:
        await message.answer("⚠️ Reklama uchun xabarga REPLY qiling.")
        return
    users = hamma_userlar()
    sent_msg = await message.answer(f"🚀 Reklama ketdi ({len(users)} user)...")
    count = 0
    for user in users:
        try:
            await message.reply_to_message.copy_to(chat_id=user)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await sent_msg.edit_text(f"✅ Tugadi. Bordi: {count}")

@dp.message(Command("stat"))
async def stat_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        users = hamma_userlar()
        await message.answer(f"📊 Jami userlar: {len(users)}")

@dp.message(F.text == "🎲 Tasodifiy kino")
async def random_movie(message: Message):
    user_id = message.from_user.id
    if not await check_all_subs(user_id):
        await majburiy_obuna_xabari(message)
        return
    rand_code = random.randint(1, ENG_OXIRGI_KINO_ID)
    await message.answer(f"🎲 Tavakkal kod: **{rand_code}**")
    await send_movie(message, rand_code)

@dp.message(F.text == "✍️ Adminga yozish")
async def contact_admin(message: Message, state: FSMContext):
    await message.answer("📝 Xabarni yozing:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminAloqa.xabar_kutish)

@dp.message(AdminAloqa.xabar_kutish)
async def forward_to_admin(message: Message, state: FSMContext):
    try:
        await bot.forward_message(chat_id=ADMIN_ID, from_chat_id=message.chat.id, message_id=message.message_id)
        await message.answer("✅ Yuborildi!", reply_markup=main_menu)
    except:
        await message.answer("❌ Xatolik.", reply_markup=main_menu)
    await state.clear()

@dp.message(F.text)
async def text_handler(message: Message):
    user_id = message.from_user.id
    text = message.text
    if not await check_all_subs(user_id):
        kod = text if text.isdigit() else None
        await majburiy_obuna_xabari(message, kod)
        return
    if text.isdigit():
        await send_movie(message, text)
    else:
        if user_id == ADMIN_ID and message.reply_to_message:
            try:
                if message.reply_to_message.forward_from:
                    user_chat_id = message.reply_to_message.forward_from.id
                    await bot.copy_message(chat_id=user_chat_id, from_chat_id=message.chat.id, message_id=message.message_id)
                    await message.answer("✅ Javob ketdi.")
                else: await message.answer("⚠️ ID topilmadi.")
            except: await message.answer(f"❌ Xatolik")
        elif user_id != ADMIN_ID:
            await message.answer("❌ Faqat kino kodini yuboring.", reply_markup=main_menu)

@dp.callback_query(F.data.startswith("check_"))
async def check_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data.split("_")[1]
    if await check_all_subs(user_id):
        await callback.message.delete()
        if data != "no": await send_movie(callback.message, data)
        else: await callback.message.answer("✅ Obuna tasdiqlandi!", reply_markup=main_menu)
    else: await callback.answer("❌ Hali to'liq a'zo bo'lmadingiz!", show_alert=True)

# ================= SERVER VA BOTNI BIRGA ISHLATISH =================

async def handle(request):
    return web.Response(text="Bot ishlab turibdi! (Alive)")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    # Portni server o'zi beradi, yoki 8080 ni oladi
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main():
    baza_ulanish()
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Ikkalasini bir vaqtda ishga tushiramiz: Bot + Web Sayt
    await asyncio.gather(
        dp.start_polling(bot),
        start_web_server()
    )

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtadi")