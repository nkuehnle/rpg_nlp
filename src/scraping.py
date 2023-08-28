# 3rd party/standard library imports
import requests
from bs4 import BeautifulSoup
import time
from requests.exceptions import RequestException, MissingSchema
from markdownify import markdownify as md

# Needed only for type-hinting
from typing import List, Dict, Tuple
import numpy as np
import re
import pandas as pd

# Custom modules
from .preprocessing.text_cleaning.markup_style_cleaning import strip_tags
from .preprocessing.text_cleaning.noise import NOISY_HTML


def _grab_src_url(url: str) -> str:
    """
    This method attempts to find the source/markdown for an entry. If it
    can't find a link to the page, it will return the original URL.

    Parameters
    ----------
    url : str
        A URL, either to the GMBinder or Homebrewery sites. Typically this
        will be a rendered view rather than a source page.

    Returns
    -------
    str
        A URL, either to the GMBinder or Homebrewery sites. Ideally this
        should be the page containing the source code.
    """

    if "gmbinder.com" in url:
        _r = requests.get(url)
        soup = BeautifulSoup(_r.text, "html5lib")
        src_btn = soup.find("a", {"class": "btn btn-default", "title": "View Source"})

        if src_btn is not None:
            return src_btn["href"]
        else:
            return url

    elif "homebrewery.naturalcrit.com" in url:
        if "share" in url:
            return url.replace("share", "source")
        elif "source" in url:
            return url
        else:
            _r = requests.get(url)
            soup = BeautifulSoup(_r.text, "html5lib")
            src_btn = soup.find("a", {"class": "navItem teal", "icon": "fas fa-code"})

            if src_btn is not None:  # Seems outdated as of July 2021
                return "https://homebrewery.naturalcrit.com" + src_btn["href"]
            else:
                return ""

    else:
        return ""


def _collect_text(url: str, noisy_tags: List[str] = NOISY_HTML) -> str:
    """
    Collects text associated with a GMBinder or Homebrewery link.
    This method generally assumes the link will be directly to the markdown.
    Thus it will attempt to find the textarea tag for GMBinder links before
    returning the text form of the resulting soup.

    NOISY_HTML are head, img, script, campaign-manager-header,
    campaign-manager-footer, and style.

    Parameters
    ----------
    url : str
        A URL, either to the GMBinder or Homebrewery sites. Ideally this is
        should be the page containing the source code.
    noisy_tags : List[str]
        A list containing different HTML tags to remove in the form of strings,
        by default, NOISY_HTML ['head', 'img', 'script',
        'campaign-manager-header', 'campaign-manager-footer', 'style']

    Returns
    -------
    str
        The text associated with the resulting link.
    """
    try:
        _r = requests.get(url)
    except MissingSchema:
        return ""

    encoding = _r.apparent_encoding
    soup = BeautifulSoup(_r.content, "html5lib", from_encoding=encoding)

    for tag in noisy_tags:
        strip_tags(soup, tag)

    if "gmbinder.com" in url:
        txt_area = soup.find("textarea")
        if txt_area is not None:
            return txt_area.text
        else:
            strip_tags(soup, "style")
            strip_tags(soup, "script")
            html = str(soup)
            md_txt = md(html, heading_style="")
            return md_txt
    elif "homebrewery.naturalcrit.com" in url:
        return soup.text
    else:
        return ""


def _get_source_text(url: str, noisy_tags: List[str] = NOISY_HTML) -> Tuple[str, str]:
    """Attempty(lambdas to retrieve raw source text from GMBinder/Homebrewery

    Three primary steps:
    1. Attempts to find a link to the most basic/raw form of text possible (if
    unsuccesful, it returns the original URL)
    2. Retrieves the plain text (stripped of as much HTML as possible) for that
    entry
    3. Does a final pass to remove any HTML, which occasionally contaminates
    the text due to markdown formating/usage of CSS by authors.

    Parameters
    ----------
    url : str
        A URL, either to the GMBinder or Homebrewery sites. Typically this
        will be a rendered view rather than a source page.
    noisy_tags : List[str]
        A list containing different HTML tags to remove in the form of strings,
        by default, NOISY_HTML ['head', 'img', 'script',
        'campaign-manager-header', 'campaign-manager-footer', 'style']

    Tuople[str, str]
        [description]
    """
    src_url = _grab_src_url(url)
    src_text = _collect_text(src_url, noisy_tags=noisy_tags)

    # Remove excess single spaces and compress linebreaks of 3+ to 2.
    src_text = src_text.lstrip()
    src_text = src_text.rstrip()
    src_text = re.sub(" +", " ", src_text)
    src_text = re.sub(r"([\r\n]{4,})+", r"\r\n\r\n", src_text)

    return (src_url, src_text)


def _try_to_get_src(
    results: Dict[str, Tuple[str, str]],
    url: str,
    noisy_tags: List[str] = NOISY_HTML,
):
    """_summary_

    Parameters
    ----------
    results : Dict[str, str]
        _description_
    url : str
        _description_
    noisy_tags : List[str], optional
        _description_, by default NOISY_HTML
    """
    try:
        results[url] = _get_source_text(url, noisy_tags=noisy_tags)
    except RequestException:
        results[url] = ("", "")


def get_source_texts(
    df: pd.DataFrame,
    noisy_tags: List[str] = NOISY_HTML,
    rate_limit: float = 0.05,
    pass_attempts: int = 1,
    verbose: bool = False,
) -> pd.DataFrame:
    """[summary]

    Parameters
    ----------
    df : pd.DataFrame
        A dataframe containing a column 'link' of URLs as strings
    noisy_tags : List[str]
        A list containing different HTML tags to remove in the form of strings,
        by default, NOISY_HTML ['head', 'img', 'script',
        'campaign-manager-header', 'campaign-manager-footer', 'style']
    rate_limit : float, optional
        Length of seconds to wait between requests, by default .05
    pass_attempts : int, optional
        [description], by default 1

    Returns
    -------
    pd.DataFrame
        A copy of the original dataframe containing new columns 'src_url' and
        'Text'
    """
    results: Dict[str, Tuple[str, str]] = {}

    url_array = df["link"].to_numpy()

    eta = len(url_array) * rate_limit
    if verbose:
        print(
            f"Procesing submissions... eta approx: {eta:.2f} to {eta*pass_attempts:.2f} seconds."
        )

    for url in url_array:
        _try_to_get_src(results, url, noisy_tags=noisy_tags)
        time.sleep(rate_limit)

    if any([i for i in results.values() if i is None or i == ""]):
        for _ in range(pass_attempts - 1):
            for url, result in results.items():
                if (result is None) or (result == ""):
                    _try_to_get_src(results, url, noisy_tags=noisy_tags)
                    time.sleep(rate_limit)
        for url, result in results.items():
            if result is None:
                results[url] = ""

    src_urls = np.empty(url_array.shape, dtype=object)
    texts = np.empty(url_array.shape, dtype=object)
    for ind, url in enumerate(url_array):
        result = results[url]
        try:
            src_urls[ind] = result[0]
            texts[ind] = result[1]
        except TypeError:
            src_urls[ind] = result
            texts[ind] = result

    submissions = (src_urls, texts)

    new_df = df.copy()
    new_df["src_url"] = submissions[0]
    new_df["Text"] = submissions[1]

    return new_df
