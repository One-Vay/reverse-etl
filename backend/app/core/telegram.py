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

# Telegram returns this exact description when the bot has never
# exchanged a message with the given chat ID — Telegram has no chat
# record to send into yet, distinct from a wrong ID or a revoked token.
# The fix is on the user's side (message the bot first), so surface that
# instead of a bare API error string.
_CHAT_NOT_FOUND_HINT = (
    "Telegram doesn't recognize this chat ID yet. Open a chat with your bot "
    "and send it any message (e.g. /start) first — Telegram only lets a bot "
    "message chats it has already seen — then try the test again."
)


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
        if "chat not found" in detail.lower():
            raise TelegramError(_CHAT_NOT_FOUND_HINT)
        raise TelegramError(
            f"Telegram rejected the message (HTTP {response.status_code}): {detail}"
        )
