import re
from .credit_identification_helpers import (
    check_if_credit,
    FauxSection,
)


class NoHeadersError(Exception):
    pass


def remove_empty_headers(text: str) -> str:
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
    # Remove any lines that are "header" without content
    clean_lines = []

    for line in text.split("\n"):
        if "#" in line:
            stripped = line.replace("#", "")
            empty_heading = (stripped == "") or stripped.isspace()
            if not empty_heading:
                clean_lines.append(line)
        else:
            clean_lines.append(line)

    text = "\n".join(clean_lines)

    return text


def fix_mispaced_headers(text: str) -> str:
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

    def _fix_mispaced_headers(match: re.Match) -> str:
        match_str: str = match.group(0)
        return match_str[0:-1] + " " + match_str[-1]

    pattern = r"^\s*#+[^\s#]"
    clean_lines = []

    for line in text.split("\n"):
        line = re.sub(pattern=pattern, repl=_fix_mispaced_headers, string=line)
        clean_lines.append(line)

    text = "\n".join(clean_lines)

    return text


def get_max_header_level(text: str) -> int:
    headers = re.findall(pattern=r"\n#+ ", string=text)
    try:
        max_header_level = min([len(header) - 2 for header in headers])
    except (TypeError, ValueError) as _:
        raise NoHeadersError()
    return max_header_level


def fix_missing_credit_headers(section: str, text: str, level: int) -> str:
    """_summary_

    Parameters
    ----------
    section : str
        _description_
    text : str
        _description_
    level : int
        _description_

    Returns
    -------
    str
        _description_
    """
    splits = re.split(pattern=r"___+", string=section)
    first_line = splits[0].split("\n")[0]
    main_faux_section = FauxSection(splits[0], first_line)

    if check_if_credit(main_faux_section):
        return text

    for txt in splits[1:]:
        _txt = txt.lstrip()
        heading = _txt.split("\n")[0]
        body = _txt.strip(heading).lstrip().rstrip()
        faux_section = FauxSection(txt, heading)

        if check_if_credit(faux_section):
            # Fix main text
            text = re.sub(pattern=f"___+{re.escape(txt)}", repl="", string=text)
            text = text.rstrip()
            # Add credit to end of text
            header = "#" * level
            heading = heading.strip("*").lstrip(">- ")
            text = text + f"\n\n{header} {heading}\n{body}"

    return text


def credited_horizontal_rules_to_headers(text: str) -> str:
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
    text = "\n" + text
    # Max level with content
    level = get_max_header_level(text)
    sections = re.split(pattern=r"\n#+\s*", string=text)
    sections = [section for section in sections if "___" in section]
    for section in sections:
        text = fix_missing_credit_headers(section, text, level)
    text = text.lstrip()
    return text


def clean_leading_and_laging(text: str) -> str:
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
    clean_lines = []
    for line in text.split("\n"):
        line = line.lstrip().rstrip()
        line = line.lstrip(">- ")
        line = line.lstrip()
        line = line.lstrip(">- ")
        clean_lines.append(line)
    text = "\n".join(clean_lines)
    return text


def fix_markdown(text: str) -> str:
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
    # Remove any leading >/- characters
    text = clean_leading_and_laging(text)
    # Fix mispaced headers, i.e hashes that start a line where a space is missing afterwards (prevents recognition by NLTK)
    text = fix_mispaced_headers(text)
    # Remove any empty headers (just add noise)
    text = remove_empty_headers(text)

    return text
