"""
Advance Quiz Bot — Pyrogram Quiz Execution Engine
Handles:
1. /start <qid> deep-links (shows Quiz Card + Play WebApp + Start Polls buttons)
2. Interactive Group/PM Quiz Poll Session loop (/quiz <qid>, callback start_quiz_polls_<qid>)
3. /stop, /skip, /leaderboard
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any

from pyrogram import Client, filters
from pyrogram.enums import PollType
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from quizbot.database import QuizRepository, LeaderboardRepository, get_db
from quizbot.shared import config
from quizbot.shared.mini_app_link import mini_app_play_url

logger = logging.getLogger(__name__)

# Active chat sessions: chat_id -> session dict
active_quiz_sessions: Dict[int, Dict[str, Any]] = {}


async def handle_start_quiz_param(c: Client, m: Message, qid: str) -> bool:
    """Handle /start <qid> deep-link payload. Returns True if handled as a quiz lookup."""
    clean_qid = qid.strip()
    if clean_qid.startswith("play_"):
        clean_qid = clean_qid.split("_")[1] if len(clean_qid.split("_")) > 1 else clean_qid
    elif clean_qid.startswith("quiz_"):
        clean_qid = clean_qid.split("_")[1] if len(clean_qid.split("_")) > 1 else clean_qid

    quiz_repo = QuizRepository(get_db())
    quiz = await quiz_repo.get(clean_qid)
    if not quiz:
        import re
        from quizbot.database.repositories import _clean
        row = await quiz_repo.col.find_one({"qid": {"$regex": f"^{re.escape(clean_qid)}$", "$options": "i"}})
        quiz = _clean(row)
    
    if not quiz:
        return False

    quiz_name = quiz.get("quiz_name", "Quiz")
    questions = quiz.get("questions", [])
    timer = quiz.get("timer", 20)
    quiz_type = quiz.get("quiz_type", "free")

    text = (
        f"📋 **Quiz Details**\n\n"
        f"📝 **Name:** {quiz_name}\n"
        f"❓ **Questions:** {len(questions)}\n"
        f"⏱️ **Timer:** {timer}s per question\n"
        f"🆔 **Quiz ID:** `{clean_qid}`\n"
        f"📊 **Type:** `{quiz_type}`\n\n"
        f"Choose how you want to play below:"
    )

    buttons = []
    
    # WebApp button if domain configured
    play_url = mini_app_play_url(clean_qid, "practice")
    if play_url:
        from pyrogram.types import WebAppInfo
        buttons.append([InlineKeyboardButton("🎮 Play in Web App (Interactive)", web_app=WebAppInfo(url=play_url))])

    # Start Quiz Polls button
    buttons.append([InlineKeyboardButton("🚀 Start Quiz Polls in Telegram", callback_data=f"start_polls_{clean_qid}")])
    
    # Share / HTML report buttons
    buttons.append([
        InlineKeyboardButton("🔗 Share Quiz", switch_inline_query=clean_qid),
        InlineKeyboardButton("📊 HTML Report", callback_data=f"gen_whtml_{clean_qid}")
    ])

    await m.reply(text, reply_markup=InlineKeyboardMarkup(buttons))
    return True


async def start_polls_callback(c: Client, cb: CallbackQuery) -> None:
    """Handle callback_data `start_polls_<qid>`."""
    qid = cb.data.replace("start_polls_", "").strip()
    chat_id = cb.message.chat.id
    
    quiz_repo = QuizRepository(get_db())
    quiz = await quiz_repo.get(qid)
    if not quiz:
        import re
        from quizbot.database.repositories import _clean
        row = await quiz_repo.col.find_one({"qid": {"$regex": f"^{re.escape(qid)}$", "$options": "i"}})
        quiz = _clean(row)

    if not quiz:
        await cb.answer("❌ Quiz not found!", show_alert=True)
        return

    questions = quiz.get("questions", [])
    if not questions:
        await cb.answer("⚠️ This quiz has no questions!", show_alert=True)
        return

    if chat_id in active_quiz_sessions and not active_quiz_sessions[chat_id].get("stopped", True):
        await cb.answer("⚠️ A quiz is already running in this chat!", show_alert=True)
        return

    await cb.answer("🚀 Starting Quiz...")
    await _start_quiz_session(c, chat_id, quiz)


async def quiz_cmd(c: Client, m: Message) -> None:
    """/quiz <qid> -- launch quiz in group or PM."""
    chat_id = m.chat.id
    parts = m.text.strip().split(maxsplit=1)
    
    if len(parts) < 2:
        await m.reply(
            "ℹ️ **Usage:** `/quiz <QUIZ_ID>`\n\n"
            "Example: `/quiz GGN123456`\n"
            "Use `/list` to view your created quiz IDs."
        )
        return

    qid = parts[1].strip()
    quiz_repo = QuizRepository(get_db())
    quiz = await quiz_repo.get(qid)
    if not quiz:
        import re
        from quizbot.database.repositories import _clean
        row = await quiz_repo.col.find_one({"qid": {"$regex": f"^{re.escape(qid)}$", "$options": "i"}})
        quiz = _clean(row)
    
    if not quiz:
        await m.reply("❌ **Quiz not found!** Check the Quiz ID and try again.")
        return

    questions = quiz.get("questions", [])
    if not questions:
        await m.reply("⚠️ **This quiz has no questions.**")
        return

    if chat_id in active_quiz_sessions and not active_quiz_sessions[chat_id].get("stopped", True):
        await m.reply("⚠️ **A quiz is already running in this chat!** Use `/stop` to stop it first.")
        return

    await _start_quiz_session(c, chat_id, quiz)


async def _start_quiz_session(c: Client, chat_id: int, quiz: dict) -> None:
    qid = quiz.get("qid")
    quiz_name = quiz.get("quiz_name", "Quiz")
    questions = quiz.get("questions", [])
    timer = max(5, int(quiz.get("timer", 20)))

    session = {
        "qid": qid,
        "quiz_name": quiz_name,
        "questions": questions,
        "timer": timer,
        "stopped": False,
        "skip_event": asyncio.Event(),
        "scores": {},
    }
    active_quiz_sessions[chat_id] = session

    # Increment participants count
    await QuizRepository(get_db()).increment_participants(qid)

    asyncio.create_task(_run_quiz_loop(c, chat_id, session))


async def _run_quiz_loop(c: Client, chat_id: int, session: dict) -> None:
    quiz_name = session["quiz_name"]
    questions = session["questions"]
    total_q = len(questions)
    timer = session["timer"]

    await c.send_message(
        chat_id,
        f"🚀 **Quiz Starting Now!**\n\n"
        f"📝 **Name:** {quiz_name}\n"
        f"❓ **Total Questions:** {total_q}\n"
        f"⏱️ **Timer per Question:** {timer} seconds\n\n"
        f"First question in 3 seconds..."
    )
    await asyncio.sleep(3)

    for i, q in enumerate(questions, 1):
        if session.get("stopped"):
            break

        session["skip_event"].clear()
        txt = q.get("question", f"Question {i}")
        options = [str(opt)[:99] for opt in q.get("options", [])[:10]]
        correct_id = int(q.get("correct_option_id", 0))
        exp = q.get("explanation", "")

        if len(options) < 2:
            continue

        try:
            await c.send_poll(
                chat_id=chat_id,
                question=f"[{i}/{total_q}] {txt}"[:290],
                options=options,
                is_anonymous=False,
                type=PollType.QUIZ,
                correct_option_id=correct_id if correct_id < len(options) else 0,
                explanation=exp[:190] if exp else None,
                open_period=min(600, max(5, timer)),
            )
        except Exception as err:
            logger.error(f"Failed to send poll in {chat_id}: {err}")

        try:
            await asyncio.wait_for(session["skip_event"].wait(), timeout=timer)
        except asyncio.TimeoutError:
            pass

        if session.get("stopped"):
            break

    active_quiz_sessions.pop(chat_id, None)
    await c.send_message(chat_id, f"🏁 **Quiz Completed: {quiz_name}!**\n\nThank you for participating!")


async def stop_cmd(c: Client, m: Message) -> None:
    """/stop -- stop active quiz in chat."""
    chat_id = m.chat.id
    if chat_id in active_quiz_sessions:
        active_quiz_sessions[chat_id]["stopped"] = True
        active_quiz_sessions[chat_id]["skip_event"].set()
        active_quiz_sessions.pop(chat_id, None)
        await m.reply("🛑 **Quiz session stopped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def skip_cmd(c: Client, m: Message) -> None:
    """/skip -- skip current question."""
    chat_id = m.chat.id
    if chat_id in active_quiz_sessions:
        active_quiz_sessions[chat_id]["skip_event"].set()
        await m.reply("⏭️ **Question skipped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def gen_whtml_cb(c: Client, cb: CallbackQuery) -> None:
    """Handle callback_data `gen_whtml_<qid>`."""
    qid = cb.data.replace("gen_whtml_", "").strip()
    await cb.answer("⚡ Generating HTML Report...")
    from quizbot.shared.html.quiz_report import generate_quiz_report_html
    quiz = await QuizRepository(get_db()).get(qid)
    if not quiz:
        await cb.message.reply("❌ Quiz not found.")
        return
    doc, filename = generate_quiz_report_html(quiz)
    import io
    bio = io.BytesIO(doc)
    bio.name = filename
    await cb.message.reply_document(document=bio, caption=f"📊 **Interactive HTML Report** for `{qid}`")


def register(app: Client) -> None:
    app.on_message(filters.command("quiz"))(quiz_cmd)
    app.on_message(filters.command("stop"))(stop_cmd)
    app.on_message(filters.command("skip"))(skip_cmd)
    app.on_callback_query(filters.regex(r"^start_polls_"))(start_polls_callback)
    app.on_callback_query(filters.regex(r"^gen_whtml_"))(gen_whtml_cb)
