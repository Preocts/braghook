"""
Webhook builder.

This module contains the functions to build the webhook message.

Update the BUILDERS dictionary to add new webhook builders.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from typing import Protocol

    class Builder(Protocol):
        """Protocol for the message builder."""

        def __call__(
            self,
            author: str,
            author_icon: str,
            content: str,
        ) -> dict[str, Any]:
            ...


def extract_title_from_message(message: str) -> str:
    """Extract the title from the message."""
    match = re.search(r"^#{1,4}\s(.+)$", message, re.MULTILINE)
    return match.group(1).strip() if match else ""


def bullet_marks_to_diamonds(message: str) -> str:
    """Convert bullet marks to diamonds."""
    message = re.sub(r"^[-*]\s?", r":small_blue_diamond: ", message, flags=re.MULTILINE)
    message = re.sub(
        r"^(\s*)[-*]\s?", r":small_orange_diamond: ", message, flags=re.MULTILINE
    )
    return message


def headers_to_bold(message: str) -> str:
    """Convert headers to bold."""
    message = re.sub(r"^#{1,4}\s(.+)$", r"**\1**", message, flags=re.MULTILINE)
    return message


def build_discord_webhook_plain(
    author: str,
    author_icon: str,
    content: str,
) -> dict[str, Any]:
    """Build the Discord webhook."""
    content = f"{author} ({author_icon})\n{content}"
    return {"username": "braghook", "content": f"```{content}```"}


def build_discord_webhook(
    author: str,
    author_icon: str,
    content: str,
) -> dict[str, Any]:
    """Build the Discord webhook."""
    title = extract_title_from_message(content)
    content = bullet_marks_to_diamonds(content)
    content = headers_to_bold(content)

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
    content = headers_to_bold(content)
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


# Define the builders here, used in the main script
# NOTE: The key is the config field that defines the url
# NOTE: The value is the function that builds the message
BUILDERS: dict[str, Builder] = {
    "discord_webhook": build_discord_webhook,
    "discord_webhook_plain": build_discord_webhook_plain,
    "msteams_webhook": build_msteams_webhook,
}