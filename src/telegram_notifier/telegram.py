import logging

from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder

logger = logging.getLogger(__name__)


async def send_message(token: str, chat_id: str, text: str) -> int:
    """Send a new Telegram message. Returns the message_id."""
    application = ApplicationBuilder().token(token).build()
    async with application:
        message = await application.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return message.message_id


async def edit_message(token: str, chat_id: str, message_id: int, text: str) -> None:
    """Edit an existing Telegram message.

    Silently ignores "message is not modified" errors.
    """
    application = ApplicationBuilder().token(token).build()
    async with application:
        try:
            await application.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.info("Message content unchanged, skipping edit")
            else:
                raise
