"""
Advance Quiz Bot — Pyrogram Quiz Runner Engine
Handles /quiz <qid>, group & DM Telegram Quiz Polls, poll answer recording, /stop, /skip, and /leaderboard.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Dict, Any

from pyrogram import Client, filters
from pyrogram.enums import PollType
from pyrogram.types import Message

from quizbot.database import QuizRepository, LeaderboardRepository, get_db

logger = logging.getLogger(__name__)

# Active chat sessions: chat_id -> session dict
active_quiz_sessions: Dict[int, Dict[str, Any]] = {}

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

    await QuizRepository(get_db()).increment_participants(qid)
    asyncio.create_task(_run_quiz_loop(c, chat_id, session))


async def _run_quiz_loop(c: Client, chat_id: int, session: dict) -> None:
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
            poll_msg = await c.send_poll(
                chat_id=chat_id,
                question=f"[{i}/{total_q}] {txt}"[:290],
                options=options,
                is_anonymous=False,
                type=PollType.QUIZ,
                correct_option_id=correct_id if correct_id < len(options) else 0,
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

        try:
            await asyncio.wait_for(session["skip_event"].wait(), timeout=timer)
        except asyncio.TimeoutError:
            pass

        if session.get("stopped"):
            break

    # Session finished
    active_quiz_sessions.pop(chat_id, None)

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


async def poll_answer_cb(c: Client, pa: Any) -> None:
    poll_id = pa.poll_id
    poll_meta = active_polls.get(poll_id)
    if not poll_meta:
        return

    chat_id = poll_meta["chat_id"]
    session = active_quiz_sessions.get(chat_id)
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
    chat_id = m.chat.id
    if chat_id in active_quiz_sessions:
        active_quiz_sessions[chat_id]["stopped"] = True
        active_quiz_sessions[chat_id]["skip_event"].set()
        active_quiz_sessions.pop(chat_id, None)
        await m.reply("🛑 **Quiz session stopped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def skip_cmd(c: Client, m: Message) -> None:
    chat_id = m.chat.id
    if chat_id in active_quiz_sessions:
        active_quiz_sessions[chat_id]["skip_event"].set()
        await m.reply("⏭️ **Question skipped.**")
    else:
        await m.reply("⚠️ **No active quiz running in this chat.**")


async def leaderboard_cmd(c: Client, m: Message) -> None:
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


from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.types import UpdateBotPollVote


async def raw_poll_vote_cb(client: Client, update: Any, users: dict, chats: dict) -> None:
    if isinstance(update, UpdateBotPollVote):
        poll_id = str(update.poll_id)
        poll_meta = active_polls.get(poll_id)
        if not poll_meta:
            return
        chat_id = poll_meta["chat_id"]
        session = active_quiz_sessions.get(chat_id)
        if not session:
            return
        user_id = update.user_id
        user_obj = users.get(user_id)
        name = user_obj.first_name if user_obj and hasattr(user_obj, "first_name") and user_obj.first_name else str(user_id)
        selected_option = update.options[0] if update.options else None
        correct_option = poll_meta["correct_id"]

        if user_id not in session["scores"]:
            session["scores"][user_id] = {"name": name, "correct": 0}

        if selected_option == correct_option:
            session["scores"][user_id]["correct"] += 1
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


def register(app: Client) -> None:
    app.on_message(filters.command(["quiz", "quiz@bot"]))(quiz_cmd)
    app.on_message(filters.command("stop"))(stop_cmd)
    app.on_message(filters.command("skip"))(skip_cmd)
    app.on_message(filters.command(["leaderboard", "leaders"]))(leaderboard_cmd)
    app.add_handler(RawUpdateHandler(raw_poll_vote_cb))
