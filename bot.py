"""Einstiegspunkt: discord.py-Bot + GitHub-Webhook-Server in einem Prozess.

Start:  python bot.py
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from webhook_server import start_webhook_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("github-bot")


class ActivityBot(commands.Bot):
    def __init__(self) -> None:
        # Für ein reines Activity-Log reichen die Default-Intents (kein
        # privilegierter Message-Content nötig).
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self._webhook_runner = None

    async def setup_hook(self) -> None:
        # Webhook-Server starten, sobald der Event-Loop läuft.
        self._webhook_runner = await start_webhook_server(self)

    async def on_ready(self) -> None:
        log.info("Eingeloggt als %s (id=%s)", self.user, self.user.id)
        channel = self.get_channel(config.DISCORD_CHANNEL_ID)
        if channel is None:
            log.warning(
                "Channel %s nicht gefunden. Ist der Bot eingeladen und hat "
                "Senderechte?",
                config.DISCORD_CHANNEL_ID,
            )
        else:
            log.info("Poste Aktivitäts-Log in #%s", channel.name)

    async def close(self) -> None:
        if self._webhook_runner is not None:
            await self._webhook_runner.cleanup()
        await super().close()


def main() -> None:
    bot = ActivityBot()
    bot.run(config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
