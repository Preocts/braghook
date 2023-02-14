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
    assert config.openweathermap_url == ""


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


def test_create_if_missing() -> None:
    filename = "tests/test-brag.md"

    with patch("braghook.braghook.create_empty_template_file") as mock_create_file:
        braghook.create_if_missing(filename)

        mock_create_file.assert_called_once_with(filename)


def test_create_if_missing_does_not_overwrite() -> None:
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        file.write("Test")

    try:
        with patch("braghook.braghook.create_empty_template_file") as mock_create_file:
            braghook.create_if_missing(file.name)

        mock_create_file.assert_not_called()

    finally:
        os.remove(file.name)


def test_open_editor_file_exists() -> None:
    config = braghook.Config(editor_args="--test_flag")
    filename = "tests/test-brag.md"
    with patch("subprocess.run") as mock_run:
        braghook.open_editor(config, filename)

        mock_run.assert_called_once_with(["vim", "--test_flag", filename])


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


def test_split_uri() -> None:
    uri = "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    uri_no_path = "https://discord.com"
    expected = ("discord.com", "/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz")
    expected_no_path = ("discord.com", "")

    assert braghook.split_uri(uri) == expected
    assert braghook.split_uri(uri_no_path) == expected_no_path


def test__post() -> None:
    url = "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    message = {"message": "Test message"}
    expected_domain = "discord.com"
    expected_route = "/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    expected_headers = {"content-type": "application/json"}

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 204
        braghook._post(url, message)

        mock_connection.assert_called_once_with(expected_domain)
        mock_connection.return_value.request.assert_called_once_with(
            "POST", expected_route, json.dumps(message), expected_headers
        )


def test__post_failed(caplog: pytest.LogCaptureFixture) -> None:
    url = "https://discord.com/api/webhooks/1234567890/abcdefghijklmnopqrstuvwxyz"
    message = {"message": "Test message"}

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 400

        braghook._post(url, message)

        assert "Error sending message:" in caplog.text


def test__get() -> None:
    url = "https://api.github.com/gists/1234567890"
    response_bytes = json.dumps({"test": "response"}).encode("utf-8")
    expected_domain = "api.github.com"
    expected_route = "/gists/1234567890"
    expected_headers = {"content-type": "application/json"}
    expected_response = {"test": "response"}

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.read.return_value = (
            response_bytes
        )
        mock_connection.return_value.getresponse.return_value.status = 200
        result = braghook._get(url)

        assert result == expected_response
        mock_connection.assert_called_once_with(expected_domain)
        mock_connection.return_value.request.assert_called_once_with(
            "GET", expected_route, headers=expected_headers
        )


def test__get_failed(caplog: pytest.LogCaptureFixture) -> None:
    url = "https://api.github.com/gists/1234567890"

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 400

        result = braghook._get(url)

        assert result is None
        assert "Error fetching message:" in caplog.text


def test_send_message() -> None:
    config = braghook.Config(
        discord_webhook="https://discord.com/api/webhooks/1234567890/abc",
    )
    message = "Test message"

    with patch("braghook.braghook._post") as mock_post_message:
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


def test_post_brag_to_gist_failure(caplog: pytest.LogCaptureFixture) -> None:
    config = braghook.Config(
        github_user="test_user",
        github_pat="test_pat",
        gist_id="test_gist_id",
    )

    with patch("http.client.HTTPSConnection") as mock_connection:
        mock_connection.return_value.getresponse.return_value.status = 403
        braghook.post_brag_to_gist(config, "bragging-rights.md", "message")

        mock_connection.assert_called_once_with("api.github.com")
        assert "Error sending gist:" in caplog.text


def test_post_brag_tol_gist_no_pat() -> None:
    config = braghook.Config(
        github_user="test_user",
        github_pat="",
        gist_id="test_gist_id",
    )

    with patch("http.client.HTTPSConnection") as mock_connection:
        braghook.post_brag_to_gist(config, "bragging-rights.md", "message")

        mock_connection.assert_not_called()


def test_get_weather_string() -> None:
    config = braghook.Config(
        openweathermap_url="https://api.openweathermap.org/data/2.5/weather"
    )
    weather = {
        "main": {
            "temp": 300.15,
            "feels_like": 300.15,
            "temp_min": 300.15,
            "temp_max": 300.15,
            "pressure": 1013,
            "humidity": 81,
        },
        "wind": {"speed": 4.6, "deg": 90},
        "clouds": {"all": 90},
        "weather": [{"description": "light intensity drizzle"}],
    }
    expected_weather_string = "min: 27.0°C, max: 27.0°C, feels like: 27.0°C, humidity: 81%, pressure: 1013hPa\n"  # noqa: E501

    with patch("braghook.braghook._get") as mock_get:
        mock_get.return_value = weather
        result = braghook.get_weather_string(config.openweathermap_url)

        assert result == expected_weather_string


