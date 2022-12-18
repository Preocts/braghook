from __future__ import annotations

import pytest
from braghook import webhook_builder


@pytest.mark.parametrize(
    "message, expected_title",
    [
        ("Test message", ""),
        ("## Test message", "Test message"),
        ("## Test message \n Test message body", "Test message"),
    ],
)
def test_extract_title_from_message(message: str, expected_title: str) -> None:
    assert webhook_builder.extract_title_from_message(message) == expected_title


def test_build_discord_webhook() -> None:
    # Test the results of the webhook by sending it to a Discord channel
    # this just tests that nothing raises an exception
    author = "Test Author"
    author_icon = "https://example.com/icon.png"
    message = "Test message"

    result = webhook_builder.build_discord_webhook(author, author_icon, message)

    assert result


def test_build_plain_discord_webhook() -> None:
    # Test the results of the webhook by sending it to a Discord channel
    # this just tests that nothing raises an exception
    message = "Test message"

    result = webhook_builder.build_discord_webhook_plain(message)

    assert result


def test_build_msteams_webhook() -> None:
    # Test the results of the webhook by sending it to a MS Teams channel
    # this just tests that nothing raises an exception
    author = "Test Author"
    author_icon = "https://example.com/icon.png"
    message = "Test message"

    result = webhook_builder.build_msteams_webhook(author, author_icon, message)

    assert result
