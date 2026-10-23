import httpx


class TelegramClient:
    """Minimal Telegram Bot API client (long polling, no public webhook needed)."""

    def __init__(self, token: str):
        self._base = f"https://api.telegram.org/bot{token}"
        self._http = httpx.AsyncClient(timeout=40)

    async def get_updates(self, offset: int, timeout: int = 25) -> list:
        r = await self._http.get(
            f"{self._base}/getUpdates",
            params={"offset": offset, "timeout": timeout, "allowed_updates": '["message"]'},
        )
        r.raise_for_status()
        return r.json()["result"]

    async def send_message(self, chat_id: int, text: str) -> None:
        r = await self._http.post(
            f"{self._base}/sendMessage", json={"chat_id": chat_id, "text": text}
        )
        r.raise_for_status()

    async def aclose(self) -> None:
        await self._http.aclose()