def test_get_weather_string_no_url() -> None:
    config = braghook.Config(openweathermap_url="")

    with patch("braghook.braghook._get") as mock_get:
        result = braghook.get_weather_string(config.openweathermap_url)

        mock_get.assert_not_called()
        assert result == ""


def test_get_weather_empty_response() -> None:
    config = braghook.Config(
        openweathermap_url="https://api.openweathermap.org/data/2.5/weather"
    )

    with patch("braghook.braghook._get") as mock_get:
        mock_get.return_value = {}
        result = braghook.get_weather_string(config.openweathermap_url)

        assert result == ""


def test_append_weather_to_content_only_once() -> None:
    config = braghook.Config(openweathermap_url="https://mock.com/api/openweather")
    weather_string = "min: 27.0°C, max: 27.0°C, feels like: 27.0°C, humidity: 81%, pressure: 1013hPa\n"  # noqa: E501
    content = MOCKFILE_CONTENTS

    with patch("braghook.braghook.get_weather_string") as mock_weather_string:
        mock_weather_string.return_value = weather_string
        # Call twice to ensure it only appends once
        content = braghook.append_weather_to_content(config, content)
        content = braghook.append_weather_to_content(config, content)
        print(content)
        mock_weather_string.assert_called_once()


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
    module = "braghook.braghook"
    # Turn black off to make this more readable and easier to maintain
    # fmt: off
    with patch("braghook.braghook.load_config") as load_config, \
            patch(f"{module}.create_if_missing") as create_if_missing, \
            patch(f"{module}.open_editor") as open_editor, \
            patch(f"{module}.read_file_contents") as read_file, \
            patch(f"{module}.append_weather_to_content") as append_weather_to_content, \
            patch(f"{module}.send_message") as send_message, \
            patch(f"{module}.get_input") as get_input, \
            patch(f"{module}.post_brag_to_gist") as post_brag:
        # fmt: on

        get_input.return_value = "y"

        braghook.main(
            [
                "--config",
                "tests/bh.ini",
                "--bragfile",
                "tests/brag.md",
            ]
        )

        load_config.assert_called_once_with("tests/bh.ini")
        open_editor.assert_called_once()
        read_file.assert_called_once()
        create_if_missing.assert_called_once()
        append_weather_to_content.assert_called_once()
        send_message.assert_called_once()
        get_input.assert_called_once()
        post_brag.assert_called_once()


def test_main_no_send() -> None:
    module = "braghook.braghook"
    # Turn black off to make this more readable and easier to maintain
    # fmt: off
    with patch(f"{module}.load_config") as load_config, \
            patch(f"{module}.create_if_missing") as create_if_missing, \
            patch(f"{module}.open_editor") as open_editor, \
            patch(f"{module}.read_file_contents") as read_file, \
            patch(f"{module}.append_weather_to_content") as append_weather_to_content, \
            patch(f"{module}.send_message") as send_message, \
            patch(f"{module}.get_input") as get_input:
        # fmt: on

        get_input.return_value = "n"

        braghook.main(
            [
                "--config",
                "tests/braghook.ini",
                "--bragfile",
                "tests/brag.md",
            ]
        )

        load_config.assert_called_once_with("tests/braghook.ini")
        create_if_missing.assert_called_once()
        open_editor.assert_called_once()
        read_file.assert_not_called()
        append_weather_to_content.assert_not_called()
        send_message.assert_not_called()


def test_main_create_config() -> None:
    module = "braghook.braghook"
    # Turn black off to make this more readable and easier to maintain
    # Someday 3.9 will go EOL and we can use parenthesis instead of \
    # fmt: off
    with patch(f"{module}.create_config") as create_config, \
            patch(f"{module}.load_config") as load_config, \
            patch(f"{module}.create_if_missing") as create_if_missing, \
            patch(f"{module}.open_editor") as open_editor, \
            patch(f"{module}.read_file_contents") as read_file, \
            patch(f"{module}.append_weather_to_content") as append_weather_to_content, \
            patch(f"{module}.send_message") as send_message, \
            patch(f"{module}.get_input") as get_input:
        # fmt: on

        get_input.return_value = "y"

        braghook.main(
            [
                "--config",
                "tests/braghook.ini",
                "--bragfile",
                "tests/brag.md",
                "--create-config",
            ]
        )

        create_config.assert_called_once()
        load_config.assert_not_called()
        create_if_missing.assert_not_called()
        open_editor.assert_not_called()
        read_file.assert_not_called()
        append_weather_to_content.assert_not_called()
        send_message.assert_not_called()
        get_input.assert_not_called()
