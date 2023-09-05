"""
BragHook.
"""
from __future__ import annotations

import argparse
import dataclasses
import http.client
import json
import logging
import re
import subprocess
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

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


DEFAULT_CONFIG_FILE = "braghook.ini"
DEFAULT_FILE_TEMPLATE = """### {date}

Motivation summary:

Shout outs:

Improvements:

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
    openweathermap_url: str = ""


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
        openweathermap_url=default.get("openweathermap_url", fallback=""),
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


def create_if_missing(filename: str) -> None:
    """Create the file if it doesn't exist."""
    if not Path(filename).exists():
        create_empty_template_file(filename)


def read_file_contents(filename: str) -> str:
    """Read the file."""
    with open(filename) as file:
        return file.read()


def send_message(config: Config, content: str) -> None:
    """Send the message to any webhooks defined in config."""
    # Define the builders here, used in the main script
    # NOTE: The key is the config field that defines the url
    # NOTE: The value is the function that builds the message
    builders: dict[str, Builder] = {
        "discord_webhook": build_discord_webhook,
        "discord_webhook_plain": build_discord_webhook_plain,
        "msteams_webhook": build_msteams_webhook,
    }

    for config_field, builder in builders.items():
        url = getattr(config, config_field)
        if not url:
            continue  # Skip if the webhook is not defined in config
        data = builder(
            author=config.author,
            author_icon=config.author_icon,
            content=content,
        )
        _post(url=url, data=data)


def split_uri(uri: str) -> tuple[str, str]:
    """Split the URI into host and path."""
    uri = uri.replace("http://", "").replace("https://", "")
    host = uri.split("/", 1)[0]
    path = uri.replace(host, "")
    return host, path


def _post(
    url: str,
    data: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> None:
    """Post the data to the URL. Expects JSON."""
    headers = headers or {"content-type": "application/json"}
    host, path = split_uri(url)

    conn = http.client.HTTPSConnection(host)
    conn.request("POST", path, json.dumps(data), headers)
    response = conn.getresponse()
    if response.status not in range(200, 300):
        logger.error("Error sending message: %s", response.read())


def _get(
    url: str,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Get the data from the URL. Expected to return JSON."""
    headers = headers or {"content-type": "application/json"}
    host, path = split_uri(url)

    conn = http.client.HTTPSConnection(host)
    conn.request("GET", path, headers=headers)
    response = conn.getresponse()
    if response.status not in range(200, 300):
        logger.error("Error fetching message: %s", response.read())
        return None
    return json.loads(response.read())


def get_weather_string(url: str) -> str:
    """Get the weather string. Uses provided OpenWeatherMap URL and API key."""
    if not url:
        return ""

    data = _get(url)

    if not data:
        return ""

    temp_min_c = f"min: {data['main']['temp_min'] - 273.15:.1f}°C"
    temp_max_c = f"max: {data['main']['temp_max'] - 273.15:.1f}°C"
    temp_feels_like_c = f"feels like: {data['main']['feels_like'] - 273.15:.1f}°C"
    humidity = f"humidity: {data['main']['humidity']}%"
    pressure = f"pressure: {data['main']['pressure']}hPa"

    return f"{temp_min_c}, {temp_max_c}, {temp_feels_like_c}, {humidity}, {pressure}\n"


def append_weather_to_content(config: Config, content: str) -> str:
    """Append weather line to content."""
    if re.search(r"^min:.+Pa$", content, flags=re.MULTILINE):
        return content

    content += "\n" if content[-1] != "\n" else ""
    weather = get_weather_string(config.openweathermap_url)
    content += weather
    return content


def post_brag_to_gist(config: Config, filename: str, content: str) -> None:
    """Post the brag to a GitHub gist."""
    # Remove http(s):// from the url
    url = config.github_api_url.replace("http://", "").replace("https://", "")

    if not config.github_user or not config.github_pat or not config.gist_id:
        return None

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
                                            "text": "sent by: braghook",
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


def send_brags(config: Config, filename: str, content: str) -> None:
    """Send brags to hooks or other targets."""
    send_message(config, content)

    post_brag_to_gist(config, filename, content)


def main(_args: list[str] | None = None) -> int:
    """Run the program."""
    args = parse_args(_args)

    if args.create_config:
        create_config()
        return 0

    config = load_config(args.config)
    filename = args.bragfile or create_filename(config)

    create_if_missing(filename)

    open_editor(config, filename)

    if not args.auto_send and get_input("Send brag? [y/N] ").lower() != "y":
        return 0

    content = read_file_contents(filename)
    append_weather_to_content(config, content)

    send_brags(config, filename, content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
