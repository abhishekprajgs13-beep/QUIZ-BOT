"""
Advance Quiz Bot — Open Source Project
This project was originally developed by Gagan (github.com/devgaganin).
Reference: https://t.me/advance_quiz_bot
The codebase has been reviewed and verified with the assistance of Claude AI.
"""

from __future__ import annotations

import logging

from pyrogram import Client
from pyrogram.errors import UserNotParticipant
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from quizbot.shared import config

logger = logging.getLogger(__name__)

_JOIN_PROMPT_PHOTO = "https://graph.org/file/d44f024a08ded19452152.jpg"


async def subscribe_gate(app: Client, m: Message) -> bool:
    """Return True (and reply with a block/prompt message) if the command
    should be BLOCKED -- i.e. the user is banned from `LOG_GROUP`, or not a
    member of `REQUIRED_SUB_CHANNEL`. Returns False if the command may
    proceed. Callers should `return` immediately when this returns True:

        if await subscribe_gate(app, m):
            return
    """
    if not m.from_user:
        return False

    # 1. Check if user is banned in LOG_GROUP
    if config.LOG_GROUP:
        try:
            member = await app.get_chat_member(config.LOG_GROUP, m.from_user.id)
            if str(member.status) in ("ChatMemberStatus.BANNED", "banned"):
                await m.reply_text("\U0001F6AB Banned")
                return True
        except Exception:
            pass

    # 2. Check required sub channel membership
    if config.REQUIRED_SUB_CHANNEL:
        channel_username = config.REQUIRED_SUB_CHANNEL.strip()
        clean_username = channel_username.lstrip("@")
        try:
            member = await app.get_chat_member(channel_username if channel_username.startswith("@") else f"@{channel_username}", m.from_user.id)
            if str(member.status) in ("ChatMemberStatus.BANNED", "banned"):
                await m.reply_text("\U0001F6AB Banned")
                return True
        except UserNotParticipant:
            await m.reply_photo(
                _JOIN_PROMPT_PHOTO,
                caption="\U0001F4E2 Please join our channel to continue.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("\U0001F517 Join Channel", url=f"https://t.me/{clean_username}")]]
                ),
            )
            return True
        except Exception as exc:
            logger.debug("subscribe_gate channel check failed (allowing through): %s", exc)

    return False
