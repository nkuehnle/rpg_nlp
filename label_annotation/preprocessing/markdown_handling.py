from pathlib import Path
import shutil
from nltk.corpus.reader.markdown import CategorizedMarkdownCorpusReader, MarkdownSection
from typing import List, Sequence, Dict
import pandas as pd
from collections import defaultdict, namedtuple
from .text_cleaning.credit_identification_helpers import check_if_credit

Image = namedtuple("Image", "label src title")
Link = namedtuple("Link", "label href title")


def validate_data(
    df: pd.DataFrame, required_columns: List[str], inplace: bool = False
) -> pd.DataFrame:
    """
    Validate the input DataFrame to ensure the required columns exist.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to be validated.
    required_columns : List[str]
        List of column names required in the DataFrame.
    inplace : bool, optional
        If True, modify the input DataFrame in place; if False, return a new DataFrame.
        Default is True.

    Returns
    -------
    pd.DataFrame
        Validated DataFrame with the required columns.

    Raises
    ------
    ValueError
        If any of the required columns are missing.
    """
    missing_columns = set(required_columns) - set(df.columns)

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    return df if inplace else df.copy()


def sections_df_to_docs(df: pd.DataFrame, inplace: bool = False) -> pd.DataFrame:
    """
    Convert a DataFrame of sections to a DataFrame of documents.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing section information with columns: 'UID', 'section_number',
        'section_text', 'is_credit'.
    inplace : bool, optional
        If True, modify the input DataFrame in place; if False, return a new DataFrame.
        Default is True.

    Returns
    -------
    pd.DataFrame or None
        If inplace=False, returns a new DataFrame containing document information with
        columns: 'UID', 'text', 'credit_text', 'num_setions', 'num_credit_sections'

    Notes
    -----
    - The resulting DataFrame will have fixed columns:
        - 'clean_text': The merged main text for each document
        - 'credit_text': The merged credit text for each document
        - 'num_sections': The number of sections in each document
        - 'num_credit_sections': The number of credit sections in each document.
    - The resulting dataframe will have optional columns:
        - Columns that contain the sub-phrase 'tokens', it will expect a sequence of
          tokens for each section to be in the column
          Non-credit lists will be merged into a single new list with the same name
        - Columns that have a single value for each UID will also be passed

    Examples
    --------
    >>> df = pd.DataFrame({
            'UID': [1, 1, 2, 2, 3, 3],
            'section_number': [1, 2, 1, 2, 1, 2],
            'section_text': ['Intro', 'Credit', 'Intro', 'Credit', 'Intro', 'Credit'],
            'word_tokens': [['Intro'], ['Credit'], ['Intro'], ['Credit'], ['Intro'], ['Credit']],
            'is_credit': [False, True, False, True, False, True],
            'other_column': ['A', 'A', 'B', 'B', 'C', 'C']
        })
    >>> result = sections_df_to_docs(df)
    >>> print(result)
        UID clean_text credit_text num_sections num_credit_sections other_column clean_word_tokens  credit_word_tokens
    0    1     Intro     Credit         2                1                A        ['Intro']             ['Credit']
    1    2     Intro     Credit         2                1                B        ['Intro']             ['Credit']
    2    3     Intro     Credit         2                1                C        ['Intro']             ['Credit']
    """
    df = validate_data(
        df,
        required_columns=["UID", "section_number", "section_text", "is_credit"],
        inplace=inplace,
    )

    df = df.sort_values(["UID", "section_number"])
    uids: Sequence[int] = df["UID"].unique()

    # Figure out what columns to process
    # Standard cols
    section_cols = [
        "UID",
        "is_credit",
        "section_text",
        "section_number",
        "header_level",
    ]
    token_cols = [c for c in df.columns if "tokens" in c]
    standard_cols = token_cols + section_cols
    # Other cols
    _other_cols = [c for c in df.columns if c not in standard_cols]
    other_cols = []
    for c in _other_cols:
        unique_combos = df[~df.duplicated(["UID", c], keep="first")]
        if len(unique_combos) == len(uids):
            other_cols.append(c)

    # Set values for each UID
    values: Dict[str, List[int | str]] = defaultdict(list)
    for uid in uids:
        section_df = df[df["UID"] == uid]
        is_credit = section_df["is_credit"]
        main_text = "\n\n".join(section_df[~is_credit]["section_text"])
        credit_text = "\n\n".join(section_df[is_credit]["section_text"])

        values["UID"].append(uid)
        values["clean_text"].append(main_text)
        values["num_sections"].append(len(section_df))
        values["credit_text"].append(credit_text)
        values["num_credit_sections"].append(is_credit.sum())

        for col in token_cols:
            clean_tokens = section_df.loc[~is_credit, col].explode().to_list()
            credit_tokens = section_df.loc[is_credit, col].explode().to_list()
            values[f"clean_{col}"].append(clean_tokens)
            values[f"credit_{col}"].append(credit_tokens)

        for col in other_cols:
            values[col].append(section_df[col].values[0])

    # Return DF
    _df = pd.DataFrame(values)
    for col in other_cols:
        _df[col] = _df[col].astype(df[col].dtype)

    if inplace:
        df = _df
    else:
        return _df


