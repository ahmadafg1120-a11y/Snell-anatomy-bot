import requests
import json
import os
from datetime import datetime, timezone

# ═══════════════════════════════════════════
#   تنظیمات — از GitHub Secrets می‌آید
# ═══════════════════════════════════════════
BOT_TOKEN  = os.environ.get("SNELL_BOT_TOKEN")
CHANNEL_ID = os.environ.get("SNELL_CHANNEL_ID")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def load_highlights():
    with open("snell_ch1_highlights.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_highlight_index(total):
    start_date = datetime(2025, 8, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    hours_elapsed = int((now - start_date).total_seconds() / 3600)
    period = hours_elapsed // 6  # هر ۶ ساعت یک نکته
    return period % total

def send_message(text):
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=data)
    return response.json()

def format_highlight(h, index, total):
    return (
        f"📚 <b>Snell Clinical Anatomy — Chapter 1</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔹 <b>{h['topic']}</b>\n\n"
        f"{h['highlight']}\n\n"
        f"{h['mnemonic']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔢 Highlight {index + 1} of {total}\n\n"
        f"@snellbookquiz"
    )

def main():
    highlights = load_highlights()
    total = len(highlights)
    idx = get_highlight_index(total)
    h = highlights[idx]

    message = format_highlight(h, idx, total)
    result = send_message(message)
    print(f"Sent highlight {h['id']} — {h['topic']}: {result.get('ok')}")

if __name__ == "__main__":
    main()
