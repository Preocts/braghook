from __future__ import annotations

import http.client
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from braghook.config_ctrl import Config

DEFAULT_FILE_TEMPLATE = """### {date} [Optional: Add a title here]

Write your brag here. Summarize what you did today, what you learned,
 and what you plan to do tomorrow.

- Bullet specific things you did (meetings, tasks, etc.)
  - Nest details such as links to tasks, commits, or PRs
"""

logger = logging.getLogger(__name__)


def open_editor(config: Config, filename: str) -> None:
    """Open the editor."""
    if not Path(filename).exists():
        create_file(filename)
    args = config.editor_args.split()

    args.append(str(filename))
    subprocess.run([config.editor, *args])


def create_file(filename: str) -> None:
    """Create the file."""
    with open(filename, "w") as file:
        file.write(
            DEFAULT_FILE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
        )


def get_filename(config: Config) -> str:
    """Get the filename."""
    return str(Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md"))


def read_file(filename: str) -> str:
    """Read the file."""
    with open(filename) as file:
        return file.read()


def build_discord_webhook_plain(
    content: str,
) -> dict[str, Any]:
    """Build the Discord webhook."""
    return {"username": "braghook", "content": f"```{content}```"}


def build_discord_webhook(
    author: str,
    author_icon: str,
    content: str,
) -> dict[str, Any]:
    """Build the Discord webhook."""
    title = extract_title_from_message(content)
    content = re.sub(r"^[-*]\s?", r":small_blue_diamond: ", content, flags=re.MULTILINE)
    content = re.sub(
        r"^(\s*)[-*]\s?", r":small_orange_diamond: ", content, flags=re.MULTILINE
    )
    content = re.sub(r"^#{1,4}\s(.+)$", r"**\1**", content, flags=re.MULTILINE)

    return {
        "username": "braghook",
        "embeds": [
            {
                "author": {
                    "name": author,
                    "icon_url": author_icon,
                },
                "title": title,
                "description": content,
                "color": 0x9C5D7F,
            },
        ],
    }


def build_msteams_webhook(
    author: str,
    author_icon: str,
    content: str,
) -> dict[str, Any]:
    """Build the MSTeams webhook."""
    title = extract_title_from_message(content)
    content = re.sub(r"^#{1,4}\s(.+)$", r"**\1**", content, flags=re.MULTILINE)
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.2",
                    "type": "AdaptiveCard",
                    "themeColor": "9C5D7F",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": title,
                            "size": "medium",
                            "weight": "bolder",
                            "style": "heading",
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "Image",
                                            "url": author_icon,
                                            "size": "small",
                                            "style": "person",
                                            "fallback": "drop",
                                        }
                                    ],
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": author,
                                            "size": "default",
                                            "weight": "bolder",
                                            "wrap": True,
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": "Daily Brag",
                                            "spacing": "none",
                                            "isSubtle": True,
                                            "wrap": True,
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": content,
                            "size": "default",
                            "weight": "default",
                            "wrap": True,
                            "fallback": "drop",
                            "separator": True,
                            "id": "contentToToggle",
                            "isVisible": False,
                        },
                    ],
                    "actions": [
                        {
                            "type": "Action.ToggleVisibility",
                            "title": "Toggle Content",
                            "targetElements": ["contentToToggle"],
                        },
                    ],
                    "msteams": {
                        "width": "Full",
                        "entities": [],
                    },
                },
            }
        ],
    }


def extract_title_from_message(message: str) -> str:
    """Extract the title from the message."""
    match = re.search(r"^#{1,4}\s(.+)$", message, re.MULTILINE)
    return match.group(1).strip() if match else ""


def post_message(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> None:
    """Post the message to defined webhooks in config."""
    headers = headers or {"content-type": "application/json"}

    # Remove http(s):// from the url
    url = url.replace("http://", "").replace("https://", "")

    # Split the url into host and path
    url_parts = url.split("/", 1)

    conn = http.client.HTTPSConnection(url_parts[0])
    conn.request("POST", f"/{url_parts[1]}", json.dumps(data), headers)
    response = conn.getresponse()
    if response.status not in range(200, 300):
        logger.error("Error sending message: %s", response.read())


def send_message(config: Config, content: str) -> None:
    """Send the message to defined webhooks in config."""
    if config.discord_webhook != "":
        post_message(
            url=config.discord_webhook,
            data=build_discord_webhook(
                author=config.author,
                author_icon=config.author_icon,
                content=content,
            ),
        )

    if config.discord_webhook_plain != "":
        post_message(
            url=config.discord_webhook_plain,
            data=build_discord_webhook_plain(content),
        )

    if config.msteams_webhook != "":
        post_message(
            url=config.msteams_webhook,
            data=build_msteams_webhook(
                author=config.author,
                author_icon=config.author_icon,
                content=content,
            ),
        )
