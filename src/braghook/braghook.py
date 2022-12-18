from __future__ import annotations

import http.client
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from typing import TYPE_CHECKING

from braghook import webhook_builder

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


def send_message(config: Config, content: str) -> None:
    """Send the message to any webhooks defined in config."""

    for config_label, builder in webhook_builder.BUILDERS.items():
        url = getattr(config, config_label)
        if not url:
            continue
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
