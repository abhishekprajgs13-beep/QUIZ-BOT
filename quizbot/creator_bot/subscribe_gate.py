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
    channel = config.REQUIRED_SUB_CHANNEL
    if channel:
        try:
            clean_ch = channel.lstrip("@")
            member = await app.get_chat_member(channel, m.from_user.id)
            if str(member.status) in ("ChatMemberStatus.BANNED", "banned", "kicked"):
                await m.reply_text("🚫 Banned from channel.")
                return True
        except UserNotParticipant:
            clean_ch = channel.lstrip("@")
            await m.reply_photo(
                _JOIN_PROMPT_PHOTO,
                caption="📢 Please join our channel to continue using the bot.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔗 Join Channel", url=f"https://t.me/{clean_ch}")]]
                ),
            )
            return True
        except Exception as exc:
            logger.debug("subscribe_gate check failed (allowing through): %s", exc)
    return False
