# prostratsix GitHub → Discord Activity Bot

Ein Discord-Bot, der das Repo
[`maxnoelp/prostratsix`](https://github.com/maxnoelp/prostratsix) überwacht und
in Echtzeit ein Aktivitäts-Log in einen Discord-Channel postet:

- 🎫 **Tickets/Issues** – eröffnet, geschlossen, wieder geöffnet, übernommen (assigned), Labels
- 💬 **Kommentare** zu Issues
- 🔀 **Pull Requests** – geöffnet, gemerged, geschlossen, ready-for-review, Reviews (approve / changes requested)
- ⬆️ **Pushes & Branches** – Commits, Branch/Tag erstellt/gelöscht
- 🚨 **CI / GitHub Actions** – Workflow-Runs, besonders fehlgeschlagene Jobs

Technik: ein einzelner Prozess mit `discord.py` (Gateway-Bot) **und** einem
`aiohttp`-Server, der die GitHub-Webhooks empfängt, die Signatur prüft und als
Embed in den Channel postet.

```
GitHub  ──(Webhook, HMAC-signiert)──►  aiohttp-Server  ──►  discord.py-Bot  ──►  #channel
```

---

## 1. Discord-Bot anlegen

1. <https://discord.com/developers/applications> → **New Application**.
2. Links **Bot** → **Reset Token** → Token kopieren → in `.env` als `DISCORD_TOKEN`.
3. **Installation / OAuth2** → Scope `bot`, Permission `Send Messages` (+ `Embed Links`).
   Die generierte URL aufrufen und den Bot in deinen Server einladen.
4. In Discord: **Einstellungen → Erweitert → Entwicklermodus** aktivieren,
   dann Rechtsklick auf den Ziel-Channel → **ID kopieren** → in `.env` als
   `DISCORD_CHANNEL_ID`.

> Privilegierte Intents sind **nicht** nötig – der Bot liest keine Nachrichten.

## 2. Konfigurieren

```bash
cp .env.example .env
# .env ausfüllen: DISCORD_TOKEN, DISCORD_CHANNEL_ID, GITHUB_WEBHOOK_SECRET
```

`GITHUB_WEBHOOK_SECRET` ist ein frei wählbares, geheimes Passwort – z. B.:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## 3. Lokal starten

```bash
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python bot.py
```

Der Webhook-Server lauscht dann auf `http://0.0.0.0:8080/github`.

## 4. Öffentlich erreichbar machen

GitHub muss den Webhook-Endpunkt per HTTPS erreichen können.

**Zum Testen (lokal)** – mit einem Tunnel:

```bash
# z. B. Cloudflare Tunnel
cloudflared tunnel --url http://localhost:8080
# oder ngrok
ngrok http 8080
```

Du bekommst eine URL wie `https://xyz.trycloudflare.com` – der Webhook-Pfad ist
dann `https://xyz.trycloudflare.com/github`.

**Produktiv** – auf einem Server/Cloud hinter HTTPS (Reverse-Proxy wie
nginx/Caddy oder Plattform mit TLS). Der Endpunkt ist `<deine-domain>/github`.

## 5. GitHub-Webhook einrichten

Im Repo: **Settings → Webhooks → Add webhook**

| Feld | Wert |
|------|------|
| Payload URL | `https://<deine-url>/github` |
| Content type | `application/json` |
| Secret | exakt dein `GITHUB_WEBHOOK_SECRET` |
| Events | **Let me select individual events** → Issues, Issue comments, Pull requests, Pull request reviews, Pushes, Branch or tag creation, Branch or tag deletion, Workflow runs |

Nach dem Speichern schickt GitHub ein `ping` – der Bot postet dann
„🏓 Webhook verbunden". ✅

## 6. Mit Docker

```bash
docker build -t prostratsix-dc-bot .
docker run --env-file .env -p 8080:8080 prostratsix-dc-bot
```

---

## Events erweitern / anpassen

Die gesamte Formatierung steckt in `embeds.py`. Jedes GitHub-Event hat eine
`handle_*`-Funktion, die ein `discord.Embed` (oder `None` zum Ignorieren)
zurückgibt. Neue Events: Handler schreiben und in `_HANDLERS` eintragen.

## Mögliche Erweiterung: `/claim` direkt aus Discord

Aktuell wird „Ticket übernommen" geloggt, wenn jemand sich **auf GitHub** einem
Issue zuweist. Ein Slash-Command, der umgekehrt aus Discord heraus ein Ticket
übernimmt, braucht zusätzlich:

- einen **GitHub-Token** mit `issues:write` (als `GITHUB_TOKEN` in `.env`),
- ein **Mapping Discord-User → GitHub-User**,
- einen `@bot.tree.command`-Slash-Command, der die GitHub-API
  (`PATCH /repos/{owner}/{repo}/issues/{n}/assignees`) aufruft.

Sag Bescheid, wenn ich das ergänzen soll.
