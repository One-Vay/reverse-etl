"""Thin client for sending Telegram bot messages — used for scheduled-run
completion reports (see `app.core.scheduler`) and the Settings page's
"Send test message" button. Deliberately not a general notifications
abstraction — this app has exactly one notification channel, and
Telegram's Bot API is simple enough not to need an SDK on top of the
`httpx` this project already depends on.
"""

from __future__ import annotations

import httpx

_API_BASE = "https://api.telegram.org"

_CHAT_NOT_FOUND_HINT = (
    "Telegram doesn't recognize this chat ID yet. Open a chat with your bot "
    "and send it any message (e.g. /start) first — Telegram only lets a bot "
    "message chats it has already seen — then try the test again."
)
_BOT_TO_BOT_HINT = (
    "This chat ID belongs to a bot — Telegram never lets a bot message "
    "itself or another bot. Use your own personal chat ID instead (e.g. "
    "message @userinfobot and it will reply with it), not the bot's ID "
    "from BotFather."
)

# Telegram error strings that mean "the chat ID is wrong" rather than
# "something's broken", each with a different, specific fix — worth
# surfacing directly instead of the bare API string. Matched as
# case-insensitive substrings against the API's `description` field.
# Telegram's wording for the bot-to-bot case varies ("...to the bot" vs.
# "...to bots"), so both variants are listed.
_KNOWN_ERROR_HINTS = {
    "chat not found": _CHAT_NOT_FOUND_HINT,
    "can't send messages to the bot": _BOT_TO_BOT_HINT,
    "can't send messages to bots": _BOT_TO_BOT_HINT,
}


class TelegramError(Exception):
    """Raised when a message couldn't be sent. Callers are expected to
    catch-and-log rather than let this fail whatever triggered the
    notification — a broken Telegram integration must never break a
    sync run."""


async def send_message(
    bot_token: str, chat_id: str, text: str, *, timeout: float = 10.0
) -> None:
    """Send `text` to `chat_id` via the given bot.

    Raises:
        TelegramError: If the token/chat ID are wrong, the bot can't
            reach the chat, or the request otherwise fails.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{_API_BASE}/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
    except httpx.HTTPError as exc:
        raise TelegramError(f"Could not reach Telegram: {exc}") from exc

    if response.is_error:
        try:
            detail = response.json().get("description", response.text)
        except ValueError:
            detail = response.text
        detail_lower = detail.lower()
        for needle, hint in _KNOWN_ERROR_HINTS.items():
            if needle in detail_lower:
                raise TelegramError(hint)
        raise TelegramError(
            f"Telegram rejected the message (HTTP {response.status_code}): {detail}"
        )
