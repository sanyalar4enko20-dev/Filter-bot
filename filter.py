import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(TOKEN)
dp = Dispatcher()

# ===== БАЗА =====

conn = sqlite3.connect("filters.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS filters (
    chat_id INTEGER,
    word TEXT
)
""")
conn.commit()


# ===== ФУНКЦИИ БД =====

def add_filter(chat_id: int, word: str):
    cursor.execute(
        "INSERT INTO filters (chat_id, word) VALUES (?, ?)",
        (chat_id, word.lower())
    )
    conn.commit()


def remove_filter(chat_id: int, word: str):
    cursor.execute(
        "DELETE FROM filters WHERE chat_id = ? AND word = ?",
        (chat_id, word.lower())
    )
    conn.commit()


def get_filters(chat_id: int):
    cursor.execute(
        "SELECT word FROM filters WHERE chat_id = ?",
        (chat_id,)
    )
    return [row[0] for row in cursor.fetchall()]


# ===== ПРОВЕРКА АДМИНА =====

async def is_admin(message: types.Message):
    member = await message.chat.get_member(message.from_user.id)
    return member.status in ["administrator", "creator"]


# ===== СТАРТ =====

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить в группу",
                    url=f"https://t.me/{(await bot.me()).username}?startgroup=true"
                )
            ]
        ]
    )

    await message.answer(
        "👮 Бот фильтрации слов\n\n"
        "📌 Команды:\n"
        "+фильтр слово слово — добавить слова (только админ)\n"
        "-фильтр слово — удалить слова (только админ)\n"
        "фильтр — показать список слов\n\n"
        "⚠ Если пользователь напишет запрещённое слово — он будет забанен.",
        reply_markup=keyboard
    )


# ===== +ФИЛЬТР (ТОЛЬКО АДМИН) =====

@dp.message(F.text.startswith("+фильтр"))
async def add_filter_cmd(message: types.Message):
    if message.chat.type == "private":
        return

    if not await is_admin(message):
        await message.reply("❌ Только администраторы могут добавлять фильтр.")
        return

    words = message.text.split()[1:]
    if not words:
        await message.reply("Укажи слова.")
        return

    for word in words:
        add_filter(message.chat.id, word)

    await message.reply("✅ Слова добавлены в фильтр.")


# ===== -ФИЛЬТР (ТОЛЬКО АДМИН) =====

@dp.message(F.text.startswith("-фильтр"))
async def remove_filter_cmd(message: types.Message):
    if message.chat.type == "private":
        return

    if not await is_admin(message):
        await message.reply("❌ Только администраторы могут удалять фильтр.")
        return

    words = message.text.split()[1:]
    if not words:
        await message.reply("Укажи слова.")
        return

    current_words = get_filters(message.chat.id)

    removed = []
    not_found = []

    for word in words:
        word = word.lower()
        if word in current_words:
            remove_filter(message.chat.id, word)
            removed.append(word)
        else:
            not_found.append(word)

    response = ""

    if removed:
        response += "✅ Удалено:\n" + "\n".join(removed) + "\n\n"

    if not_found:
        response += "⚠ Не найдено в фильтре:\n" + "\n".join(not_found)

    await message.reply(response.strip())

# ===== ПОКАЗАТЬ СПИСОК (ВСЕ МОГУТ) =====

@dp.message(F.text.lower() == "фильтр")
async def list_filters(message: types.Message):
    if message.chat.type == "private":
        return

    words = get_filters(message.chat.id)

    if not words:
        await message.reply("📭 Фильтр пуст.")
        return

    await message.reply("🚫 Фильтр:\n" + "\n".join(words))


# ===== ПРОВЕРКА СООБЩЕНИЙ =====

@dp.message()
async def check_message(message: types.Message):
    if message.chat.type == "private":
        return

    if not message.text:
        return

    words = get_filters(message.chat.id)
    text = message.text.lower()

    matched_words = [word for word in words if word in text]

    if matched_words:
        try:
            await message.delete()
            await message.chat.ban(message.from_user.id)

            if len(matched_words) == 1:
                reason_text = "запрещённое слово"
            else:
                reason_text = "запрещённые слова"

            await message.answer(
                f"🚫 Пользователь {message.from_user.full_name} "
                f"забанен за {reason_text}: "
                f"{', '.join(matched_words)}"
            )
        except:
            pass

# ===== ЗАПУСК =====

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
