from __future__ import annotations

import os
import tempfile
from configparser import ConfigParser
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import braghook
from braghook import Config

MOCKFILE_CONTENTS = "# Bragging rights"


def test_load_config() -> None:
    config = braghook.load_config("tests/braghook.ini", "tests/.env")

    assert config.workdir == "."
    assert config.editor == "vim"
    assert config.editor_args == []
    assert config.author == "braghook"
    assert config.author_icon == ""
    assert config.discord_webhook == ""
    assert config.discord_webhook_plain == ""


def test_get_filename() -> None:
    config = Config()
    # Fun fact, this can fail if you run it at midnight
    filename = Path(config.workdir) / datetime.now().strftime("brag-%Y-%m-%d.md")

    assert braghook.get_filename(config) == str(filename)


def test_open_editor_file_exists() -> None:
    config = Config(editor_args=["--test_flag"])
    with tempfile.NamedTemporaryFile(mode="w") as file:
        with patch("subprocess.run") as mock_run:
            with patch("braghook.create_file") as mock_create_file:
                braghook.open_editor(config, file.name)

                mock_run.assert_called_once_with(["vim", "--test_flag", str(file.name)])
                mock_create_file.assert_not_called()


def test_open_editor_file_does_not_exist() -> None:
    config = Config(editor_args=["--test_flag"])
    filename = "tests/test-brag.md"

    with patch("subprocess.run") as mock_run:
        with patch("braghook.create_file") as mock_create_file:
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


def test_send_message_discord() -> None:
    config = Config(
        discord_webhook="https://discord.com/api/webhooks/1234567890/abcdefghij"
    )
    message = "Test message"
    expected_webhook = braghook.build_discord_webhook(
        author=config.author,
        author_icon=config.author_icon,
        content=message,
    )

    with patch("httpx.post") as mock_post:
        braghook.send_message(config, message, "mock")

        mock_post.assert_called_once_with(
            config.discord_webhook,
            json=expected_webhook,
            headers=None,
        )


def test_send_message_discord_plain() -> None:
    config = Config(
        discord_webhook_plain="https://discord.com/api/webhooks/1234567890/abcdefghij",
    )
    message = "Test message"
    expected_webhook = braghook.build_discord_webhook_plain(message)

    with patch("httpx.post") as mock_post:
        braghook.send_message(config, message, "mock")

        mock_post.assert_called_once_with(
            config.discord_webhook_plain,
            json=expected_webhook,
            headers=None,
        )


def test_send_message_no_hooks() -> None:
    config = Config()
    message = "Test message"

    with patch("httpx.post") as mock_post:
        braghook.send_message(config, message, "mock")

        mock_post.assert_not_called()


def test_get_input() -> None:
    with patch("builtins.input") as mock_input:
        mock_input.return_value = "y"

        assert braghook.get_input("Test prompt") == "y"


def test_parse_args() -> None:
    args = braghook.parse_args(
        [
            "--config",
            "tests/braghook.ini",
            "--env",
            "tests/.env",
            "--bragfile",
            "tests/brag.md",
            "--create-config",
            "--auto-send",
        ]
    )

    assert args.config == "tests/braghook.ini"
    assert args.env == "tests/.env"
    assert args.bragfile == "tests/brag.md"
    assert args.create_config
    assert args.auto_send


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
        with patch("braghook.ConfigParser.write") as mock_write:
            braghook.create_config(file.name)

        mock_write.assert_not_called()

    finally:
        os.remove(file.name)


def test_extract_title_from_message() -> None:
    message = "## Test message \n Test message body"
    expected_title = "Test message"

    assert braghook.extract_title_from_message(message) == expected_title


def test_main() -> None:
    with patch("braghook.load_config") as mock_load_config:
        with patch("braghook.open_editor") as mock_open_editor:
            with patch("braghook.read_file") as mock_read_file:
                with patch("braghook.send_message") as mock_send_message:
                    with patch("braghook.get_input") as mock_get_input:
                        mock_get_input.return_value = "y"

                        braghook.main(
                            [
                                "--config",
                                "tests/braghook.ini",
                                "--env",
                                "tests/.env",
                                "--bragfile",
                                "tests/brag.md",
                            ]
                        )

                        mock_load_config.assert_called_once_with(
                            "tests/braghook.ini", "tests/.env"
                        )
                        mock_open_editor.assert_called_once()
                        mock_read_file.assert_called_once()
                        mock_send_message.assert_called_once()
                        mock_get_input.assert_called_once()


def test_main_no_send() -> None:
    with patch("braghook.load_config") as mock_load_config:
        with patch("braghook.open_editor") as mock_open_editor:
            with patch("braghook.read_file") as mock_read_file:
                with patch("braghook.send_message") as mock_send_message:
                    with patch("braghook.get_input") as mock_get_input:
                        mock_get_input.return_value = "n"

                        braghook.main(
                            [
                                "--config",
                                "tests/braghook.ini",
                                "--env",
                                "tests/.env",
                                "--bragfile",
                                "tests/brag.md",
                            ]
                        )

                        mock_load_config.assert_called_once_with(
                            "tests/braghook.ini", "tests/.env"
                        )
                        mock_open_editor.assert_called_once()
                        mock_read_file.assert_not_called()
                        mock_send_message.assert_not_called()


def test_main_create_config() -> None:
    with patch("braghook.create_config") as mock_create_config:
        with patch("braghook.load_config") as mock_load_config:
            with patch("braghook.open_editor") as mock_open_editor:
                with patch("braghook.read_file") as mock_read_file:
                    with patch("braghook.send_message") as mock_send_message:
                        with patch("braghook.get_input") as mock_get_input:
                            mock_get_input.return_value = "y"

                            braghook.main(
                                [
                                    "--config",
                                    "tests/braghook.ini",
                                    "--env",
                                    "tests/.env",
                                    "--bragfile",
                                    "tests/brag.md",
                                    "--create-config",
                                ]
                            )

                            mock_create_config.assert_called_once_with(
                                f"{braghook.DEFAULT_CONFIG_FILE}.ini"
                            )
                            mock_load_config.assert_not_called()
                            mock_open_editor.assert_not_called()
                            mock_read_file.assert_not_called()
                            mock_send_message.assert_not_called()
                            mock_get_input.assert_not_called()
