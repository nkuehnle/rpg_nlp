# Processing/updating data
import pandas as pd
import numpy as np

# Web/collecting data
import requests
import bs4

# Annotation/ system
from pathlib import Path
from typing import Tuple, List, Optional, Dict
import sys

# CLI/UI
import inquirer
import re  # Cutting out excess space

# Custom modules
## Annotation CLI only
from .annotation_utils.data_io import (
    pandas_from_path,
    fill_missing_cols,
    save_pandas_to_path,
)
from .annotation_utils.uix_utils import ANNOUNCE, RAW, Cyans

## Shared with scraping/processing notebooks
from .preprocessing.praw_processing import conform_url
from .preprocessing.text_cleaning import clean_scraped_text
from .scraping import get_source_texts
from .scraping import _grab_src_url

FLAIR = [
    "Class",
    "Subclass",
    "Monster",
    "Mechanic",
    "Race",
    "Spell",
    "Item",
    "Feat",
    "Resource",
    "Compendium",
    "Background",
    "Adventure",
    "Prestige",
    "World",
    "Other",
    None,
]


class EmptyText(Exception):
    pass


class SubmissionRecord:
    def __init__(self, title, id):
        """_summary_

        Parameters
        ----------
        title : _type_
            _description_
        id : _type_
            _description_
        """
        self.title = title
        self.id = id

    def __str__(self) -> str:
        return self.title

    def __repr__(self) -> str:
        return self.id + "_" + self.title


def fix_and_fill_src_url(metadata: pd.DataFrame, data: pd.DataFrame):
    # Helpers for grabbing source URLs efficiently.
    url_map = metadata.set_index("link").to_dict()["src_url"]
    url_cache: Dict[str, str] = {}

    def to_src_url(url_str):
        if url_str in url_map.keys():
            return url_map[url_str]
        elif url_str in url_cache.keys():
            return url_cache[url_str]
        else:
            url_cache[url_str] = _grab_src_url(url_str)
            return url_cache[url_str]

    if "src_url" not in data.columns:
        # Get all source URLs
        data["src_url"] = data["link"].apply(lambda x: to_src_url(x))
    else:
        # Fill in missing source URLs
        missing_src = data["src_url"].isna()
        data.loc[missing_src, "src_url"] = data.loc[missing_src, "link"].apply(
            lambda x: to_src_url(x)
        )


def is_empty_text_body(text: str) -> bool:
    to_drop = [
        # Drop GMBinder links that are dead.
        "NoSuchKey" in text,
        # Drop Homebrwery links that are dead
        "Can not find brew" in text,
        # Some users have relocated their files to other sources and are also being pruned here.
        "This content has been moved" in text,
        # Some are not found
        "Error: File not found" in text,
        # Anything super short is probably not a real piece of content
        len(text) <= 100,
    ]

    return any(to_drop)


