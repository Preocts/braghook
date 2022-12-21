from __future__ import annotations

import argparse

from braghook import braghook
from braghook import config_ctrl


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse the arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bragfile",
        "-b",
        type=str,
        help="The brag file to use",
        default=None,
    )
    parser.add_argument(
        "--create-config",
        "-C",
        action="store_true",
        help="Create the config file",
    )
    parser.add_argument(
        "--auto-send",
        "-a",
        action="store_true",
        help="Automatically send the brag",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=config_ctrl.DEFAULT_CONFIG_FILE,
        help="The config file to use",
    )
    return parser.parse_args(args)


def get_input(prompt: str) -> str:
    """Get input from the user."""
    return input(prompt)


def main(_args: list[str] | None = None) -> int:
    """Run the program."""
    args = parse_args(_args)

    if args.create_config:
        config_ctrl.create_config()
        return 0

    config = config_ctrl.load_config(args.config)
    filename = args.bragfile or braghook.create_filename(config)

    braghook.open_editor(config, filename)

    if not args.auto_send and get_input("Send brag? [y/N] ").lower() != "y":
        return 0

    content = braghook.read_file(filename)
    braghook.send_message(config, content)
    braghook.post_brag_to_gist(config, filename, content)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
