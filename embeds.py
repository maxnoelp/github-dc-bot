"""Baut Discord-Embeds aus GitHub-Webhook-Payloads.

Jede ``handle_*``-Funktion bekommt den geparsten JSON-Payload und gibt ein
``discord.Embed`` zurück – oder ``None``, wenn das konkrete Event nicht
geloggt werden soll.

Die öffentliche Funktion ``build_embed(event, payload)`` wählt anhand des
GitHub-Event-Namens (Header ``X-GitHub-Event``) den passenden Handler.
"""

from __future__ import annotations

from typing import Callable, Optional

import discord

# --- Farben ----------------------------------------------------------------
COLOR_GREEN = 0x2ECC71   # geöffnet / erfolgreich / gemerged
COLOR_RED = 0xE74C3C     # geschlossen / fehlgeschlagen
COLOR_BLUE = 0x3498DB    # Pull Requests
COLOR_PURPLE = 0x9B59B6  # Push / Branches
COLOR_GRAY = 0x95A5A6    # Kommentare / neutral
COLOR_YELLOW = 0xF1C40F  # Reviews / Wartet
COLOR_ORANGE = 0xE67E22  # zugewiesen / claim


def _author(payload: dict) -> dict:
    """Discord-Embed-Author-Block aus dem GitHub-Sender."""
    sender = payload.get("sender") or {}
    return {
        "name": sender.get("login", "unbekannt"),
        "url": sender.get("html_url", ""),
        "icon_url": sender.get("avatar_url", ""),
    }


def _repo_name(payload: dict) -> str:
    repo = payload.get("repository") or {}
    return repo.get("full_name", "")


def _truncate(text: Optional[str], limit: int = 500) -> str:
    if not text:
        return ""
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _base_embed(payload: dict, *, color: int) -> discord.Embed:
    embed = discord.Embed(color=color)
    author = _author(payload)
    embed.set_author(
        name=author["name"],
        url=author["url"] or None,
        icon_url=author["icon_url"] or None,
    )
    embed.set_footer(text=_repo_name(payload))
    return embed


# --- Issues / Tickets ------------------------------------------------------
def handle_issues(payload: dict) -> Optional[discord.Embed]:
    action = payload.get("action")
    issue = payload.get("issue", {})
    number = issue.get("number")
    title = issue.get("title", "")
    url = issue.get("html_url", "")

    actions = {
        "opened": ("🎫 Ticket eröffnet", COLOR_GREEN),
        "closed": ("✅ Ticket geschlossen", COLOR_RED),
        "reopened": ("🔄 Ticket wieder geöffnet", COLOR_GREEN),
        "assigned": ("🙋 Ticket übernommen (assigned)", COLOR_ORANGE),
        "unassigned": ("↩️ Zuweisung entfernt", COLOR_GRAY),
    }
    if action not in actions:
        return None

    label, color = actions[action]
    embed = _base_embed(payload, color=color)
    embed.title = f"{label}: #{number} {title}"
    embed.url = url

    if action == "opened":
        embed.description = _truncate(issue.get("body"))
    if action in ("assigned", "unassigned"):
        assignee = (payload.get("assignee") or {}).get("login", "?")
        embed.add_field(name="Bearbeiter", value=assignee, inline=True)

    labels = [lbl.get("name") for lbl in issue.get("labels", [])]
    if labels:
        embed.add_field(name="Labels", value=", ".join(labels), inline=True)
    return embed


def handle_issue_comment(payload: dict) -> Optional[discord.Embed]:
    if payload.get("action") != "created":
        return None
    issue = payload.get("issue", {})
    comment = payload.get("comment", {})
    number = issue.get("number")
    embed = _base_embed(payload, color=COLOR_GRAY)
    embed.title = f"💬 Kommentar zu #{number} {issue.get('title', '')}"
    embed.url = comment.get("html_url", "")
    embed.description = _truncate(comment.get("body"))
    return embed


# --- Pull Requests ---------------------------------------------------------
def handle_pull_request(payload: dict) -> Optional[discord.Embed]:
    action = payload.get("action")
    pr = payload.get("pull_request", {})
    number = pr.get("number")
    title = pr.get("title", "")
    url = pr.get("html_url", "")

    if action == "closed":
        if pr.get("merged"):
            label, color = "🟣 Pull Request gemerged", COLOR_PURPLE
        else:
            label, color = "❌ Pull Request geschlossen (nicht gemerged)", COLOR_RED
    else:
        mapping = {
            "opened": ("🔀 Pull Request geöffnet", COLOR_BLUE),
            "reopened": ("🔄 Pull Request wieder geöffnet", COLOR_BLUE),
            "ready_for_review": ("👀 Pull Request bereit für Review", COLOR_YELLOW),
            "review_requested": ("📋 Review angefragt", COLOR_YELLOW),
        }
        if action not in mapping:
            return None
        label, color = mapping[action]

    embed = _base_embed(payload, color=color)
    embed.title = f"{label}: #{number} {title}"
    embed.url = url
    if action == "opened":
        embed.description = _truncate(pr.get("body"))

    head = (pr.get("head") or {}).get("ref", "?")
    base = (pr.get("base") or {}).get("ref", "?")
    embed.add_field(name="Branch", value=f"`{head}` → `{base}`", inline=True)
    return embed


