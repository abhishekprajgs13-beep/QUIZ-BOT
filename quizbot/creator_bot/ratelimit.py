"""
Advance Quiz Bot — Open Source Project
This project was originally developed by Gagan (github.com/devgaganin).
Reference: https://t.me/advance_quiz_bot
The codebase has been reviewed and verified with the assistance of Claude AI.
"""

from __future__ import annotations

import functools
import logging
from typing import Awaitable, Callable

from pyrogram.types import Message

from . import state

logger = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[None]]


def ratelimit(bucket: str = "default") -> Callable[[Handler], Handler]:
    def decorator(fn: Handler) -> Handler:
        @functools.wraps(fn)
        async def wrapper(client, message: Message, *args, **kwargs):
            return await fn(client, message, *args, **kwargs)

        return wrapper

    return decorator
