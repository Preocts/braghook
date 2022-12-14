from __future__ import annotations

import os
import tempfile
from collections.abc import Generator
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

import braghook

MOCKFILE_CONTENTS = "# Bragging rights"


@pytest.fixture
def filled_file() -> Generator[Path, None, None]:
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
            file.write(MOCKFILE_CONTENTS)

        yield Path(file.name)

    finally:
        os.remove(file.name)


def test_load_config() -> None:
    config = braghook.load_config("tests/braghook.ini", "tests/.env")

    assert config.workdir == Path(".")
    assert config.editor == "vim"
    assert config.editor_args == []
    assert config.discord_webhook == ""
    assert config.author == "braghook"
    assert config.author_icon == ""


def test_create_filename() -> None:
    config = braghook.Config(
        workdir=Path("."),
        editor="vim",
        editor_args=[],
        discord_webhook="",
        author="",
        author_icon="",
    )
    filename = config.workdir / datetime.now().strftime("brag-%Y-%m-%d.md")

    assert braghook.create_filename(config) == str(filename)


def test_open_editor() -> None:
    config = braghook.Config(
        workdir=Path("."),
        editor="vim",
        editor_args=["--test_flag"],
        discord_webhook="",
        author="",
        author_icon="",
    )
    filename = str(config.workdir / datetime.now().strftime("brag-%Y-%m-%d.md"))

    with patch("subprocess.run") as mock_run:
        braghook.open_editor(config, filename)

        mock_run.assert_called_once_with(["vim", "--test_flag", str(filename)])


def test_read_file(filled_file: Path) -> None:
    assert braghook.read_file(str(filled_file)) == MOCKFILE_CONTENTS


def test_send_message_discord() -> None:
    config = braghook.Config(
        workdir=Path("."),
        editor="vim",
        editor_args=[],
        discord_webhook="https://discord.com/api/webhooks/1234567890/abcdefghij",
        author="",
        author_icon="",
    )
    message = "Test message"
    expected_webhook = braghook.build_discord_webhook(config, message, "mock")

    with patch("httpx.post") as mock_post:
        braghook.send_message(config, message, "mock")

        mock_post.assert_called_once_with(
            config.discord_webhook,
            json=expected_webhook,
        )


def test_send_message_no_hooks() -> None:
    config = braghook.Config(
        workdir=Path("."),
        editor="vim",
        editor_args=[],
        discord_webhook="",
        author="",
        author_icon="",
    )
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
    expected_config.read_dict(braghook.DEFAULT_CONFIG)

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