def _get_section_df(
    reader: CategorizedMarkdownCorpusReader, uids: Sequence[int]
) -> pd.DataFrame:
    """
    Convert a CategorizedMarkdownCorpusReader object to a DataFrame of section
    information.

    Parameters
    ----------
    reader : CategorizedMarkdownCorpusReader
        A CategorizedMarkdownCorpusReader object for reading markdown files.
    uids : Sequence[int]
        A sequence of unique IDs representing the documents to process.

    Returns
    -------
    pd.DataFrame
        DataFrame containing section information with columns: 'UID', 'header_level',
        'section_number', 'section_text', 'is_credit'. Optionally: any columns
        containing the phrase "tokens" are merged into one.
    """
    values: Dict[str, List[int | str]] = defaultdict(list)

    for uid in uids:
        sections: List[MarkdownSection] = reader.sections(f"{uid}.txt")
        for i, section in enumerate(sections):
            values["UID"].append(uid)
            values["header_level"].append(section.level)
            values["section_number"].append(i)
            values["section_heading"].append(section.heading)
            values["section_text"].append(section.content)
            values["is_credit"].append(check_if_credit(section))

    df = pd.DataFrame(values)
    df["section_number"] = df["section_number"].astype("Int16")
    df["header_level"] = df["header_level"].astype("Int8")
    df["is_credit"] = df["is_credit"].astype("boolean")

    df = df[df["section_text"] != ""]

    return df


def get_section_df(
    df: pd.DataFrame, text_path: Path, inplace: bool = False
) -> pd.DataFrame:
    """
    Convert a DataFrame of documents to a DataFrame of section information.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing document information with at least one column 'UID'.
        Expects columns: 'UID'.
    text_path : Path
        Path to the directory containing the markdown files.
    inplace : bool, optional
        If True, modify the input DataFrame in place; if False, return a new DataFrame.
        Default is True.

    Returns
    -------
    pd.DataFrame
        DataFrame containing section information with columns: 'UID', 'header_level',
        'section_number', 'section_text', 'is_credit'.
    """
    df = validate_data(
        df,
        required_columns=["UID"],
        inplace=inplace,
    )

    # Make temp directory for reader
    print("\tPreparing markdown corpus reader")
    corpus_path = text_path / "Corpus_Files"
    corpus_path.mkdir(exist_ok=True)
    for uid in df["UID"].values:
        target = text_path / f"{uid}.txt"
        destination = corpus_path / f"{uid}.txt"
        shutil.copy(target, destination)
    reader = CategorizedMarkdownCorpusReader(str(corpus_path), r"[0-9]+\.txt")

    # Get actual section data
    print("\tParsing sections")
    _df = _get_section_df(reader=reader, uids=df["UID"])

    # Clean up
    del reader
    shutil.rmtree(corpus_path)

    # Merge with original data
    df = pd.merge(df, _df, how="outer", on="UID")

    return df if not inplace else None
