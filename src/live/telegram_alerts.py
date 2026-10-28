"""Telegram alerts for live market predictions."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


class TelegramAlertSender:
    """Send prediction alerts using Telegram Bot HTTP API."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        timeout_seconds: int = 10,
    ) -> None:
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.timeout_seconds = timeout_seconds

    @property
    def configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    @staticmethod
    def format_prediction(prediction: dict[str, Any]) -> str:
        symbol = prediction.get("symbol", "UNKNOWN")
        lines = [
            "📊 LIVE MARKET PREDICTION",
            f"Symbol: {symbol}",
            f"Generated: {prediction.get('generated_at', 'N/A')}",
            "",
        ]

        for item in prediction.get("predictions", []):
            horizon = item.get("horizon_minutes", "?")
            status = item.get("status", "UNKNOWN")
            direction = item.get("direction") or status
            confidence = item.get("confidence")

            if confidence is None:
                lines.append(f"{horizon}m: {direction}")
            else:
                lines.append(
                    f"{horizon}m: {direction} | "
                    f"Confidence: {confidence * 100:.1f}%"
                )

        lines.extend([
            "",
            "⚠️ AI estimate only; not a guaranteed outcome.",
            "Orders are not placed automatically.",
        ])
        return "\n".join(lines)

    def send_message(self, message: str) -> dict[str, Any]:
        """Send a message; return an explicit status instead of hiding errors."""
        if not self.configured:
            return {
                "ok": False,
                "status": "NOT_CONFIGURED",
                "message": "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.",
            }

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": message,
            "disable_web_page_preview": True,
        }).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
                return {
                    "ok": bool(result.get("ok")),
                    "status": "SENT" if result.get("ok") else "API_ERROR",
                    "description": result.get("description"),
                }
        except urllib.error.HTTPError as exc:
            return {
                "ok": False,
                "status": "HTTP_ERROR",
                "code": exc.code,
            }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return {
                "ok": False,
                "status": "NETWORK_ERROR",
                "message": str(exc),
            }
        except (ValueError, json.JSONDecodeError) as exc:
            return {
                "ok": False,
                "status": "INVALID_RESPONSE",
                "message": str(exc),
            }

    def send_prediction(self, prediction: dict[str, Any]) -> dict[str, Any]:
        return self.send_message(self.format_prediction(prediction))
