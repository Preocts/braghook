from __future__ import annotations

import json
import os
import tempfile
from configparser import ConfigParser
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from braghook import braghook
from braghook.braghook import Config

MOCKFILE_CONTENTS = "# Bragging rights"


def test_load_config() -> None:
    config = braghook.load_config("tests/braghook.ini")

    assert config.workdir == "."
    assert config.editor == "vim"
    assert config.editor_args == ""
    assert config.author == "braghook"
    assert config.author_icon == ""
    assert config.discord_webhook == ""
    assert config.discord_webhook_plain == ""
    assert config.msteams_webhook == ""


def test_get_filename() -> None:
    config = Config()
    # Fun fact, this can fail if you run it at midnight
    filename = Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md")

    assert braghook.get_filename(config) == str(filename)


def test_open_editor_file_exists() -> None:
    config = Config(editor_args="--test_flag")
    with tempfile.NamedTemporaryFile(mode="w") as file:
        with patch("subprocess.run") as mock_run:
            with patch("braghook.braghook.create_file") as mock_create_file:
                braghook.open_editor(config, file.name)

                mock_run.assert_called_once_with(["vim", "--test_flag", str(file.name)])
                mock_create_file.assert_not_called()


def test_open_editor_file_does_not_exist() -> None:
    config = Config(editor_args="--test_flag")
    filename = "tests/test-brag.md"

    with patch("subprocess.run") as mock_run:
        with patch("braghook.braghook.create_file") as mock_create_file:
            braghook.open_editor(config, filename)

            mock_create_file.assert_called_once_with(filename)
            mock_run.assert_called_once_with(["vim", "--test_flag", str(filename)])


def test_read_file() -> None:
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
            file.write(MOCKFILE_CONTENTS)

        assert braghook.read_file(file.name) == MOCKFILE_CONTENTS

    finally:
        os.remove(file.name)


def test_create_file() -> None:
    filename = "tests/test-brag.md"

    try:
        braghook.create_file(filename)

        assert Path(filename).is_file()

    finally:
        os.remove(filename)


def test_post_message() -> None:
    url = "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    message = {"message": "Test message"}
    expected_domain = "discord.com"
    expected_route = "/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    expected_headers = {"content-type": "application/json"}

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 204
        braghook.post_message(url, message)

        mock_connection.assert_called_once_with(expected_domain)
        mock_connection.return_value.request.assert_called_once_with(
            "POST", expected_route, json.dumps(message), expected_headers
        )


def test_post_message_failed(caplog: pytest.LogCaptureFixture) -> None:
    url = "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    message = {"message": "Test message"}

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 400

        braghook.post_message(url, message)

        assert "Error sending message:" in caplog.text


def test_send_message_discord() -> None:
    config = Config(
        discord_webhook="https://discord.com/api/webhooks/1234567890/abcdefg"
    )
    message = "Test message"
    data = braghook.build_discord_webhook(config.author, config.author_icon, message)

    with patch("braghook.braghook.post_message") as mock_post_message:
        braghook.send_message(config, message)

        mock_post_message.assert_called_once_with(url=config.discord_webhook, data=data)


def test_send_message_discord_plain() -> None:
    config = Config(
        discord_webhook_plain="https://discord.com/api/webhooks/1234567890/abcdefg"
    )
    message = "Test message"
    data = braghook.build_discord_webhook_plain(message)

    with patch("braghook.braghook.post_message") as mock_post_message:
        braghook.send_message(config, message)

        mock_post_message.assert_called_once_with(
            url=config.discord_webhook_plain, data=data
        )


def test_send_message_msteams() -> None:
    config = Config(
        msteams_webhook="https://outlook.office.com/webhook/1234567890/abcdefg"
    )
    message = "Test message"
    data = braghook.build_msteams_webhook(config.author, config.author_icon, message)

    with patch("braghook.braghook.post_message") as mock_post_message:
        braghook.send_message(config, message)

        mock_post_message.assert_called_once_with(url=config.msteams_webhook, data=data)


def test_send_message_no_hooks() -> None:
    config = Config()
    message = "Test message"

    with patch("http.client.HTTPSConnection") as mock_connection:
        braghook.send_message(config, message)

        mock_connection.assert_not_called()


def test_create_config_with_tempfile() -> None:
    expected_config = ConfigParser()
    expected_config.read_dict({"DEFAULT": asdict(Config())})

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        ...
    os.remove(file.name)

    braghook.create_config(file.name)

    try:
        actual_config = ConfigParser()
        actual_config.read(file.name)

        assert actual_config == expected_config

    finally:
        os.remove(file.name)


def test_create_config_does_not_overwrite() -> None:
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        file.write("[braghook]\n")

    try:
        with patch("braghook.braghook.ConfigParser.write") as mock_write:
            braghook.create_config(file.name)

        mock_write.assert_not_called()

    finally:
        os.remove(file.name)


def test_extract_title_from_message() -> None:
    message = "## Test message \n Test message body"
    expected_title = "Test message"

    assert braghook.extract_title_from_message(message) == expected_title
