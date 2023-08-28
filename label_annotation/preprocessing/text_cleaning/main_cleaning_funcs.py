# Imports primarily for typehinting
from pathlib import Path
import pandas as pd
from typing import List
from nltk.corpus.reader.markdown import CategorizedMarkdownCorpusReader
import re

# Custom modules
from .data_io import (
    read_src_txt_from_file,
    get_uids_from_path,
)
from .mappers import ENCODING_MAPPER
from .noise import HTML_TAG_PATTERN, URL_PATTERN
from .markup_style_cleaning import (
    clean_html,
    clean_formatters,
    clean_metadata,
    clean_css,
    clean_links_images,
    strip_excess_whitespace,
)
from .credit_identification_helpers import check_if_any_pats, CREDIT_PATTERNS
from .md_fixes import fix_markdown, credited_horizontal_rules_to_headers, NoHeadersError
from .consistency import make_consistent
from .nuisance_credits import fix_known_nuisance_credits


def clean_scraped_text(text: str, **kwargs) -> str:
    """
    Clean scraped text by applying various cleaning operations.

    It first fixes any mistakes of improper string encoding, i.e. cases where UTF-8
    strings contain ISO-8599 encoded UTF-8 characters (obtained from
    https://gist.github.com/xijo/d4bad3953f7b9979dd91.)

    This function performs a series of cleaning operations on the input text to remove
    noise in the form of unwanted page formatting, HTML tags, CSS, metadata, promotional
    text cleaning, unusual characters etc.


    Parameters
    ----------
    text : str
        The text to be cleaned.
    ensure_consistence : bool
        Whether or not to ensure consistent language/formating, may negatively impact
        human-readability in some cases.

    Other Parameters
    ----------------
    **kwargs
        Additional keyword arguments for controlling the cleaning process.

    Returns
    -------
    str
        The cleaned text.

    Notes
    -----
    - The CSS cleaning function raises an error when a curly bracket is
        improperly used in place of another opening/closing, e.g.
        "Text with a bad (parenthetical}")
    - Currently these are fixed via manual text inspection/correction
    """
    # Perform encoding replacement to fix improper UTF-8 encoding
    for k, v in ENCODING_MAPPER.items():
        text = text.replace(k, v)

    # Clean HTML tags as noise
    if re.search(pattern=HTML_TAG_PATTERN, string=text):
        text = clean_html(text)

    # Clean formatters as noise
    if "formatters" in kwargs:
        text = clean_formatters(text, kwargs["formatters"])
    else:
        text = clean_formatters(text)

    # Clean CSS as noise
    css_kwargs = {k: v for k, v in kwargs.items() if k in ("noisy_css", "warn_limit")}
    text = clean_css(text=text, **css_kwargs)

    # Clean metadata as noise
    if "noisy_metadata" in kwargs:
        text = clean_metadata(text, kwargs["noisy_metadata"])
    else:
        text = clean_metadata(text)

    # Fix critical markdown errors
    text = fix_markdown(text)

    # Strip excess whitespaces
    text = strip_excess_whitespace(text)

    return text


def clean_by_uid(uid: int, raw_path: Path, clean_path: Path):
    """_summary_

    Parameters
    ----------
    uid : int
        _description_
    raw_path : Path
        _description_
    clean_path : Path
        _description_
    """
    txt = read_src_txt_from_file(uid, raw_path)

    # This is necessary for handling some really unusual methods of attributing credit
    # Uses patterns in /src/prepocessing/text_cleaning/nuisance_credits.csv
    txt = fix_known_nuisance_credits(txt)

    # Basic cleaning
    txt = clean_scraped_text(txt)

    # Clean out images...
    imgs_or_links = ("](" in txt) or bool(re.search(pattern=URL_PATTERN, string=txt))
    if imgs_or_links:
        tmp_file = clean_path / f"_{uid}.tmp"
        with open(tmp_file, "w") as f:
            f.write(txt)

        # Clear out images
        reader = CategorizedMarkdownCorpusReader(str(clean_path), f"_{uid}" + r"\.tmp")
        images = [i for i in reader.images(f"_{uid}.tmp")]
        links = [i for i in reader.links(f"_{uid}.tmp")]
        txt = clean_links_images(txt, links, images)
        tmp_file.unlink()

    txt = "\n".join([line for line in txt.split("\n") if line.strip() != "Num"])
    txt = make_consistent(txt)
    txt = txt.rstrip().lstrip()

    # Check if there could be improperly marked credit sections
    if "___" in txt:
        if check_if_any_pats(CREDIT_PATTERNS, txt):
            txt = credited_horizontal_rules_to_headers(txt)

    txt = re.sub(r"__+", "", txt)

    # Write cleaned text
    with open(clean_path / f"{uid}.txt", "w") as f:
        f.write(txt)


