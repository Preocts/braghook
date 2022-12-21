from __future__ import annotations

import dataclasses
from configparser import ConfigParser
from pathlib import Path

DEFAULT_CONFIG_FILE = "braghook.ini"


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
