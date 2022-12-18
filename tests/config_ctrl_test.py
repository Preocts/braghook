from __future__ import annotations

import os
import tempfile
from configparser import ConfigParser
from dataclasses import asdict
from unittest.mock import patch

from braghook import config_ctrl
from braghook.config_ctrl import Config


def test_load_config() -> None:
    config = config_ctrl.load_config("tests/braghook.ini")

    assert config.workdir == "."
    assert config.editor == "vim"
    assert config.editor_args == ""
    assert config.author == "braghook"
    assert config.author_icon == ""
    assert config.discord_webhook == ""
    assert config.discord_webhook_plain == ""
    assert config.msteams_webhook == ""
    assert config.github_user == ""
    assert config.github_pat == ""
    assert config.gist_id == ""


def test_create_config_with_tempfile() -> None:
    expected_config = ConfigParser()
    expected_config.read_dict({"DEFAULT": asdict(Config())})

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as file:
        ...
    os.remove(file.name)

    config_ctrl.create_config(file.name)

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
        with patch("braghook.config_ctrl.ConfigParser.write") as mock_write:
            config_ctrl.create_config(file.name)

        mock_write.assert_not_called()

    finally:
        os.remove(file.name)