def clean_raw_scrapes(
    df: pd.DataFrame, raw_path: Path, clean_path: Path, limit_to_df: bool = False
):
    """
    Clean raw texts by applying the `clean_scraped_text` function to each text.

    This function takes a DataFrame, a raw text file path, and a clean text file path
    as input. It compares the UIDs of raw texts and clean texts to identify the texts
    that need cleaning. It then applies the `clean_scraped_text` function to each raw
    text to perform basic cleaning operations and saves the cleaned texts to the clean
    text file path.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame used for error reporting. This DataFrame is not used for the
        cleaning process, but is used to provide information regarding errors.
    raw_path : Path
        The file path to the directory containing the raw text files.
    clean_path : Path
        The file path to the directory where the cleaned text files will be saved.
    limit_to_df : bool
        Whether to only fix texts with UIDs in the DF of interest

    Raises
    ------
    ValueError | KeyError
        If an error occurs during the cleaning process, either a ValueError or KeyError
        is raised.
        -ValueError is typically raised during the CSS cleaning process if typos which
        resemble CSS are encountered or extensive portions of unusual CSS are observed.
        -KeyError is raised for UIDs for which there is not a raw text file present.

    Notes
    -----
    - The function applies the `clean_scraped_text` function to each raw text,
      performing basic cleaning operations, and saves the cleaned text to a file in the
      clean text directory.
    - If an error occurs during the cleaning process, the function prints an error
      message, including the UID and, if available, the associated URL from the
      DataFrame `df`. The specific error encountered is also printed.
    - If multiple errors occur, only the first encountered error is raised at the end of
      the cleaning process, though all are printed to the console.

    """
    raw_uids = get_uids_from_path(raw_path)
    print(f"{len(raw_uids)} raw texts found")
    clean_uids = get_uids_from_path(clean_path)
    print(f"{len(clean_uids)} clean texts found")

    uids_to_clean = [i for i in raw_uids if i not in clean_uids]
    uids_to_clean.sort()
    if limit_to_df:
        print("Limiting cleaning only to files in the provided dataframe")
        uids_to_clean = [uid for uid in uids_to_clean if uid in df["UID"].values]
    n_uids = len(uids_to_clean)

    if any(uids_to_clean):
        ur = 6
        lr = 4
        lb_min, lb_sec = divmod(n_uids / ur, 60)
        lb = f"{int(lb_min)} min {int(lb_sec)} sec"
        ub_min, ub_sec = divmod(n_uids / lr, 60)
        ub = f"{int(ub_min)} min {int(ub_sec)} sec"

        print(f"Cleaning {n_uids} texts, starting with UID {uids_to_clean[0]}.")
        print(f"Note processes ~{lr}-{ur} texts/sec.\nETA: {lb} to {ub}")

        errs: List[ValueError | KeyError | NoHeadersError] = []
        for uid in uids_to_clean:
            try:
                clean_by_uid(uid, raw_path, clean_path)
            except (ValueError, KeyError, NoHeadersError) as e:
                try:
                    url = f" ({df[df['UID'] == uid]['link'].values[0]})"
                except Exception:
                    url = ""
                print(f"Error: UID {uid}{url}")
                print(e)
                errs.append(e)

        if len(errs) > 0:
            raise errs[0]
    else:
        print("All texts have already been cleaned and filtered.")
