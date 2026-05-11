"""
ربات آزمون کتاب ۱۲ فصله
نصب: pip install python-telegram-bot==20.7
"""

import os, json, time, random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler

# ══════════════════════════════════════════════
#  ⚙️  تنظیمات — اینجا رو تغییر بده
# ══════════════════════════════════════════════
BOT_TOKEN   = "توکن_ربات_خودت_را_اینجا_بگذار"
ADMIN_IDS   = [123456789]   # آیدی عددی تلگرام خودت
BOOK_TITLE  = "نام کتاب شما"
NUM_CHAPTERS = 12
# ══════════════════════════════════════════════

QUESTIONS_FILE = "questions.json"
RESULTS_FILE   = "results.json"

# state های مکالمه
MAIN_MENU, CHAPTER_MENU, IN_EXAM, WAITING_NAME = range(4)


# ──────────────────────────────────────────────
# بارگذاری و ذخیره داده
# ──────────────────────────────────────────────
def load_questions():
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []

def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_results(results):
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

def is_admin(uid): return uid in ADMIN_IDS


# ──────────────────────────────────────────────
# منوی اصلی
# ──────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    keyboard = [
        ["📚 آزمون فصل‌به‌فصل"],
        ["📝 آزمون کل کتاب"],
        ["📊 نتایج من"],
        ["ℹ️ راهنما"]
    ]
    if is_admin(update.effective_user.id):
        keyboard.append(["👑 پنل مدیریت"])

    await update.message.reply_text(
        f"📖 به ربات آزمون «{BOOK_TITLE}» خوش اومدی!\n\n"
        "یکی از گزینه‌ها رو انتخاب کن:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return MAIN_MENU


# ──────────────────────────────────────────────
# آزمون فصل‌به‌فصل
# ──────────────────────────────────────────────
async def chapter_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()

    # پیدا کردن فصل‌های موجود
    chapters = {}
    for q in questions:
        ch = q.get("chapter", 0)
        title = q.get("chapter_title", f"فصل {ch}")
        if ch not in chapters:
            chapters[ch] = {"title": title, "count": 0}
        chapters[ch]["count"] += 1

    if not chapters:
        await update.message.reply_text("❌ هنوز سوالی اضافه نشده.")
        return MAIN_MENU

    # ساخت دکمه‌های فصل‌ها
    buttons = []
    for ch in sorted(chapters.keys()):
        info = chapters[ch]
        buttons.append([InlineKeyboardButton(
            f"📌 {info['title']}  ({info['count']} سوال)",
            callback_data=f"chapter|{ch}"
        )])
    buttons.append([InlineKeyboardButton("🎲 فصل تصادفی", callback_data="chapter|random")])

    await update.message.reply_text(
        "کدام فصل؟",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHAPTER_MENU


async def chapter_selected(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, val = query.data.split("|")

    questions = load_questions()
    if val == "random":
        chapters = list({q["chapter"] for q in questions})
        val = str(random.choice(chapters))

    chapter_qs = [q for q in questions if str(q.get("chapter")) == val]
    if not chapter_qs:
        await query.message.reply_text("سوالی برای این فصل وجود ندارد.")
        return MAIN_MENU

    ctx.user_data["exam_questions"] = random.sample(chapter_qs, len(chapter_qs))
    ctx.user_data["exam_mode"]      = f"فصل {val}"

    await query.edit_message_text(
        f"✅ {len(chapter_qs)} سوال از فصل {val} آماده‌ست.\nاسمت رو بنویس:"
    )
    return WAITING_NAME


# ──────────────────────────────────────────────
# آزمون کل کتاب
# ──────────────────────────────────────────────
async def full_exam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    if not questions:
        await update.message.reply_text("❌ سوالی ثبت نشده.")
        return MAIN_MENU

    # انتخاب ۲۰ سوال تصادفی از همه فصل‌ها
    sample = random.sample(questions, min(20, len(questions)))
    ctx.user_data["exam_questions"] = sample
    ctx.user_data["exam_mode"]      = "کل کتاب"

    await update.message.reply_text(
        f"📝 آزمون کل کتاب — {len(sample)} سوال از فصل‌های مختلف\n\nاسمت رو بنویس:",
        reply_markup=ReplyKeyboardRemove()
    )
    return WAITING_NAME


# ──────────────────────────────────────────────
# شروع آزمون
# ──────────────────────────────────────────────
async def got_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["student_name"] = update.message.text.strip()
    ctx.user_data["current_q"]    = 0
    ctx.user_data["answers"]      = {}
    ctx.user_data["start_time"]   = time.time()
    ctx.user_data["exam_done"]    = False

    n = len(ctx.user_data["exam_questions"])
    await update.message.reply_text(
        f"✅ سلام {ctx.user_data['student_name']}!\n"
        f"آزمون {ctx.user_data.get('exam_mode','')} شروع شد.\n"
        f"تعداد سوالات: {n}\n\n"
        "موفق باشی! 🍀"
    )
    await send_question(update, ctx)
    return IN_EXAM


async def send_question(update, ctx):
    questions = ctx.user_data["exam_questions"]
    idx       = ctx.user_data["current_q"]

    if idx >= len(questions):
        await finish_exam(update, ctx)
        return

    q = questions[idx]
    chapter_info = f"📌 {q.get('chapter_title', '')}\n" if q.get("chapter_title") else ""
    text = (
        f"{chapter_info}"
        f"❓ سوال {idx + 1} از {len(questions)}\n\n"
        f"{q['text']}"
    )
    buttons = [[InlineKeyboardButton(
        f"{k}) {v}", callback_data=f"ans|{idx}|{k}"
    )] for k, v in q["options"].items()]

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


async def handle_answer(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if ctx.user_data.get("exam_done"):
        return IN_EXAM

    _, q_idx_str, chosen = query.data.split("|")
    q_idx   = int(q_idx_str)
    current = ctx.user_data["current_q"]

    if q_idx != current:
        return IN_EXAM

    questions = ctx.user_data["exam_questions"]
    q = questions[q_idx]
    correct = q["answer"].upper()
    chosen  = chosen.upper()
    ctx.user_data["answers"][q_idx] = chosen

    if chosen == correct:
        feedback = f"✅ درست! +{q.get('score', 1)} نمره"
    else:
        feedback = f"❌ غلط!\nجواب درست: {correct}) {q['options'][correct]}"

    # توضیح اضافی (اگه وجود داشت)
    if q.get("explanation"):
        feedback += f"\n\n💡 {q['explanation']}"

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(feedback)

    ctx.user_data["current_q"] += 1
    await send_question(update, ctx)
    return IN_EXAM


# ──────────────────────────────────────────────
# پایان آزمون
# ──────────────────────────────────────────────
async def finish_exam(update, ctx):
    ctx.user_data["exam_done"] = True
    questions = ctx.user_data["exam_questions"]
    answers   = ctx.user_data.get("answers", {})
    name      = ctx.user_data.get("student_name", "ناشناس")
    mode      = ctx.user_data.get("exam_mode", "")

    total_score = max_score = correct_cnt = 0
    for i, q in enumerate(questions):
        s = q.get("score", 1)
        max_score += s
        if answers.get(i, "").upper() == q["answer"].upper():
            total_score += s
            correct_cnt += 1

    elapsed = int(time.time() - ctx.user_data.get("start_time", 0))
    pct = round(total_score / max_score * 100) if max_score else 0

    if pct >= 85:   medal = "🥇 عالی!"
    elif pct >= 70: medal = "🥈 خوب!"
    elif pct >= 50: medal = "🥉 قابل قبول"
    else:           medal = "📚 باید بیشتر مطالعه کنی"

    result_text = (
        f"🎓 آزمون {mode} تموم شد!\n\n"
        f"👤 {name}\n"
        f"✅ {correct_cnt} درست از {len(questions)} سوال\n"
        f"⭐ نمره: {total_score}/{max_score}\n"
        f"📊 درصد: {pct}%\n"
        f"⏱ زمان: {elapsed // 60}:{elapsed % 60:02d}\n\n"
        f"{medal}"
    )

    # ذخیره نتیجه
    results = load_results()
    uid = str(update.effective_user.id)
    results.setdefault(uid, []).append({
        "name": name, "mode": mode, "score": total_score,
        "max": max_score, "pct": pct, "correct": correct_cnt,
        "total": len(questions),
        "date": time.strftime("%Y-%m-%d %H:%M")
    })
    save_results(results)

    keyboard = [["📚 آزمون فصل‌به‌فصل"], ["📝 آزمون کل کتاب"],
                ["📊 نتایج من"], ["ℹ️ راهنما"]]
    if is_admin(update.effective_user.id):
        keyboard.append(["👑 پنل مدیریت"])

    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(
        result_text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# ──────────────────────────────────────────────
# نتایج کاربر
# ──────────────────────────────────────────────
async def my_results(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    results = load_results()
    uid = str(update.effective_user.id)
    history = results.get(uid, [])

    if not history:
        await update.message.reply_text("📭 هنوز آزمونی نداده‌ای!")
        return MAIN_MENU

    text = "📊 آخرین آزمون‌های تو:\n\n"
    for r in history[-5:]:
        text += f"📌 {r.get('mode','')} — {r['pct']}% — {r['date']}\n"
    await update.message.reply_text(text)
    return MAIN_MENU


# ──────────────────────────────────────────────
# راهنما
# ──────────────────────────────────────────────
async def help_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"📖 ربات آزمون «{BOOK_TITLE}»\n\n"
        "🔹 آزمون فصل‌به‌فصل: از یک فصل خاص سوال بزن\n"
        "🔹 آزمون کل کتاب: ۲۰ سوال تصادفی از همه فصل‌ها\n"
        "🔹 بعد از هر جواب، توضیح می‌بینی\n"
        "🔹 نتایج ذخیره می‌شه\n\n"
        "موفق باشی! 🍀"
    )
    return MAIN_MENU


# ──────────────────────────────────────────────
# پنل ادمین
# ──────────────────────────────────────────────
async def admin_panel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return MAIN_MENU

    questions = load_questions()
    results   = load_results()

    # آمار فصل‌ها
    chapters = {}
    for q in questions:
        ch = q.get("chapter", 0)
        chapters[ch] = chapters.get(ch, 0) + 1

    stats = "\n".join([f"  فصل {k}: {v} سوال" for k, v in sorted(chapters.items())])
    total_users = len(results)
    total_exams = sum(len(v) for v in results.values())

    await update.message.reply_text(
        f"👑 پنل مدیریت\n\n"
        f"📚 سوالات:\n{stats or '  (خالی)'}\n\n"
        f"👥 کاربران: {total_users}\n"
        f"📝 آزمون‌های برگزار شده: {total_exams}\n\n"
        "برای افزودن سوال، فایل questions.json رو ویرایش کن."
    )
    return MAIN_MENU


# ──────────────────────────────────────────────
# راه‌اندازی
# ──────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^🏠"), start),
        ],
        states={
            MAIN_MENU: [
                MessageHandler(filters.Regex("^📚 آزمون فصل‌به‌فصل$"), chapter_menu),
                MessageHandler(filters.Regex("^📝 آزمون کل کتاب$"),    full_exam),
                MessageHandler(filters.Regex("^📊 نتایج من$"),          my_results),
                MessageHandler(filters.Regex("^ℹ️ راهنما$"),            help_text),
                MessageHandler(filters.Regex("^👑 پنل مدیریت$"),        admin_panel),
            ],
            CHAPTER_MENU: [
                CallbackQueryHandler(chapter_selected, pattern=r"^chapter\|"),
            ],
            IN_EXAM: [
                CallbackQueryHandler(handle_answer, pattern=r"^ans\|"),
            ],
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, got_name),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    print(f"✅ ربات «{BOOK_TITLE}» فعال شد...")
    app.run_polling()


if __name__ == "__main__":
    main()