def preview_long_text(text: str, n: int) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    n : int
        _description_

    Returns
    -------
    str
        _description_
    """
    lines = text.split("\n")
    total_lines = len(lines)

    if total_lines >= 2 * n:
        first_n = [i for i in lines[:n]]
        last_n = [i for i in lines[-n:]]
        lines = first_n + ["....."] + last_n

    text = "\n".join(lines)

    return text


def get_soup(url: str) -> bs4.BeautifulSoup:
    """Get a BeautifulSoup object by making a request to the specified URL.

    Parameters
    ----------
    url : str
        The URL from which to fetch the data.

    Returns
    -------
    bs4.BeautifulSoup
        A BeautifulSoup object representing the parsed HTML content.
    """
    r = requests.get(url)
    soup = bs4.BeautifulSoup(r.text, "html5lib")
    return soup


def get_title_and_body(
    text_dir: Path, metadata: pd.DataFrame, url: str, clean: bool
) -> Tuple[str, str]:
    """Get the title and body of the content associated with the given URL.

    Parameters
    ----------
    text_dir : Path
        The path to the directory where the text files are stored.
    metadata : pd.DataFrame
        The DataFrame containing metadata information.
    url : str
        The URL of the content to retrieve.
    clean : bool
        Flag indicating whether the scraped text needs to be cleaned.

    Returns
    -------
    Tuple[str, str]
        A tuple containing the title and body of the content.
    """
    try:
        soup = get_soup(url)
        title = RAW + soup.title
    except Exception:
        title = RAW + "Title Not Found"

    if url in metadata["src_url"].values:
        print(ANNOUNCE + "Loading text body from local source.")
        uid = metadata[metadata["src_url"] == url]["UID"]
        uid = uid.values[0]
        print(ANNOUNCE + f"Loading UID {uid} ({url})")

        with open(text_dir / f"{uid}.txt", "r") as f:
            body = f.read().replace("\n\n", "\n")
    else:
        print(ANNOUNCE + f"Searching for data at {url}")
        df = pd.DataFrame({"link": [url]})
        df = get_source_texts(df, pass_attempts=5)
        body = df["Text"].values[0]
        if body == "":
            body = "Body Not Found"
    if clean:
        body = clean_scraped_text(body, ensure_consistence=False)

    body = re.sub(r"\n\s*\n\s*(\n\s*)+", "\n\n", body)
    body = RAW + body

    return (title, body)


def post_entry_data(
    data: pd.DataFrame,
    metadata: pd.DataFrame,
    text_dir: Path,
    url: str,
    i: int,
    num_urls: int,
    prev_length: int,
    clean: bool,
):
    """Display the entry data to the terminal for the specified URL.

    Parameters
    ----------
    data : pd.DataFrame
        The DataFrame containing data related to the content.
    metadata : pd.DataFrame
        The DataFrame containing metadata information.
    text_dir : Path
        The path to the directory where the text files are stored.
    url : str
        The URL of the content to process and display.
    i : int
        The current index of the URL being processed.
    num_urls : int
        The total number of URLs to process.
    prev_length : int
        The desired length for previewing the text body.
    clean : bool
        Flag indicating whether the scraped text needs to be cleaned.
    """
    # Get entry data to display
    pos = ANNOUNCE + f"{i}/{num_urls}: "
    # Author
    sub_author = data[data["src_url"] == url]["submission_author"].values[0]
    cmt_author = data[data["src_url"] == url]["comment_author"].values[0]
    author = ANNOUNCE + str(sub_author)
    if cmt_author != "":
        author = author + f"/{cmt_author}"
    # Title and body
    title, body = get_title_and_body(text_dir, metadata, url, clean)
    body = preview_long_text(body, n=round(prev_length / 2))

    # Write entry data to terminal
    print(f"{pos} ({author})")
    print(title)
    print(body)

    if is_empty_text_body(body):
        print("Marking flair as None")
        raise EmptyText


def inquire(
    submissions: List[SubmissionRecord],
    mode_flair: str,
) -> Optional[Tuple[str, List[SubmissionRecord]]]:
    """Ask the user questions and prompt for input.

    Parameters
    ----------
    submissions : List[SubmissionRecord]
        A list of SubmissionRecord objects representing available submissions.
    mode_flair : str
        The current flair mode.

    Returns
    -------
    Optional[Tuple[str, List[SubmissionRecord]]]
        A tuple containing the flair and the list of valid submissions selected by the user.
        Returns None if no answers are provided.
    """
    questions = [
        inquirer.Checkbox(
            "submissions",
            message="Which submission title matches this post?",
            choices=submissions,
            carousel=True,
        ),
        inquirer.List(
            "flair",
            message=f"Which flair describes this content (currently {mode_flair})?",
            choices=FLAIR,
            carousel=True,
        ),
    ]
    answers = inquirer.prompt(questions, theme=Cyans())
    if answers is None:
        return None
    else:
        return (answers["flair"], answers["submissions"])


def process_url_entry(data: pd.DataFrame, data_path: Path, url: str):
    """Process the data related to the specified URL.

    Parameters
    ----------
    data : pd.DataFrame
        The DataFrame containing data related to the content.
    data_path : Path
        The path to the CSV or pickle file containing the data.
    url : str
        The URL of the content to process.
    """
    # Get data for questions
    url_inds = data["src_url"] == url
    submission_titles = data[url_inds]["submission_title"].values.tolist()
    submission_ids = data[url_inds]["submission_id"].values.tolist()
    try:
        mode_flair = data[url_inds]["submission_flair"].value_counts().index[0]
    except IndexError:
        mode_flair = "Unknown"

    submissions = [
        SubmissionRecord(title, _id)
        for title, _id in zip(submission_titles, submission_ids)
    ]
    # Ask questions
    answers = inquire(submissions, mode_flair)

    # Update data
    if answers is None:
        processed = data["manually_reviewed"].sum()
        print(
            ANNOUNCE + f"Exiting...{processed} out of {len(data)} records processed..."
        )
        sys.exit()
    flair, valid_subs = answers
    ids = [sub.id for sub in valid_subs]

    if any(ids):
        id_inds = data["submission_id"].isin(ids)
        data.loc[url_inds & id_inds, "related_link"] = True

    data.loc[url_inds, "corrected_flair"] = flair
    data.loc[url_inds, "manually_reviewed"] = True
    save_pandas_to_path(data, data_path)


def prep_data(
    data_path: Path, metadata_path: Path
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare the data for processing, ensuring that URLs are formatted as similarly as
    possible and

    Parameters
    ----------
    data_path : Path
        The path to the CSV or pickle file containing the data.
    metadata_path : Path
        The path to the CSV or pickle file containing metadata information.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        A tuple containing the DataFrame of newly scraped links to validate and the
        DataFrame with metadata information (regarding existing reviewed/collected data).
    """
    # Get data and fix URLs
    data = pandas_from_path(data_path)
    metadata = pandas_from_path(metadata_path)

    # Make sure URLs adhere to certain standards for consistent ID of duplicates
    data["link"] = data["link"].apply(lambda x: conform_url(x))
    metadata["link"] = metadata["link"].apply(lambda x: conform_url(x))
    # Make sure "manually_reviewed", "related_link", "corrected_flair" are in columns
    ## Fill with NaN/False as appropriate/needed
    fill_missing_cols(data)
    # Try to find a src url for each link to help identify repeat links
    ## Avoid making web requests as much as possible
    fix_and_fill_src_url(metadata, data)
    # Save data now that everything has been cleaned/prepped
    save_pandas_to_path(data, data_path)

    return (data, metadata)


