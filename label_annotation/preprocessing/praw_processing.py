# Utility Imports
from datetime import datetime
from typing import Tuple, Optional, List, Dict

# Imports for data processing/handling
import numpy as np
import pandas as pd
from urllib.parse import urlparse


def fix_dt(utc: str | int | datetime) -> Optional[datetime]:
    """
    Properly converts UTC datetime string to datetime object for Pandas.

    Parameters
    ----------
    utr : str | int } datetime
        A UTC datetime in string, int, or datetime format.

    Returns
    -------
    Optional[datetime]
        A properly instantiated datetime object or "none" if not numerical
    """
    try:
        if isinstance(utc, datetime):
            return utc
        else:
            utc = str(utc)
            if utc.isalnum():
                return datetime.utcfromtimestamp(int(utc))
            elif "-" in utc:
                return datetime.strptime(utc, "%Y-%m-%d %H:%M:%S")
            elif "/" in utc:
                return datetime.strptime(utc, "%m/%d/%Y %H:%M")
            else:
                raise Exception(utc)
    except ValueError:
        return None


def conform_url(url: str) -> str:
    """
    Takes in a URL string with any formatting and gives it a predictable
    schema and general domain/path formatting.

    i.e. http://reddit.com/r/all and https://www.reddit.com/r/all/
    would both be converted to https://reddit.com/r/all

    Parameters
    ----------
    url : str
        Variably formatted URL as string

    Returns
    -------
    str
        URL with fixed formatting of type https://<domain><path> without any
        trailing "/" characters
    """
    parse_result = urlparse(url)
    if parse_result.scheme == "":
        url = "https://"
    parse_result = urlparse(url)
    domain = parse_result.netloc.replace("www.", "")  # Remove "www."
    path = parse_result.path.rstrip("/")  # Remove trailing /
    path = "".join([c for c in path if (c in "_-/") or c.isalnum()])
    url = f"https://{domain}{path}"
    url = "".join([i for i in url if i != "\\"])
    url = url.split("?")[0]

    return url


