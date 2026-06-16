"""Konfiguration des GitHub-Activity-Discord-Bots.

Alle Werte kommen aus Umgebungsvariablen (siehe .env.example).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Umgebungsvariable {name} fehlt. Lege sie in deiner .env an "
            f"(siehe .env.example)."
        )
    return value


# --- Discord ---------------------------------------------------------------
DISCORD_TOKEN: str = _require("DISCORD_TOKEN")
# Channel-ID (Rechtsklick auf Channel -> "ID kopieren", Entwicklermodus an).
DISCORD_CHANNEL_ID: int = int(_require("DISCORD_CHANNEL_ID"))

# --- GitHub Webhook --------------------------------------------------------
# Das gleiche Secret, das du beim Anlegen des Webhooks im Repo einträgst.
GITHUB_WEBHOOK_SECRET: str = _require("GITHUB_WEBHOOK_SECRET")

# --- HTTP-Server (empfängt die GitHub-Webhooks) ----------------------------
WEBHOOK_HOST: str = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT: int = int(os.environ.get("WEBHOOK_PORT", "8080"))
# Pfad, unter dem GitHub die POST-Requests schickt.
WEBHOOK_PATH: str = os.environ.get("WEBHOOK_PATH", "/github")

# Repo nur für Anzeigezwecke (Footer / Fallback-Links).
REPO_FULL_NAME: str = os.environ.get("REPO_FULL_NAME", "maxnoelp/prostratsix")
