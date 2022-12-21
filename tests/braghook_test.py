from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from braghook import braghook
from braghook.config_ctrl import Config

MOCKFILE_CONTENTS = "# Bragging rights"


def test_create_filename() -> None:
    config = Config()
    # Fun fact, this can fail if you run it at midnight
    filename = Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md")

    assert braghook.create_filename(config) == str(filename)


def test_open_editor_file_exists() -> None:
    config = Config(editor_args="--test_flag")
    with tempfile.NamedTemporaryFile(mode="w") as file:
        with patch("subprocess.run") as mock_run:
            with patch(
                "braghook.braghook.create_empty_template_file"
            ) as mock_create_file:
                braghook.open_editor(config, file.name)

                mock_run.assert_called_once_with(["vim", "--test_flag", str(file.name)])
                mock_create_file.assert_not_called()


def test_open_editor_file_does_not_exist() -> None:
    config = Config(editor_args="--test_flag")
    filename = "tests/test-brag.md"

    with patch("subprocess.run") as mock_run:
        with patch("braghook.braghook.create_empty_template_file") as mock_create_file:
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


def test_create_empty_template_file() -> None:
    filename = "tests/test-brag.md"

    try:
        braghook.create_empty_template_file(filename)

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


def test_send_message() -> None:
    config = Config(discord_webhook="https://discord.com/api/webhooks/1234567890/abc")
    message = "Test message"

    with patch("braghook.braghook.post_message") as mock_post_message:
        braghook.send_message(config, message)

        mock_post_message.assert_called_once()


def test_post_brag_to_gist() -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    config = Config(
        github_user="test_user",
        github_pat="test_pat",
        gist_id="test_gist_id",
    )
    message = "Test message"

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 200
        braghook.post_brag_to_gist(config, "bragging-rights.md", message)

        mock_connection.assert_called_once_with("api.github.com")
        mock_connection.return_value.request.assert_called_once_with(
            "PATCH",
            "/gists/test_gist_id",
            json.dumps(
                {
                    "description": f"Brag posted: {date}",
                    "files": {"bragging-rights.md": {"content": message}},
                }
            ),
            {
                "accept": "application/vnd.github.v3+json",
                "user-agent": "test_user",
                "authorization": "token test_pat",
            },
        )