def review_newly_ingested_links(
    data_path: Path, metadata_path: Path, text_dir: Path, prev_length: int, clean: bool
):
    """
    Process the main submission flair for newly scraped URLs and prompts the user for
    input.

    This function processes the main submission flair for URLs that have not been
    manually reviewed yet. It prompts the user to review each URL and provides entry
    data useful for annotation such as the title and body of the linked content for
    review.

    URLs are merged as much as possible to limit redundancy and the user is also
    prompted to indicate which, if any, primary submissions the URL is directly related
    to.

    Parameters
    ----------
    data_path : Path
        The path to the CSV or pickle file containing the main data DataFrame.
    metadata_path : Path
        The path to the CSV or pickle file containing metadata information.
    text_dir : Path
        The path to the directory where the text files are stored.
    prev_length : int
        The desired length for previewing the text body during the review process.
    clean : bool
        Flag indicating whether the scraped text needs to be cleaned before displaying.
    """
    data, metadata = prep_data(data_path, metadata_path)

    # Announce how much progress as been made.
    num_processed = data["manually_reviewed"].sum()
    print(ANNOUNCE + f"{num_processed} records already processed out of {len(data)}")

    # Get the minimal number of unique URLs to review
    urls = data[~data["manually_reviewed"]]["src_url"].unique()
    num_urls = len(urls)

    # Check each URL one by one
    for i, url in enumerate(urls):
        try:
            post_entry_data(
                data=data,
                metadata=metadata,
                text_dir=text_dir,
                url=url,
                i=i,
                num_urls=num_urls,
                prev_length=prev_length,
                clean=clean,
            )
            process_url_entry(data, data_path, url)
        except EmptyText:
            data.loc[data["src_url"] == url, "corrected_flair"] = np.nan
            data.loc[data["src_url"] == url, "manually_reviewed"] = True
            save_pandas_to_path(data, data_path)
