from __future__ import annotations

import argparse
import subprocess
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from runtime_yolk import Yolk

DEFAULT_CONFIG_FILE = "braghook"
DEFAULT_ENV_FILE = ".env"
DEFAULT_CONFIG = {
    "DEFAULT": {
        "workdir": ".",
        "editor": "vim",
        "editor_args": "",
        "author": "braghook",
        "author_icon": "",
        "discord_webhook": "",
    },
}


@dataclass(frozen=True)
class Config:
    """Dataclass for the configuration."""

    workdir: Path
    editor: str
    editor_args: list[str]
    author: str
    author_icon: str
    discord_webhook: str


def load_config(config_file: str, env_file: str) -> Config:
    """Load the configuration."""
    yolk = Yolk()
    yolk.load_env(env_file)
    yolk.load_config(config_file)
    config = yolk.config["DEFAULT"]

    return Config(
        workdir=Path(config.get("workdir", fallback=".")),
        editor=config.get("editor", fallback="vim"),
        editor_args=config.get("editor_args", fallback="").split(),
        author=config.get("author", fallback="braghook"),
        author_icon=config.get("author_icon", fallback=""),
        discord_webhook=config.get("discord_webhook", fallback=""),
    )


def open_editor(config: Config, filename: str) -> None:
    """Open the editor."""
    # Filename is the current date
    config.editor_args.append(str(filename))
    subprocess.run([config.editor, *config.editor_args])


def create_filename(config: Config) -> str:
    """Create the filename."""
    return str(config.workdir / datetime.now().strftime("brag-%Y-%m-%d.md"))


def read_file(filename: str) -> str:
    """Read the file."""
    with open(filename) as file:
        return file.read()


def build_discord_webhook(
    config: Config,
    content: str,
    filename: str,
) -> dict[str, Any]:
    """Build the Discord webhook."""
    return {
        "username": "braghook",
        "embeds": [
            {
                "author": {
                    "name": config.author,
                    "icon_url": config.author_icon,
                },
                "title": filename,
                "description": content,
                "color": 0x00FF00,
                "footer": {
                    "text": "Created using: https://github.com/Preocts/braghook",
                },
            },
        ],
    }


def send_discord_webhook(config: Config, content: str, filename: str) -> None:
    """Send the Discord webhook."""
    data = build_discord_webhook(config, content, filename)
    httpx.post(config.discord_webhook, json=data)


def send_message(config: Config, content: str, filename: str) -> None:
    """Send the message to defined webhooks in config."""
    if config.discord_webhook != "":
        send_discord_webhook(config, content, filename)


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
    config.read_dict(DEFAULT_CONFIG)
    with open(config_file, "w") as file:
        config.write(file)


def main(_args: list[str] | None = None) -> int:
    """Run the program."""
    args = parse_args(_args)

    if args.create_config:
        create_config(f"{DEFAULT_CONFIG_FILE}.ini")
        return 0

    config = load_config(args.config, args.env)
    filename = args.bragfile or create_filename(config)

    open_editor(config, filename)

    if not args.auto_send and get_input("Send brag? [y/N] ").lower() != "y":
        return 0

    content = read_file(filename)
    send_message(config, content, filename)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
