"""
Notification service — LINE Notify + Telegram Bot
"""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


async def send_line(message: str) -> bool:
    """ส่งข้อความผ่าน LINE Notify"""
    if not settings.LINE_NOTIFY_TOKEN:
        logger.warning("LINE_NOTIFY_TOKEN ไม่ได้ตั้งค่า")
        return False
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://notify-api.line.me/api/notify",
                headers={"Authorization": f"Bearer {settings.LINE_NOTIFY_TOKEN}"},
                data={"message": f"\n{message}"},
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error(f"LINE Notify error: {resp.status_code} {resp.text}")
            return ok
    except Exception as e:
        logger.error(f"LINE Notify exception: {e}")
        return False


async def send_telegram(message: str) -> bool:
    """ส่งข้อความผ่าน Telegram Bot"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN / CHAT_ID ไม่ได้ตั้งค่า")
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={
                    "chat_id":    settings.TELEGRAM_CHAT_ID,
                    "text":       message,
                    "parse_mode": "HTML",
                },
                timeout=10,
            )
            ok = resp.status_code == 200
            if not ok:
                logger.error(f"Telegram error: {resp.status_code} {resp.text}")
            return ok
    except Exception as e:
        logger.error(f"Telegram exception: {e}")
        return False


async def notify(channel: str, message: str) -> bool:
    """ส่งตาม channel — 'line' | 'telegram'"""
    if channel == "line":
        return await send_line(message)
    if channel == "telegram":
        return await send_telegram(message)
    logger.warning(f"Unknown channel: {channel}")
    return False
