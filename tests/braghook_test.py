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
    assert config.github_api_url == "https://api.github.com"
    assert config.github_user == ""
    assert config.github_pat == ""
    assert config.gist_id == ""


def test_create_config_with_tempfile() -> None:
    expected_config = ConfigParser()
    expected_config.read_dict({"DEFAULT": asdict(braghook.Config())})

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


def test_create_filename() -> None:
    config = braghook.Config()
    # Fun fact, this can fail if you run it at midnight
    filename = Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md")

    assert braghook.create_filename(config) == str(filename)


def test_open_editor_file_exists() -> None:
    config = braghook.Config(editor_args="--test_flag")
    with tempfile.NamedTemporaryFile(mode="w") as file:
        with patch("subprocess.run") as mock_run:
            with patch(
                "braghook.braghook.create_empty_template_file"
            ) as mock_create_file:
                braghook.open_editor(config, file.name)

                mock_run.assert_called_once_with(["vim", "--test_flag", str(file.name)])
                mock_create_file.assert_not_called()


def test_open_editor_file_does_not_exist() -> None:
    config = braghook.Config(editor_args="--test_flag")
    filename = "tests/test-brag.md"

    with patch("subprocess.run") as mock_run:
        with patch("braghook.braghook.create_empty_template_file") as mock_create_file:
            braghook.open_editor(config, filename)

            mock_create_file.assert_called_once_with(filename)
            mock_run.assert_called_once_with(["vim", "--test_flag", str(filename)])


def test_read_file_contents() -> None:
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
            file.write(MOCKFILE_CONTENTS)

        assert braghook.read_file_contents(file.name) == MOCKFILE_CONTENTS

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
    config = braghook.Config(
        discord_webhook="https://discord.com/api/webhooks/1234567890/abc",
    )
    message = "Test message"

    with patch("braghook.braghook.post_message") as mock_post_message:
        braghook.send_message(config, message)

        mock_post_message.assert_called_once()


def test_post_brag_to_gist() -> None:
    date = datetime.now().strftime("%Y-%m-%d")
    config = braghook.Config(
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


@pytest.mark.parametrize(
    "message, expected_title",
    [
        ("Test message", ""),
        ("## Test message", "Test message"),
        ("## Test message \n Test message body", "Test message"),
    ],
)
def test_extract_title_from_message(message: str, expected_title: str) -> None:
    assert braghook.extract_title_from_message(message) == expected_title


@pytest.mark.parametrize(
    "message, expected_message",
    [
        ("Test message", "Test message"),
        ("## Test message", "## Test message"),
        ("- Test message", ":small_blue_diamond: Test message"),
        ("  - Test message", ":small_orange_diamond: Test message"),
    ],
)
def test_bullet_markes_to_diamonds(message: str, expected_message: str) -> None:
    assert braghook.bullet_marks_to_diamonds(message) == expected_message


@pytest.mark.parametrize(
    "message, expected_message",
    [
        ("Test message", "Test message"),
        ("## Test message", "**Test message**"),
        ("### Test message", "**Test message**"),
        ("#### Test message", "**Test message**"),
        ("##### Test message", "##### Test message"),  # more than four are not headers
    ],
)
def test_headers_to_bold(message: str, expected_message: str) -> None:
    result = braghook.headers_to_bold(message)

    assert result == expected_message


def test_build_discord_webhook() -> None:
    # Test the results of the webhook by sending it to a Discord channel
    # this just tests that nothing raises an exception
    author = "Test Author"
    author_icon = "https://example.com/icon.png"
    message = "Test message"

    result = braghook.build_discord_webhook(author, author_icon, message)

    assert result


def test_build_plain_discord_webhook() -> None:
    # Test the results of the webhook by sending it to a Discord channel
    # this just tests that nothing raises an exception
    author = "Test Author"
    author_icon = "https://example.com/icon.png"
    message = "Test message"

    result = braghook.build_discord_webhook_plain(author, author_icon, message)

    assert result


def test_build_msteams_webhook() -> None:
    # Test the results of the webhook by sending it to a MS Teams channel
    # this just tests that nothing raises an exception
    author = "Test Author"
    author_icon = "https://example.com/icon.png"
    message = "Test message"

    result = braghook.build_msteams_webhook(author, author_icon, message)

    assert result


def test_get_input() -> None:
    with patch("builtins.input") as mock_input:
        mock_input.return_value = "y"

        assert braghook.get_input("Test prompt") == "y"


def test_parse_args() -> None:
    args = braghook.parse_args(
        [
            "--config",
            "tests/braghook.ini",
            "--bragfile",
            "tests/brag.md",
            "--create-config",
            "--auto-send",
        ]
    )

    assert args.config == "tests/braghook.ini"
    assert args.bragfile == "tests/brag.md"
    assert args.create_config
    assert args.auto_send


def test_main() -> None:
    with patch("braghook.braghook.load_config") as mock_load_config:
        with patch("braghook.braghook.open_editor") as mock_open_editor:
            with patch("braghook.braghook.read_file_contents") as mock_read_file:
                with patch("braghook.braghook.send_message") as mock_send_message:
                    with patch("braghook.braghook.get_input") as mock_get_input:
                        with patch(
                            "braghook.braghook.post_brag_to_gist"
                        ) as mock_post_brag:
                            mock_get_input.return_value = "y"

                            braghook.main(
                                [
                                    "--config",
                                    "tests/braghook.ini",
                                    "--bragfile",
                                    "tests/brag.md",
                                ]
                            )

                            mock_load_config.assert_called_once_with(
                                "tests/braghook.ini"
                            )
                            mock_open_editor.assert_called_once()
                            mock_read_file.assert_called_once()
                            mock_send_message.assert_called_once()
                            mock_get_input.assert_called_once()
                            mock_post_brag.assert_called_once()


def test_main_no_send() -> None:
    with patch("braghook.braghook.load_config") as mock_load_config:
        with patch("braghook.braghook.open_editor") as mock_open_editor:
            with patch("braghook.braghook.read_file_contents") as mock_read_file:
                with patch("braghook.braghook.send_message") as mock_send_message:
                    with patch("braghook.braghook.get_input") as mock_get_input:
                        mock_get_input.return_value = "n"

                        braghook.main(
                            [
                                "--config",
                                "tests/braghook.ini",
                                "--bragfile",
                                "tests/brag.md",
                            ]
                        )

                        mock_load_config.assert_called_once_with("tests/braghook.ini")
                        mock_open_editor.assert_called_once()
                        mock_read_file.assert_not_called()
                        mock_send_message.assert_not_called()


def test_main_create_config() -> None:
    with patch("braghook.braghook.create_config") as mock_create_config:
        with patch("braghook.braghook.load_config") as mock_load_config:
            with patch("braghook.braghook.open_editor") as mock_open_editor:
                with patch("braghook.braghook.read_file_contents") as mock_read_file:
                    with patch("braghook.braghook.send_message") as mock_send_message:
                        with patch("braghook.braghook.get_input") as mock_get_input:
                            mock_get_input.return_value = "y"

                            braghook.main(
                                [
                                    "--config",
                                    "tests/braghook.ini",
                                    "--bragfile",
                                    "tests/brag.md",
                                    "--create-config",
                                ]
                            )

                            mock_create_config.assert_called_once()
                            mock_load_config.assert_not_called()
                            mock_open_editor.assert_not_called()
                            mock_read_file.assert_not_called()
                            mock_send_message.assert_not_called()
                            mock_get_input.assert_not_called()
