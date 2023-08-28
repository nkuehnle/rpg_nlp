from typing import List
import re
from nltk.corpus.reader.markdown import MarkdownSection
from collections import namedtuple

FauxSection = namedtuple("FauxSection", "content, heading")


def check_if_credit(
    section: MarkdownSection | FauxSection, max_pct_promos: float = 0.4
) -> bool:
    """
    Check if a MarkdownSection object represents a credit section.

    Parameters
    ----------
    section : MarkdownSection | FauxSection
        A MarkdownSection object containing the heading, content, and level of a
        section.
    max_pct_promos : float
        _description_

    Returns
    -------
    bool
        True if the section represents a credit section, False otherwise.
    """
    heading = section.heading
    content = section.content.lstrip(section.heading)
    original_content = content

    if len(section.heading) > 0:
        heading = clean_promos(heading, header=True)
        pct_head_filtered = 1 - (len(heading) / len(section.heading))
    else:
        pct_head_filtered = 0

    if pct_head_filtered < max_pct_promos:
        # Check content only if heading is not credit
        if len(original_content) > 0:
            content = clean_promos(content, header=False, max_pct_promos=max_pct_promos)
            pct_cont_filtered = 1 - (len(content) / len(original_content))
        else:
            pct_cont_filtered = 0

        if pct_cont_filtered < max_pct_promos:
            # If neither is credit, return false
            return False
        else:
            return True
    else:
        return True


HARD_DROP_PATTERNS = [
    r"((©)|(copyright))( [A-Z]*)?",
    r"homebrewery",
    r"[\w]*\.?pdf[\w]*",
    r"wizards of the coast",
    r"wotc",
    r"paizo",
    r"llc",
    r"tsr",
    r"inc\.?",
    r"glossary",
    r"design notes",
    r"change ?log",
    r"patreon",
    r"gm ?binder",
    r"[^ a-z]\/?(u|r)\/\w+",
    r"Supported By",
    r"The Part Where I Shill My Patreon",
    r"Special thanks to[\w ]*Patrons",
    r"Created by Nicholas H\.",
    r"WWW\.GMBINDER\.COM This document was lovingly created using GM Binder\.",
    r"(License\n)?OPEN GAME License",
]
HARD_DROP_PATTERNS = [r"(?<![A-Z])" + p + r"(?![A-Z])" for p in HARD_DROP_PATTERNS]
SOFT_DROP_PATTERNS = [
    r"credits?",
    r"acknowledgements?" r"legal (information)?",
    r"changes? ?(log)?",
    r"homebrew(ery?)?s?",
    r"((?<!martial )art((work)|(ist)|(station))?)",
    r"(special )?thank((s)|(you))( to)?",
    r"(table of )?contents?",
    r"glossary",
    r"notes",
    r"support((ed)|(ers))",
    r"by",
    r"version",
    r"Supported By",
]
SOFT_DROP_PATTERNS = [r"(?<![A-Z])" + p + r"(?![A-Z])" for p in SOFT_DROP_PATTERNS]

SPLITTER_PATTERNS = [
    r"Supported By",
    r"The Part Where I Shill My Patreon",
    r"Special thanks to[\w ]*Patrons",
    r"Created by Nicholas H\.",
    r"WWW\.GMBINDER\.COM This document was lovingly created using GM Binder\.",
    r"(License\n)?OPEN GAME License",
]
SPLITTER_PATTERNS = [r"(?<![A-Z])" + p + r"(?![A-Z])" for p in SPLITTER_PATTERNS]

CREDIT_PATTERNS = SOFT_DROP_PATTERNS + HARD_DROP_PATTERNS + SPLITTER_PATTERNS


def pat_in_text(pat: str, text: str) -> bool:
    """_summary_

    Parameters
    ----------
    pat : str
        _description_
    text : str
        _description_

    Returns
    -------
    bool
        _description_
    """
    return bool(re.search(pattern=pat, string=text, flags=re.IGNORECASE))


def check_if_any_pats(pats: List[str], text: str) -> bool:
    """_summary_

    Parameters
    ----------
    pats : List[str]
        _description_
    text : str
        _description_

    Returns
    -------
    bool
        _description_
    """
    # any([...]) would be neater, but this minimizes loop length
    for pat in pats:
        if pat_in_text(pat, text):
            return True

    return False


def strip_header_promos(text: str) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """
    if check_if_any_pats(HARD_DROP_PATTERNS, text):
        return ""
    else:
        for pat in SOFT_DROP_PATTERNS:
            text = re.sub(pattern=pat, repl="", string=text, flags=re.IGNORECASE)
        return text


def strip_body_promos(text: str, max_pct_promos: float = 0.4) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    max_pct_promos : float, optional
        _description_, by default 0.4

    Returns
    -------
    str
        _description_
    """
    if check_if_any_pats(HARD_DROP_PATTERNS, text):
        lines = text.split("\n")

        for phrase in HARD_DROP_PATTERNS:
            text = re.sub(pattern=phrase, repl="", string=text, flags=re.IGNORECASE)

        clean_lines = []
        for edited, original in zip(text.split("\n"), lines):
            if original != edited:
                pass
            else:
                clean_lines.append(original)

        text = "\n".join(clean_lines)
    if check_if_any_pats(SOFT_DROP_PATTERNS, text):
        lines = text.split("\n")
        for phrase in SOFT_DROP_PATTERNS:
            text = re.sub(pattern=phrase, repl="", string=text, flags=re.IGNORECASE)

        clean_lines = []
        for edited, original in zip(text.split("\n"), lines):
            if original:
                pct_promo = 1 - (len(edited) / len(original))
                if pct_promo >= max_pct_promos:
                    pass
                else:
                    clean_lines.append(edited)
            else:
                clean_lines.append(original)
        text = "\n".join(clean_lines)

    return text


def clean_promos(text: str, header: bool, max_pct_promos: float = 0.4) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_

    Returns
    -------
    str
        _description_
    """
    for pat in SPLITTER_PATTERNS:
        text = re.split(pat, text)[0]

    if header:
        text = strip_header_promos(text)
    else:
        text = strip_body_promos(text, max_pct_promos=max_pct_promos)

    return text
