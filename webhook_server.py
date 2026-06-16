"""aiohttp-Server, der GitHub-Webhooks empfängt und an Discord weiterreicht.

Läuft im selben asyncio-Loop wie der discord.py-Bot. Der Bot wird per
``app["bot"]`` übergeben, damit der Handler ins Ziel-Channel posten kann.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from aiohttp import web

import config
from embeds import build_embed

log = logging.getLogger("github-bot.webhook")


def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    """Prüfe die GitHub-HMAC-Signatur (X-Hub-Signature-256)."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = (
        "sha256="
        + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, signature_header)


async def _handle_github(request: web.Request) -> web.Response:
    body = await request.read()
    signature = request.headers.get("X-Hub-Signature-256")
    if not _verify_signature(config.GITHUB_WEBHOOK_SECRET, body, signature):
        log.warning("Webhook mit ungültiger Signatur abgelehnt")
        return web.Response(status=401, text="invalid signature")

    event = request.headers.get("X-GitHub-Event", "")
    try:
        payload = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid json")

    embed = build_embed(event, payload)
    if embed is None:
        # Event wird bewusst nicht geloggt -> trotzdem 200, sonst retried GitHub.
        return web.Response(status=200, text="ignored")

    bot = request.app["bot"]
    try:
        channel = bot.get_channel(config.DISCORD_CHANNEL_ID) or await bot.fetch_channel(
            config.DISCORD_CHANNEL_ID
        )
        await channel.send(embed=embed)
    except Exception:
        log.exception("Konnte Embed nicht nach Discord senden")
        return web.Response(status=500, text="discord error")

    return web.Response(status=200, text="ok")


async def _health(_: web.Request) -> web.Response:
    return web.Response(text="ok")


def build_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_post(config.WEBHOOK_PATH, _handle_github)
    app.router.add_get("/health", _health)
    return app


async def start_webhook_server(bot) -> web.AppRunner:
    """Starte den HTTP-Server und gib den Runner zurück (zum sauberen Stoppen)."""
    app = build_app(bot)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEBHOOK_HOST, config.WEBHOOK_PORT)
    await site.start()
    log.info(
        "Webhook-Server läuft auf http://%s:%s%s",
        config.WEBHOOK_HOST,
        config.WEBHOOK_PORT,
        config.WEBHOOK_PATH,
    )
    return runner
