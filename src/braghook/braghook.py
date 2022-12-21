"""
BragHook.
"""
from __future__ import annotations

import argparse
import dataclasses
import http.client
import json
import logging
import subprocess
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from braghook import webhook_builder

if TYPE_CHECKING:
    ...

DEFAULT_CONFIG_FILE = "braghook.ini"
DEFAULT_FILE_TEMPLATE = """### {date}

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
    editor_args: str = ""
    author: str = "braghook"
    author_icon: str = ""
    discord_webhook: str = ""
    discord_webhook_plain: str = ""
    msteams_webhook: str = ""
    github_api_url: str = "https://api.github.com"
    github_user: str = ""
    github_pat: str = ""
    gist_id: str = ""


logger = logging.getLogger(__name__)


def load_config(config_file: str | None = None) -> Config:
    """Load the configuration. If no config file is given, the default is used."""
    config_file = config_file or DEFAULT_CONFIG_FILE
    config = ConfigParser()
    config.read(config_file)
    default = config["DEFAULT"]

    return Config(
        workdir=default.get("workdir", fallback="."),
        editor=default.get("editor", fallback="vim"),
        editor_args=default.get("editor_args", fallback=""),
        author=default.get("author", fallback="braghook"),
        author_icon=default.get("author_icon", fallback=""),
        discord_webhook=default.get("discord_webhook", fallback=""),
        discord_webhook_plain=default.get("discord_webhook_plain", fallback=""),
        msteams_webhook=default.get("msteams_webhook", fallback=""),
        github_user=default.get("github_user", fallback=""),
        github_pat=default.get("github_pat", fallback=""),
        gist_id=default.get("gist_id", fallback=""),
    )


def create_config(config_file: str | None = None) -> None:
    """Create the config file. If no config file is given, the default is used."""
    config_file = config_file or DEFAULT_CONFIG_FILE
    # Avoid overwriting existing config
    if Path(config_file).exists():
        print(f"Config file already exists: {config_file}")
        return

    config = ConfigParser()
    config.read_dict({"DEFAULT": dataclasses.asdict(Config())})
    with open(config_file, "w") as file:
        config.write(file)


def open_editor(config: Config, filename: str) -> None:
    """Open the editor."""
    if not Path(filename).exists():
        create_empty_template_file(filename)
    args = config.editor_args.split()

    args.append(str(filename))
    subprocess.run([config.editor, *args])


def create_empty_template_file(filename: str) -> None:
    """Create the file."""
    with open(filename, "w") as file:
        file.write(
            DEFAULT_FILE_TEMPLATE.format(date=datetime.now().strftime("%Y-%m-%d"))
        )


def create_filename(config: Config) -> str:
    """Create the filename using the current date."""
    return str(Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md"))


def read_file_contents(filename: str) -> str:
    """Read the file."""
    with open(filename) as file:
        return file.read()


def send_message(config: Config, content: str) -> None:
    """Send the message to any webhooks defined in config."""
    for config_field, builder in webhook_builder.BUILDERS.items():
        url = getattr(config, config_field)
        if not url:
            continue  # Skip if the webhook is not defined in config
        data = builder(
            author=config.author,
            author_icon=config.author_icon,
            content=content,
        )
        post_message(url=url, data=data)


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


def post_brag_to_gist(config: Config, filename: str, content: str) -> None:
    """Post the brag to a GitHub gist."""
    # Remove http(s):// from the url
    url = config.github_api_url.replace("http://", "").replace("https://", "")

    if not config.github_user or not config.github_pat or not config.gist_id:
        return

    conn = http.client.HTTPSConnection(url)
    headers = {
        "accept": "application/vnd.github.v3+json",
        "user-agent": config.github_user,
        "authorization": f"token {config.github_pat}",
    }

    data = {
        "description": f"Brag posted: {datetime.now().strftime('%Y-%m-%d')}",
        "files": {filename: {"content": content}},
    }

    conn.request("PATCH", f"/gists/{config.gist_id}", json.dumps(data), headers)
    response = conn.getresponse()
    if response.status not in range(200, 300):
        logger.error("Error sending gist: %s", response.read())


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
    return parser.parse_args(args)


def get_input(prompt: str) -> str:
    """Get input from the user."""
    return input(prompt)


def main(_args: list[str] | None = None) -> int:
    """Run the program."""
    args = parse_args(_args)

    if args.create_config:
        create_config()
        return 0

    config = load_config(args.config)
    filename = args.bragfile or create_filename(config)

    open_editor(config, filename)

    if not args.auto_send and get_input("Send brag? [y/N] ").lower() != "y":
        return 0

    content = read_file_contents(filename)
    send_message(config, content)
    post_brag_to_gist(config, filename, content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
