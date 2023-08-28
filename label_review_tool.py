from colorama import init as colorama_init
from src.annotation_utils.parser import parse_args
from src.review_newly_ingested import review_newly_ingested_links
from src.section_explorer import annotate_sections
from typing import Dict, Any
import argparse


def main(subcommand: str, args: Dict[str, Any]):
    if subcommand == "ingest":
        review_newly_ingested_links(
            prev_length=args["prevlen"],
            data_path=args["data"],
            metadata_path=args["metadata"],
            text_dir=args["text"],
            clean=args["clean"],
        )
    elif subcommand == "secExplorer":
        annotate_sections(data_path=args["data"], prev_length=args["prevlen"])
    else:
        raise argparse.ArgumentError(f"Invalid subcommmand: {subcommand}")


# CWD = Path.cwd()
# TEMP_DIR = CWD / "Other"
if __name__ == "__main__":
    colorama_init(autoreset=True)
    subcommand, args = parse_args()
    main(subcommand, args)
