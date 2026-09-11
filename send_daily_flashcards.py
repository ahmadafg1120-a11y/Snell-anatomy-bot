"""
send_daily_flashcards.py

اسکریپتی برای ارسال روزانه‌ی ۲ فلش‌کارد بیوشیمی از فایل
biochemistry_flashcards.json به یک گروه تلگرام.

نحوه کار:
- فایل JSON خوانده می‌شود (۶۰ کارت، هر روز ۲ تا بر اساس فیلد "day").
- بر اساس شمارنده‌ی روز (ذخیره‌شده در flashcard_state.json) کارت‌های
  همان روز پیدا می‌شوند.
- هر کارت به‌صورت جداگانه با فرمت "جلو" و "پشت" (با اسپویلر تلگرام
  برای مخفی کردن جواب تا کاربر روی آن ضربه بزند) ارسال می‌شود.
- شمارنده برای روز بعد افزایش می‌یابد؛ بعد از روز ۳۰ دوباره از ۱ شروع
  می‌شود (چرخشی).

اجرای خودکار روزانه: با یک GitHub Actions workflow مشابه daily-pearl.yml
(اما با اسکریپت و secret های مربوط به گروه).
"""

import json
import os
from datetime import datetime, timezone

from telegram import Bot  # pip install python-telegram-bot

# ---------- تنظیمات ----------
BOT_TOKEN = os.environ["BOT_TOKEN"]          # همان توکن ربات
GROUP_ID = os.environ["GROUP_ID"]            # chat_id عددی گروه (مثلا -1001234567890)
                                              # یا username اگر گروه پابلیک با لینک @ باشد

CARDS_FILE = os.path.join(os.path.dirname(__file__), "biochemistry_flashcards.json")
STATE_FILE = os.path.join(os.path.dirname(__file__), "flashcard_state.json")


def load_cards():
    with open(CARDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["flashcards"]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {"next_day": 1}
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def format_card(card: dict) -> str:
    return (
        f"🧪 <b>Biochem Flashcard #{card['id']}</b>\n"
        f"📂 <b>{card['category']}</b>\n\n"
        f"❓ <b>Q:</b> {card['front']}\n\n"
        f"💡 <b>A:</b> <tg-spoiler>{card['back']}</tg-spoiler>"
    )


async def send_daily_flashcards():
    cards = load_cards()
    state = load_state()

    total_days = max(c["day"] for c in cards)
    current_day = ((state["next_day"] - 1) % total_days) + 1

    todays_cards = [c for c in cards if c["day"] == current_day]

    if not todays_cards:
        print(f"[WARN] No cards found for day {current_day}")
        return

    bot = Bot(token=BOT_TOKEN)

    for card in todays_cards:
        message = format_card(card)
        await bot.send_message(
            chat_id=GROUP_ID,
            text=message,
            parse_mode="HTML",
        )
        print(f"[OK] Sent card #{card['id']} (day {current_day}, {card['category']})")

    state["next_day"] = current_day + 1
    state["last_sent_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)


if __name__ == "__main__":
    import asyncio

    asyncio.run(send_daily_flashcards())
