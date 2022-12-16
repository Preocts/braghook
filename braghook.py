from __future__ import annotations

import argparse
import dataclasses
import re
import subprocess
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from runtime_yolk import Yolk

DEFAULT_CONFIG_FILE = "braghook"
DEFAULT_ENV_FILE = ".env"
DEFAULT_FILE = """### {date} [Optional: Add a title here]

Write your brag here. Summarize what you did today, what you learned,
 and what you plan to do tomorrow.

- Bullet specific things you did (meetings, tasks, etc.)
  - Nest details such as links to tasks, commits, or PRs
"""


@dataclasses.dataclass(frozen=True)
class Config:
    """Dataclass for the configuration."""

    workdir: str = "."
    editor: str = "vim"
    editor_args: list[str] = dataclasses.field(default_factory=list)
    author: str = "braghook"
    author_icon: str = ""
    discord_webhook: str = ""
    discord_webhook_plain: str = ""


def load_config(config_file: str, env_file: str) -> Config:
    """Load the configuration."""
    yolk = Yolk()
    yolk.load_env(env_file)
    yolk.load_config(config_file)
    config = yolk.config["DEFAULT"]

    return Config(
        workdir=config.get("workdir", fallback="."),
        editor=config.get("editor", fallback="vim"),
        editor_args=config.get("editor_args", fallback="").split(),
        author=config.get("author", fallback="braghook"),
        author_icon=config.get("author_icon", fallback=""),
        discord_webhook=config.get("discord_webhook", fallback=""),
        discord_webhook_plain=config.get("discord_webhook_plain", fallback=""),
    )


def open_editor(config: Config, filename: str) -> None:
    """Open the editor."""
    if not Path(filename).exists():
        create_file(filename)

    config.editor_args.append(str(filename))
    subprocess.run([config.editor, *config.editor_args])


def create_file(filename: str) -> None:
    """Create the file."""
    with open(filename, "w") as file:
        file.write(DEFAULT_FILE.format(date=datetime.now().strftime("%Y-%m-%d")))


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
                                        }
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
    url: str, data: dict[str, Any], headers: dict[str, str] | None = None
) -> None:
    """Post the message to defined webhooks in config."""
    httpx.post(url, json=data, headers=headers)


def send_message(config: Config, content: str, filename: str) -> None:
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


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse the arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bragfile",
        "-b",
        type=str,
        help="The brag file to use",
        default=None,
    )
    parser.add_argument(
        "--create-config",
        "-C",
        action="store_true",
        help="Create the config file",
    )
    parser.add_argument(
        "--auto-send",
        "-a",
        action="store_true",
        help="Automatically send the brag",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=DEFAULT_CONFIG_FILE,
        help="The config file to use",
    )
    parser.add_argument(
        "--env",
        "-e",
        type=str,
        default=DEFAULT_ENV_FILE,
        help="The env file to use",
    )

    return parser.parse_args(args)


def get_input(prompt: str) -> str:
    """Get input from the user."""
    return input(prompt)


def create_config(config_file: str) -> None:
    """Create the config file."""
    # Avoid overwriting existing config
    if Path(config_file).exists():
        print(f"Config file already exists: {config_file}")
        return

    config = ConfigParser()
    config.read_dict({"DEFAULT": dataclasses.asdict(Config())})
    with open(config_file, "w") as file:
        config.write(file)


def main(_args: list[str] | None = None) -> int:
    """Run the program."""
    args = parse_args(_args)

    if args.create_config:
        create_config(f"{DEFAULT_CONFIG_FILE}.ini")
        return 0

    config = load_config(args.config, args.env)
    filename = args.bragfile or get_filename(config)

    open_editor(config, filename)

    if not args.auto_send and get_input("Send brag? [y/N] ").lower() != "y":
        return 0

    content = read_file(filename)
    send_message(config, content, filename)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
