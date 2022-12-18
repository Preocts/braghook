from __future__ import annotations

from unittest.mock import patch

from braghook import cli


def test_get_input() -> None:
    with patch("builtins.input") as mock_input:
        mock_input.return_value = "y"

        assert cli.get_input("Test prompt") == "y"


def test_parse_args() -> None:
    args = cli.parse_args(
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
    with patch("braghook.config_ctrl.load_config") as mock_load_config:
        with patch("braghook.braghook.open_editor") as mock_open_editor:
            with patch("braghook.braghook.read_file") as mock_read_file:
                with patch("braghook.braghook.send_message") as mock_send_message:
                    with patch("braghook.cli.get_input") as mock_get_input:
                        with patch(
                            "braghook.braghook.post_brag_to_gist"
                        ) as mock_post_brag:
                            mock_get_input.return_value = "y"

                            cli.main(
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
    with patch("braghook.config_ctrl.load_config") as mock_load_config:
        with patch("braghook.braghook.open_editor") as mock_open_editor:
            with patch("braghook.braghook.read_file") as mock_read_file:
                with patch("braghook.braghook.send_message") as mock_send_message:
                    with patch("braghook.cli.get_input") as mock_get_input:
                        mock_get_input.return_value = "n"

                        cli.main(
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
    with patch("braghook.config_ctrl.create_config") as mock_create_config:
        with patch("braghook.config_ctrl.load_config") as mock_load_config:
            with patch("braghook.braghook.open_editor") as mock_open_editor:
                with patch("braghook.braghook.read_file") as mock_read_file:
                    with patch("braghook.braghook.send_message") as mock_send_message:
                        with patch("braghook.cli.get_input") as mock_get_input:
                            mock_get_input.return_value = "y"

                            cli.main(
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