def filter_simple_cmt_issues(cmts: pd.DataFrame, subs: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out obvious redundant links (comments where there is a primary
    submission) or where a link is included multiple times in a comment.

    Parameters
    ----------
    cmts : pd.DataFrame
        DataFrame of links found in comments
    subs : pd.DataFrame
        DataFrame of links found in primary submissions

    Returns
    -------
    pd.DataFrame
        DataFrame of links that have been removed.
    """

    # First make sure we don't have any rows with a common link and post ID
    simple_dups = cmts.duplicated(subset=["submission_id", "link"])
    discards1 = cmts[simple_dups].copy()
    cmts.drop_duplicates(subset=["submission_id", "link"], inplace=True)

    log_str = f"Removed {len(discards1)} duplicated linkes from comments with the same"
    log_str = log_str + " fromparent submission ID and link"
    print(log_str)

    # Get list of links posted as submissions on /r/UnearthedArcana
    ua_sub_urls = subs["subreddit"] == "UnearthedArcana"
    ua_sub_urls = subs[ua_sub_urls]["link"]

    # Drop links from comments that were posted as submissions on /r/UnearthedArcana
    cmts_to_drop = cmts["link"].isin(ua_sub_urls)
    discards2 = cmts[cmts_to_drop].copy()
    cmts.drop(cmts[cmts_to_drop].index, inplace=True)

    log_str = f"Removed {len(discards2)} links from comments that have primary"
    log_str = log_str + " submissions on /r/UnearthedArcana"
    print(log_str)

    discards1["discard_reason"] = "Simple duplicate"
    discards2["discard_reason"] = "Has UA primary submission"
    discarded_cmts = pd.concat([discards1, discards2])

    return discarded_cmts


def _filter_dh_cross_posts(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """
    Helper function for filter_dh_cross_posts

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame of links to filter out
    dataset : str
        String for logging/reporting purposes, i.e. "comments" or "submissions."

    Returns
    -------
    pd.DataFrame
        DataFrame of the links that were removed
    """
    dh_inds = df["subreddit"] == "DnDHomebrew"
    ua_inds = df["subreddit"] == "UnearthedArcana"

    in_ua_urls = df["link"].isin(df.loc[ua_inds, "link"])
    dh_cross_posts = dh_inds & in_ua_urls

    discarded = df[dh_cross_posts].copy()
    discarded["discard_reason"] = "UA crosspost"

    df.drop(df[dh_cross_posts].index, inplace=True)

    log_str = f"Removed {len(discarded)} /r/DnDHomebrew {dataset} that were also"
    log_str = log_str + " cross-posted to /r/UnearthedArcana"

    print(log_str)

    return discarded


def filter_dh_cross_posts(
    cmts: pd.DataFrame,
    subs: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filters out links posted on /r/DnDHomebrew which were also posted to
    /r/UnearthedArcana

    Parameters
    ----------
    cmts : pd.DataFrame
        DataFrame of links found in comments
    subs : pd.DataFrame
        DataFrame of links found in primary submissions

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        Tuple of links removed from the comments and submissions
    """
    discarded_cmts = _filter_dh_cross_posts(df=cmts, dataset="comments")
    discarded_subs = _filter_dh_cross_posts(df=subs, dataset="submissions")

    return (discarded_cmts, discarded_subs)


def get_multi_link_parents_by_author(cmts: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Creates dictionary pairing authors (keys) with a list submission IDs (values)
    for the authors whcih have comments with multiple links.

    Parameters
    ----------
    cmts : pd.DataFrame
        DataFrame containing links from comments.

    Returns
    -------
    Dict[str, List[str]]
        authors (keys) with a list submission IDs (values)
    """
    comment_counts = cmts["submission_id"].value_counts()
    duplicate_ids = comment_counts[comment_counts > 1]

    multi_links = duplicate_ids.index.to_list()

    log_str = f"Found {sum(duplicate_ids)} links with shared parent submissions"
    log_str = log_str + f" (across {len(multi_links)} total submissions)"
    print(log_str)

    multi_authors = cmts[cmts["submission_id"].isin(multi_links)]["comment_author"]
    multi_authors = multi_authors.unique()

    results_dict: Dict[str, List[str]] = {author: [] for author in multi_authors}

    for parent in multi_links:
        author = cmts[cmts["submission_id"] == parent]["comment_author"]
        author = author.values[0]
        results_dict[author].append(parent)

    return results_dict


def filter_cmt_multi_links_by_date(cmts: pd.DataFrame) -> pd.DataFrame:
    """
    Filters out links where there is a pre-existing/older comment with the same
    link associated under the assumption that this is less likely to be a re-post

    Parameters
    ----------
    cmts : pd.DataFrame
        DataFrame containing links from comments.

    Returns
    -------
    pd.DataFrame
        DataFrame of the links that were removed
    """
    # Make sure dataframe is sorted by submission date
    cmts.sort_values(by=["submission_date"], ascending=False, inplace=True)

    # Create a dictionary of post authors and the submission IDs
    # that have multiple link comments
    multi_cmt_parents_by_author = get_multi_link_parents_by_author(cmts)

    # Create a dataframe to store discarded entries
    discarded = []
    # Loop over each author w/ multi-link comments
    for author in multi_cmt_parents_by_author.keys():
        # Subset by author
        author_df = cmts[cmts["submission_author"] == author]

        # Loop over all submission IDs starting with the most recent
        author_df = author_df.sort_values(
            ["submission_date", "comment_date"], ascending=[False, False]
        )

        processed_ids: List[str] = []
        for id in author_df["submission_id"].unique():
            # Get logical indexing subset for previously processed IDs
            processed_submissions = author_df["submission_id"].isin(processed_ids)

            # Logical indexing subset for current submission ID
            curr_submission = author_df["submission_id"] == id
            # Dataframe subset for current submission ID
            curr_submission_df = author_df[curr_submission]

            # Logical indexing subset for submissions posted before the current
            # statement is (not processed) & (not current)
            older_submissions = np.logical_and(~processed_submissions, ~curr_submission)
            older_urls = author_df[older_submissions]["link"]

            # Get subset to drop
            to_drop = curr_submission_df["link"].isin(older_urls)
            to_drop = curr_submission_df[to_drop]
            # Create a copy of these rows
            discarded.append(to_drop.copy())

            # Drop and add ID to processed list
            cmts.drop(to_drop.index, inplace=True)
            processed_ids.append(id)

        discarded = [i for i in discarded if isinstance(i, pd.DataFrame)]
        if len(discarded) > 1:
            disc_df = pd.concat(discarded)
        else:
            disc_df = discarded[0]

    disc_df["discard_reason"] = "Newer multi-comment"

    log_str = f"Discarded {len(disc_df)} links from authors with multiple link comments"
    log_str = log_str + " in favor of an older post associated with the same link."
    print(log_str)

    return disc_df