def handle_pull_request_review(payload: dict) -> Optional[discord.Embed]:
    if payload.get("action") != "submitted":
        return None
    review = payload.get("review", {})
    pr = payload.get("pull_request", {})
    state = (review.get("state") or "").lower()

    mapping = {
        "approved": ("✅ Review: genehmigt", COLOR_GREEN),
        "changes_requested": ("🔧 Review: Änderungen angefragt", COLOR_RED),
        "commented": ("💬 Review-Kommentar", COLOR_GRAY),
    }
    if state not in mapping:
        return None
    label, color = mapping[state]

    embed = _base_embed(payload, color=color)
    embed.title = f"{label}: #{pr.get('number')} {pr.get('title', '')}"
    embed.url = review.get("html_url", "")
    embed.description = _truncate(review.get("body"))
    return embed


# --- Push / Branches -------------------------------------------------------
def handle_push(payload: dict) -> Optional[discord.Embed]:
    ref = payload.get("ref", "")
    if not ref.startswith("refs/heads/"):
        return None  # Tags etc. ignorieren
    branch = ref.removeprefix("refs/heads/")

    # Branch-Anlage/Löschung wird über create/delete-Events abgebildet.
    if payload.get("deleted"):
        return None
    commits = payload.get("commits", [])
    if not commits:
        return None

    embed = _base_embed(payload, color=COLOR_PURPLE)
    count = len(commits)
    embed.title = f"⬆️ {count} Commit{'s' if count != 1 else ''} auf `{branch}`"
    embed.url = payload.get("compare", "")

    lines = []
    for c in commits[:10]:
        sha = c.get("id", "")[:7]
        msg = (c.get("message") or "").splitlines()[0]
        lines.append(f"[`{sha}`]({c.get('url', '')}) {_truncate(msg, 80)}")
    if count > 10:
        lines.append(f"… und {count - 10} weitere")
    embed.description = "\n".join(lines)
    return embed


def handle_create(payload: dict) -> Optional[discord.Embed]:
    ref_type = payload.get("ref_type")
    if ref_type not in ("branch", "tag"):
        return None
    ref = payload.get("ref", "")
    label = "🌱 Branch erstellt" if ref_type == "branch" else "🏷️ Tag erstellt"
    embed = _base_embed(payload, color=COLOR_PURPLE)
    embed.title = f"{label}: `{ref}`"
    repo = payload.get("repository") or {}
    base = repo.get("html_url", "")
    if ref_type == "branch" and base:
        embed.url = f"{base}/tree/{ref}"
    return embed


def handle_delete(payload: dict) -> Optional[discord.Embed]:
    ref_type = payload.get("ref_type")
    if ref_type not in ("branch", "tag"):
        return None
    ref = payload.get("ref", "")
    label = "🗑️ Branch gelöscht" if ref_type == "branch" else "🗑️ Tag gelöscht"
    embed = _base_embed(payload, color=COLOR_GRAY)
    embed.title = f"{label}: `{ref}`"
    return embed


# --- CI / GitHub Actions ---------------------------------------------------
def handle_workflow_run(payload: dict) -> Optional[discord.Embed]:
    if payload.get("action") != "completed":
        return None
    run = payload.get("workflow_run", {})
    conclusion = (run.get("conclusion") or "").lower()
    name = run.get("name", "Workflow")
    branch = run.get("head_branch", "?")

    mapping = {
        "success": ("✅ CI erfolgreich", COLOR_GREEN),
        "failure": ("🚨 CI fehlgeschlagen", COLOR_RED),
        "cancelled": ("⏹️ CI abgebrochen", COLOR_GRAY),
        "timed_out": ("⏱️ CI Timeout", COLOR_RED),
    }
    if conclusion not in mapping:
        return None
    label, color = mapping[conclusion]

    embed = _base_embed(payload, color=color)
    embed.title = f"{label}: {name}"
    embed.url = run.get("html_url", "")
    embed.add_field(name="Branch", value=f"`{branch}`", inline=True)
    embed.add_field(name="Status", value=conclusion, inline=True)
    head_commit = run.get("head_commit") or {}
    if head_commit.get("message"):
        embed.add_field(
            name="Commit",
            value=_truncate(head_commit["message"].splitlines()[0], 100),
            inline=False,
        )
    return embed


def handle_ping(payload: dict) -> Optional[discord.Embed]:
    embed = _base_embed(payload, color=COLOR_GREEN)
    embed.title = "🏓 Webhook verbunden"
    embed.description = "Der GitHub-Webhook wurde erfolgreich eingerichtet."
    return embed


_HANDLERS: dict[str, Callable[[dict], Optional[discord.Embed]]] = {
    "issues": handle_issues,
    "issue_comment": handle_issue_comment,
    "pull_request": handle_pull_request,
    "pull_request_review": handle_pull_request_review,
    "push": handle_push,
    "create": handle_create,
    "delete": handle_delete,
    "workflow_run": handle_workflow_run,
    "ping": handle_ping,
}


def build_embed(event: str, payload: dict) -> Optional[discord.Embed]:
    """Wähle den passenden Handler für ein GitHub-Event und baue das Embed."""
    handler = _HANDLERS.get(event)
    if handler is None:
        return None
    return handler(payload)
