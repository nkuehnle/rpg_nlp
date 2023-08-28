from typing import Tuple, Dict, Any
import argparse
from pathlib import Path


def add_common_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-d",
        "--data",
        dest="data",
        type=Path,
        required=True,
        help="Path to links to manually review",
    )
    parser.add_argument(
        "-p",
        "--prevlen",
        dest="prevlen",
        type=int,
        required=False,
        default=35,
        help="Maximum lines of text to display at once",
    )


def build_ingest_command(subparsers: argparse._SubParsersAction):
    subparser: argparse.ArgumentParser = subparsers.add_parser(
        "ingest", help="Review newly collected URLs/PRAW data"
    )
    add_common_args(subparser)
    subparser.add_argument(
        "-m",
        "--meta",
        dest="metadata",
        type=Path,
        required=True,
        help="Path to comment/link metadata",
    )
    subparser.add_argument(
        "-t",
        "--text",
        dest="text",
        type=Path,
        required=True,
        help="Path to text directory",
    )
    subparser.add_argument(
        "--clean", action="store_true", help="Clean text before displaying"
    )


def build_section_explorer(subparsers: argparse._SubParsersAction):
    subparser = subparsers.add_parser(
        "secExplorer", help="Review newly collected URLs/PRAW data"
    )
    add_common_args(subparser)


def build_main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manually review DnD homebrew lnks found in comments"
    )
    subparsers = parser.add_subparsers(title="Subcommands", dest="subcommand")
    build_ingest_command(subparsers)
    build_section_explorer(subparsers)

    return parser


def parse_args() -> Tuple[str, Dict[str, Any]]:
    parser = build_main_parser()
    args: Dict[str, Any] = vars(parser.parse_args())
    subcommand: str = args["subcommand"]
    args = {k: v for k, v in args.items() if k != "subcommand"}

    return subcommand, args


if __name__ == "__main__":
    args, parser = parse_args()
