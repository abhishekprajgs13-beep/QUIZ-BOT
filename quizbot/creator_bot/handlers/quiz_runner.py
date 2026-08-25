"""
Advance Quiz Bot — Pyrogram Quiz Runner Engine
Handles /quiz <qid>, interactive Telegram Poll quizzes, answers, scoring, /stop, /skip, and /leaderboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any

from pyrogram import Client, filters
from pyrogram.enums import PollType
from pyrogram.types import Message, PollAnswer, InlineKeyboardButton, InlineKeyboardMarkup

from quizbot.database import (
    QuizRepository,
    LeaderboardRepository,
    AttemptRepository,
    get_db,
)
from quizbot.shared import config
from quizbot.shared.mini_app_link import mini_app_web_app_button

logger = logging.getLogger(__name__)

# Active group quiz sessions: chat_id -> session dict
active_sessions: Dict[int, Dict[str, Any]] = {}

# Active poll mapping: poll_id -> poll_metadata dict
active_polls: Dict[str, Dict[str, Any]] = {}


async def quiz_cmd(c: Client, m: Message) -> None:
    """/quiz <qid> -- launch a quiz session in this chat or group."""
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
        await m.reply("❌ **Quiz not found!** Check the Quiz ID and try again.")
        return

    questions = quiz.get("questions", [])
    if not questions:
        await m.reply("⚠️ **This quiz has no questions.**")
        return

    if chat_id in active_sessions and not active_sessions[chat_id].get("stopped", True):
        await m.reply("⚠️ **A quiz is already running in this chat!** Use `/stop` to stop it first.")
        return

    # Create new session
    session = {
        "qid": qid,
        "quiz_name": quiz.get("quiz_name", "Quiz"),
        "questions": questions,
        "timer": max(5, int(quiz.get("timer", 20))),
        "current_index": 0,
        "stopped": False,
        "skip_event": asyncio.Event(),
        "scores": {},  # user_id -> {"name": name, "correct": 0, "total_time": 0}
        "start_time": time.time(),
    }
    active_sessions[chat_id] = session

    # Increment participants count
    await quiz_repo.increment_participants(qid)

    # Launch background task for quiz loop
    asyncio.create_task(_run_quiz_loop(c, chat_id, session))


async def _run_quiz_loop(c: Client, chat_id: int, session: dict) -> None:
    """Send quiz questions sequentially as real Telegram Polls."""
    quiz_name = session["quiz_name"]
    questions = session["questions"]
    total_q = len(questions)
    timer = session["timer"]
    qid = session["qid"]

    await c.send_message(
        chat_id,
        f"🚀 **Quiz Starting Now!**\n\n"
        f"📝 **Name:** {quiz_name}\n"
        f"❓ **Total Questions:** {total_q}\n"
        f"⏱️ **Timer per Question:** {timer} seconds\n\n"
        f"Get ready! First question in 3 seconds..."
    )
    await asyncio.sleep(3)

    for i, q in enumerate(questions, 1):
        if session.get("stopped"):
            break

        session["current_index"] = i
        session["skip_event"].clear()

        txt = q.get("question", f"Question {i}")
        options = [str(opt) for opt in q.get("options", [])]
        correct_id = int(q.get("correct_option_id", 0))
        exp = q.get("explanation", "")

        # Truncate for Telegram Poll limits
        poll_question = f"[{i}/{total_q}] {txt}"[:290]
        poll_options = [opt[:99] for opt in options[:10]]
        if len(poll_options) < 2:
            continue

        try:
            poll_msg = await c.send_poll(
                chat_id=chat_id,
                question=poll_question,
                options=poll_options,
                is_anonymous=False,
                type=PollType.QUIZ,
                correct_option_id=correct_id if correct_id < len(poll_options) else 0,
                explanation=exp[:190] if exp else None,
                open_period=min(600, max(5, timer)),
            )

            if poll_msg and poll_msg.poll:
                poll_id = poll_msg.poll.id
                active_polls[poll_id] = {
                    "chat_id": chat_id,
                    "qid": qid,
                    "q_index": i,
                    "correct_id": correct_id,
                    "sent_at": time.time(),
                }
        except Exception as err:
            logger.error(f"Failed to send poll in {chat_id}: {err}")

        # Wait for timer or skip event
        try:
            await asyncio.wait_for(session["skip_event"].wait(), timeout=timer)
        except asyncio.TimeoutError:
            pass

        if session.get("stopped"):
            break

    # Quiz Session Finished
    active_sessions.pop(chat_id, None)
    
    # Calculate leaderboard text
    scores = session.get("scores", {})
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["correct"], reverse=True)

    lb_text = f"🏆 **Quiz Finished: {quiz_name}**\n\n"
    if sorted_scores:
        lb_text += "🏅 **Final Leaderboard:**\n"
        medals = ["🥇", "🥈", "🥉"]
        for rank, (uid, uinfo) in enumerate(sorted_scores[:10], 1):
            icon = medals[rank - 1] if rank <= 3 else f"#{rank}"
            lb_text += f"{icon} **{uinfo['name']}** — {uinfo['correct']}/{total_q} correct\n"
    else:
        lb_text += "No participants answered in time."

    await c.send_message(chat_id, lb_text)


async def poll_answer_cb(c: Client, pa: PollAnswer) -> None:
    """Track user poll answers and record scores."""
    poll_id = pa.poll_id
    poll_meta = active_polls.get(poll_id)
    if not poll_meta:
        return

    chat_id = poll_meta["chat_id"]
    session = active_sessions.get(chat_id)
    if not session:
        return

    user = pa.user
    if not user:
        return

    user_id = user.id
    name = user.first_name or user.username or str(user_id)
    selected_option = pa.option_ids[0] if pa.option_ids else None
    correct_option = poll_meta["correct_id"]

    if user_id not in session["scores"]:
        session["scores"][user_id] = {"name": name, "correct": 0}

    if selected_option == correct_option:
        session["scores"][user_id]["correct"] += 1
        
        # Save to DB Leaderboard
        lb_repo = LeaderboardRepository(get_db())
        try:
            await lb_repo.col.update_one(
                {"qid": session["qid"], "user_id": user_id},
                {
                    "$set": {
                        "user_name": name,
                        "username": name,
                        "completed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                    "$inc": {"score": 1, "total_questions": 1},
                },
                upsert=True,
            )
        except Exception:
            pass


async def stop_cmd(c: Client, m: Message) -> None:
    """/stop -- stop the currently running quiz in this chat."""
    chat_id = m.chat.id
    if chat_id in active_sessions:
        active_sessions[chat_id]["stopped"] = True
        active_sessions[chat_id]["skip_event"].set()
        active_sessions.pop(chat_id, None)
        await m.reply("🛑 **Quiz session stopped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def skip_cmd(c: Client, m: Message) -> None:
    """/skip -- skip the current question in this chat."""
    chat_id = m.chat.id
    if chat_id in active_sessions:
        active_sessions[chat_id]["skip_event"].set()
        await m.reply("⏭️ **Question skipped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def leaderboard_cmd(c: Client, m: Message) -> None:
    """/leaderboard <qid> -- show quiz leaderboard."""
    parts = m.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await m.reply("Usage: `/leaderboard <QUIZ_ID>`")
        return
    qid = parts[1].strip()
    lb_repo = LeaderboardRepository(get_db())
    top_users = await lb_repo.top(qid, limit=10)
    
    if not top_users:
        await m.reply(f"🏆 **Leaderboard for {qid}:**\n\nNo scores recorded yet.")
        return

    text = f"🏆 **Top Leaderboard ({qid}):**\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for idx, row in enumerate(top_users, 1):
        icon = medals[idx - 1] if idx <= 3 else f"#{idx}"
        name = row.get("user_name") or row.get("username") or "User"
        score = row.get("score", 0)
        total = row.get("total_questions", 0)
        text += f"{icon} **{name}** — {score}/{total} pts\n"
    
    await m.reply(text)


def register(app: Client) -> None:
    app.on_message(filters.command("quiz"))(quiz_cmd)
    app.on_message(filters.command("stop"))(stop_cmd)
    app.on_message(filters.command("skip"))(skip_cmd)
    app.on_message(filters.command(["leaderboard", "leaders"]))(leaderboard_cmd)
    app.on_poll_answer()(poll_answer_cb)
