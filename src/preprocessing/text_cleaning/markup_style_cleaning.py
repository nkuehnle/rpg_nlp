from bs4 import BeautifulSoup, Tag
from typing import List, Tuple, Callable
import re
from collections import namedtuple

# Custom modules
from .noise import FORMATTERS, NOISY_CSS, NOISY_METADATA, URL_PATTERN, HTML_TAG_PATTERN
from .css_cleaning import clean_standard_css, clean_wrapper_css


def strip_excess_whitespace(text: str) -> str:
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
    text = text.rstrip().lstrip()
    text = re.sub(pattern=r"\n\s*\n\s*\n\s*\n", repl="\n\n\n", string=text)
    text = re.sub(pattern=r"\n\s*\n", repl="\n\n", string=text)
    text = re.sub(pattern=r"  ", repl=" ", string=text)
    return text


def strip_tags(soup: BeautifulSoup, tag: Tag) -> BeautifulSoup:
    """
    Removes all instances of the specified tag from a soup object.
    This function is called by collect_text() to iterate over a list of tags.
    Note: That it removes all child tags contained within the provided tag.

    Parameters
    ----------
    soup : BeautifulSoup
        The bs4 BeautifulSoup object to modify.
    tag : str
        The tag to search for and remove.

    Returns
    -------
    None
        Nothing. Instead, the original soup object will be modified.
    """

    while True:
        if soup.find(tag) is None:
            break
        else:
            soup.find(tag).decompose()

    return None


def clean_html(text: str) -> str:
    """
    Remove anything resembling an HTML tag (doesn't hanlde comments)

    Parameters
    ----------
    txt : str
        A string that contains HTML tags.

    Returns
    -------
    str
        A string, without any HTML tags.
    """
    soup = BeautifulSoup(text, "html5lib")
    # Does a good job of getting most tags that don't have content
    text = soup.text
    # Gets weird stuff that lingers for some reason
    text = re.sub(pattern=HTML_TAG_PATTERN, repl="", string=text)

    return text


def clean_css(
    text: str, noisy_css: List[re.Pattern] = NOISY_CSS, warn_limit: int = 7
) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    noisy_css : List[re.Pattern], optional
        _description_, by default NOISY_CSS
    warn_limit : int, optional
        _description_, by default 7

    Returns
    -------
    str
        _description_
    """
    lines = text.split("\n")
    single_line_block = re.compile(r"^{{.*}}")
    lines = [line for line in lines if not single_line_block.findall(line)]
    lines = clean_wrapper_css(lines=lines, noisy_css=noisy_css)
    lines = clean_standard_css(lines=lines, noisy_css=noisy_css, warn_limit=warn_limit)

    lines = [line for line in lines if line != "}"]
    lines = [line for line in lines if line != "{"]

    text = "\n".join(lines)

    return text


def clean_formatters(
    text: str,
    page_formatters: List[str] = FORMATTERS,
) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    page_formatters : List[str], optional
        _description_, by default FORMATTERS

    Returns
    -------
    str
        _description_
    """
    clean_lines = []

    for line in text.split("\n"):
        for f in page_formatters:
            line = line.replace(f, "")

        clean_lines.append(line)

    return "\n".join(clean_lines)


def clean_homebrewery_metadata(text: str) -> str:
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
    pattern = r"by \w+\n*\s*\[?Search GM Binder(\]\(\/search \"Search GM Binder\"\))?\s*\n*\s*Print \/ Generate PDF\s*\n*\s*\[?Visit User Profile(\]\(\/profile\/\w*\))?\s*\n*\s*[^\n#]*"

    text = re.sub(pattern=pattern, repl="", string=text, flags=re.IGNORECASE)
    return text


