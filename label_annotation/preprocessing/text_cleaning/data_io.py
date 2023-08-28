from pathlib import Path
from typing import List
import pandas as pd
import time


def get_uids_from_path(path: Path) -> List[int]:
    """
    Get a list of unique identifiers (UIDs) from the specified directory path.

    Parameters
    ----------
    path : Path
        The directory path from which to extract UIDs.

    Returns
    -------
    List[int]
        A list of integers representing the UIDs.

    """
    paths = list(filter(Path.is_file, path.rglob("*.txt")))
    uids = [int(f.name.replace(".txt", "")) for f in paths]
    return uids


def read_src_txt_from_file(uid: int, text_dir: Path) -> str:
    """
    Read the contents of a text file given its unique identifier.

    Parameters
    ----------
    uid : int
        An integer representing the unique identifier of the text file to be read.
    text_dir : Path
        A Path object representing the directory where the text files are stored.

    Returns
    -------
    str
        The contents of the text file as a string.

    Raises
    ------
    FileNotFoundError
        If the text file with the specified uid is not found in the text_dir directory.
    """
    filepath = text_dir / f"{uid}.txt"
    if not filepath.exists():
        raise FileNotFoundError(f"Text file with uid {uid} not found in {text_dir}")
    with open(filepath, "r") as f:
        text = f.read()
    return text


def write_row_to_file(row: pd.Series, text_dir: Path):
    filename = f"{row['UID']}" + ".txt"  # Name as UID.txt\
    destination = text_dir / filename
    if not destination.is_file():
        with open(destination, "w") as f:
            f.write(row["Text"])
        time.sleep(0.00001)  # Too lazy to change Jupyter NB IO rate limits...
