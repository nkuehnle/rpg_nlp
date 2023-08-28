# Processing/updating data
import pandas as pd
import numpy as np

# Annotation/ system
from pathlib import Path
from typing import Set, List

# CLI/UI
import inquirer

# Custom modules
from .annotation_utils.data_io import pandas_from_path, save_pandas_to_path
from .annotation_utils.uix_utils import ANNOUNCE, RAW, Cyans


FLAIR: List[str] = [
    "Class",
    "Subclass",
    "Monster",
    "Mechanic",
    "Race",
    "Spell",
    "Item",
    "Feat",
    "Compendium",
    "Background",
]


def update_label_choices(data: pd.DataFrame, labels: Set[str]) -> Set[str]:
    annotated_data = data[data["manually_annotated"]]
    label_sets = annotated_data["annotated_labels"].to_list()
    if any(label_sets):
        _labels = [item for sublist in label_sets for item in sublist]
        unique_labels = set(_labels)
        new_labels = [lbl for lbl in unique_labels if lbl not in labels]
        for new_label in new_labels:
            labels.add(new_label)
    return labels


class SectionRecord:
    def __init__(
        self, header: str, body: str, flair: str, section_number: int, uid: int
    ):
        """_summary_

        Parameters
        ----------
        title : _type_
            _description_
        id : _type_
            _description_
        """
        self.header = header
        self.body = body
        self.flair = flair
        self.section_number = section_number
        self.uid = uid

    def __str__(self) -> str:
        return RAW + f"{self.header}\n{self.body}"

    @property
    def loc(self) -> str:
        return RAW + f"UID #{self.uid}, Sec #{self.section_number}"


def rows_to_section_records(data: pd.DataFrame) -> List[SectionRecord]:
    sections: List[SectionRecord] = []
    for _, row in data.iterrows():
        header_level = row["header_level"]
        heading = row["section_heading"]
        header = f"{'#'*header_level} {heading}"

        body = row["section_text"].lstrip(heading)
        body = body.lstrip().replace("\n\n", "\n")

        flair = row["submission_flair"]
        uid = row["UID"]
        section_num = row["section_number"]

        section = SectionRecord(
            header=header,
            body=body,
            flair=flair,
            uid=uid,
            section_number=section_num,
        )
        sections.append(section)

    return sections


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


def post_entry_data(
    section: SectionRecord,
    i: int,
    num_sections: int,
    prev_length: int,
):
    """Display the entry data to the terminal for the specified URL.

    Parameters
    ----------
    data : pd.DataFrame
        The DataFrame containing data related to the content.
    i : int
        The current index of the section being processed.
    num_sections : int
        The total number of sections to process.
    prev_length : int
        The desired length for previewing the section text
    """
    # Get entry data to display
    pos = ANNOUNCE + f"{i}/{num_sections}: {section.loc} (Sub Flair: {section.flair})"
    section_text = preview_long_text(str(section), prev_length)
    # Write entry data to terminal
    print(pos)
    print(section_text)


def check_if_more_labels_needed():
    questions = [
        inquirer.List(
            "continue",
            message="Are there additional labels to add?",
            choices=["Yes", "No"],
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions, theme=Cyans())

    if answers["continue"] == "Yes":
        return True
    elif answers["continue"] == "No":
        return False


def ask_for_new_label() -> str:
    questions = [
        inquirer.Text("new_label", message="What new label would you like to include?")
    ]
    answers = inquirer.prompt(questions, theme=Cyans())

    return answers["new_label"]


def ask_for_new_labels() -> List[str]:
    new_labels = []
    new_labels_to_add = check_if_more_labels_needed()
    while new_labels_to_add:
        new_label = ask_for_new_label()
        new_labels.append(new_label)
        new_labels_to_add = check_if_more_labels_needed()
    return new_labels


def inquire(label_options: Set[str]) -> List[str]:
    """_summary_

    Returns
    -------
    List[str]
        _description_
    """
    questions = [
        inquirer.Checkbox(
            "valid_labels",
            message="Which label(s) fit this section?",
            choices=list(label_options),
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions, theme=Cyans())
    answer = answers["valid_labels"]

    labels: List[str] = answer if answer else []

    new_labels = ask_for_new_labels()
    labels = labels + new_labels

    labels = [label for label in labels if label]

    return labels


def update_row(data: pd.DataFrame, mask: np.ndarray, labels: List[str]):
    data.loc[mask, "annotated_labels"] = data.loc[mask, "annotated_labels"].map(
        lambda _: labels
    )
    data.loc[mask, "manually_annotated"] = True

    print(data[mask]["annotated_labels"])


def process_section(
    section: SectionRecord, data: pd.DataFrame, label_options: Set[str]
):
    """Process the data related to the specified URL.

    Parameters
    ----------
    section : SectionRecord
        Storage container for infomartion about section to process
    data : pd.DataFrame
        The DataFrame containing data related to the content.
    """

    # Ask questions
    labels = inquire(label_options)
    mask = (data["UID"] == section.uid) & (
        data["section_number"] == section.section_number
    )

    update_row(data, mask, labels)


def prep_data(data_path: Path) -> pd.DataFrame:
    """
    Prepare the data for processing, ensuring that URLs are formatted as similarly as
    possible and

    Parameters
    ----------
    data_path : Path
        The path to the CSV or pickle file containing the data.

    Returns
    -------
    pd.DataFrame
        A DataFrame sections to review for label annotation
    """
    # Get data and fix URLs
    data = pandas_from_path(data_path)
    if "manually_annotated" in data.columns:
        data["manually_annotated"] = data["manually_annotated"].fillna(False)
    else:
        data["manually_annotated"] = False
    if "annotated_labels" in data.columns:
        missing = data["annotated_labels"].isna()
        num_missing = missing.sum()
    else:
        data["annotated_labels"] = [[] for _ in range(len(data))]
    save_pandas_to_path(data, data_path)

    return data


def annotate_sections(data_path: Path, prev_length: int):
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
    prev_length : int
        The desired length for previewing the text body during the review process.
    """
    data = prep_data(data_path)
    label_options: Set[str] = set(FLAIR)
    label_options = update_label_choices(data, label_options)

    # Announce how much progress as been made.
    num_processed = data["manually_annotated"].sum()
    print(ANNOUNCE + f"{num_processed} sections already processed out of {len(data)}")

    # reset = (data["UID"] == 3271) & (data["section_number"] == 34)
    # data.loc[reset, "manually_annotated"] = False

    sections = rows_to_section_records(data[~data["manually_annotated"]])
    num_sections = len(sections)

    for i, section in enumerate(sections, start=1):
        post_entry_data(
            section=section,
            i=i,
            num_sections=num_sections,
            prev_length=prev_length,
        )
        process_section(section, data, label_options)
        save_pandas_to_path(data, data_path)
        label_options = update_label_choices(data, label_options)