def clean_gmbinder_metadata(
    text: str, noisy_metadata: List[str] = NOISY_METADATA
) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    noisy_metadata : List[str], optional
        _description_, by default NOISY_METADATA

    Returns
    -------
    str
        _description_
    """
    lines = text.split("\n")
    blocks = []
    block_quotes = 0
    curr_pair = []

    for i, line in enumerate(lines):
        if "```" in line:
            block_quotes += 1
            curr_pair.append(i)
            if (block_quotes % 2) == 0:
                blocks.append(curr_pair)
                curr_pair = []

    blocks_to_exclude = []
    for b in blocks:
        block_str = "\n".join(lines[b[0] : b[1] + 1])
        block_content = block_str.replace("`", "")
        block_content = re.sub(
            pattern=r"```[a-zA-Z]*", repl=r"```", string=block_content
        )

        not_empty = not block_content.isspace()
        has_metadata = any([md in block_str for md in noisy_metadata])

        if not_empty or has_metadata:
            blocks_to_exclude.append(block_str)

    for b_str in blocks_to_exclude:
        text = text.replace(b_str, "")

    text = re.sub(pattern=r"```", repl=r"", string=text)

    return text


def clean_metadata(text: str, noisy_metadata: List[str] = NOISY_METADATA) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    noisy_metadata : List[str], optional
        _description_, by default NOISY_METADATA

    Returns
    -------
    str
        _description_
    """
    text = clean_gmbinder_metadata(text, noisy_metadata)
    text = clean_homebrewery_metadata(text)

    return text


Image = namedtuple("Image", "label src title")
Link = namedtuple("Link", "label href title")


QUOTE1 = r"(" + re.escape('"') + r")"
QUOTE2 = r"(" + re.escape("'") + r")"
QUOTE = f"({QUOTE1}|{QUOTE2})"


def link_repl(match: re.Match) -> str:
    match_str: str = match.group(0)
    match_str = match_str.split("](")[0]
    match_str = match_str.lstrip("[")
    return match_str


def link_pattern_repl(link: Link) -> Tuple[str, str | Callable]:
    """_summary_

    Parameters
    ----------
    link : Link
        _description_

    Returns
    -------
    Tuple[str, str]
        _description_
    """
    label = re.escape(link.label)
    # ( ?\*.*\* ?)? captures text between asterisks that are lost by NLTK
    label = r"( ?\*.*\* ?)?" + label + r"( ?\*.*\* ?)?"
    href = re.escape(link.href)
    if link.title:
        title = re.escape(link.title)
        pattern = f"\[{label}\]\({href}\s*{QUOTE}{title}{QUOTE}\)"
    else:
        pattern = f"\[{label}\]\({href}\)"

    repl = link_repl

    return (pattern, repl)


def image_pattern_repl(image: Image) -> Tuple[str, str]:
    """_summary_

    Parameters
    ----------
    image : Image
        _description_

    Returns
    -------
    Tuple[str, str]
        _description_
    """
    label = re.escape(image.label)
    # ( ?\*.*\* ?)? captures text between asterisks that are lost by NLTK
    label = r"( ?\*.*\* ?)?" + label + r"( ?\*.*\* ?)?"
    src = re.escape(image.src)
    if image.title:
        title = re.escape(image.title)
        pattern = f"!\[{label}\]\({src}\s*{QUOTE}{title}{QUOTE}\)"
    else:
        pattern = f"!\[{label}\]\({src}\)"
    repl = ""
    return (pattern, repl)


def clean_links_images(text: str, links: List[Link], images: List[Image]) -> str:
    """_summary_

    Parameters
    ----------
    text : str
        _description_
    links : List[Link]
        _description_
    images : List[Image]
        _description_

    Returns
    -------
    str
        _description_
    """

    lines = text.split("\n")

    for img in images:
        img_pat, img_repl = image_pattern_repl(img)
        text = re.sub(pattern=img_pat, repl=img_repl, string=text)

    for link in links:
        link_pat, link_repl = link_pattern_repl(link)
        text = re.sub(pattern=link_pat, repl=link_repl, string=text)

    text = re.sub(pattern=URL_PATTERN, repl="", string=text, flags=re.IGNORECASE)

    clean_lines = []
    for edited, original in zip(text.split("\n"), lines):
        if original:
            pct_link = 1 - (len(edited) / len(original))
            if (pct_link >= 0.4) and ("#" not in original):
                pass
            else:
                clean_lines.append(edited)
        else:
            clean_lines.append(edited)

    text = "\n".join(clean_lines)

    return text
