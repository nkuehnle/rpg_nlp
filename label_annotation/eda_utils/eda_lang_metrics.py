# Utility Imports
from typing import Optional, List, Callable, Dict

# Imports for data processing/handling/basic calculations
import numpy as np
import pandas as pd
from collections import Counter

# NLP-specific processing
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
from nltk.tokenize.treebank import TreebankWordDetokenizer

EN_STOPWORDS = stopwords.words("english")
EN_STOPWORDS = [sw.lower() for sw in EN_STOPWORDS]


def get_char_counts(
    df: pd.DataFrame,
    pref: str,
    text_col: str,
    patterns_to_count: Dict[str, str] = {"hastag_runs": r"#+", "asterisk_runs": r"\*+"},
):
    """_summary_

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        _description_
    text_col : str
        _description_
    patterns_to_count : List[str], optional
        _description_, by default [r"#+", r"\*+"]
    """
    # Character/word/sentences
    df[f"{pref}_char_count"] = df[text_col].str.len().astype("Int32")
    for col, pat in patterns_to_count.items():
        df[f"{pref}_{col}"] = df[text_col].str.count(pat).astype("Int32")


def count_stopwords(
    df: pd.DataFrame,
    pref: str,
    token_col: Optional[str] = None,
    text_col: Optional[str] = None,
    tokenizer: Optional[Callable] = None,
    text_to_lower: bool = False,
):
    """_summary_

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        _description_
    token_col : Optional[str], optional
        _description_, by default None
    text_col : Optional[str], optional
        _description_, by default None
    tokenizer : Optional[Callable], optional
        _description_, by default None

    Raises
    ------
    IndexError
        _description_
    """
    stopwords = EN_STOPWORDS

    def count_sw(counter: Counter, stopwords: List[str]) -> int:
        count = 0
        for sw in stopwords:
            count += counter[sw]
        return count

    if tokenizer:
        _stopwords = []
        for sw in stopwords:
            _stopwords.extend(tokenizer(sw))
        stopwords = _stopwords

    if token_col in df.columns:
        tokens = df[token_col]
    elif text_col and tokenizer:
        tokens = df[text_col].map(tokenizer)
    else:
        raise IndexError("Missing token/text column index")

    df[f"{pref}_stopword_count"] = tokens.map(
        lambda x: count_sw(Counter(x), stopwords)
    ).astype("Int32")


def detokenize(tokens: List[str]) -> str:
    """_summary_

    Parameters
    ----------
    tokens : List[str]
        _description_

    Returns
    -------
    str
        _description_
    """
    return TreebankWordDetokenizer().detokenize(tokens)


def words_to_sents(word_tokens: List[str]) -> List[str]:
    """_summary_

    Parameters
    ----------
    word_tokens : List[str]
        _description_

    Returns
    -------
    List[str]
        _description_
    """
    sentences = sent_tokenize(detokenize(word_tokens))
    return sentences


def average_len(tokens: List[str]) -> float:
    """_summary_

    Parameters
    ----------
    tokens : List[str]
        _description_

    Returns
    -------
    float
        _description_
    """
    if tokens:
        avg = np.mean([len(token) for token in tokens])
    else:
        avg = float(0)

    return avg


def calc_token_sizes(
    df: pd.DataFrame,
    pref: str,
    text_col: Optional[str] = None,
    word_token_col: Optional[str] = None,
    sent_token_col: Optional[str] = None,
):
    """_summary_

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        _description_
    text_col : Optional[str], optional
        _description_, by default None
    word_token_col : Optional[str], optional
        _description_, by default None
    sent_token_col : Optional[str], optional
        _description_, by default None
    """
    # Words
    if word_token_col:
        word_tokens = df[word_token_col]
    else:
        print("\tWord tokens not determined yet, defaulting to NLTK word_tokenize")
        word_tokens = df[text_col].map(word_tokenize)
    # Calculate word count/average word count
    df[f"{pref}_word_count"] = word_tokens.map(len).astype("Int32")
    df[f"{pref}_avg_word_len"] = word_tokens.map(average_len)

    # Sentences
    if sent_token_col:
        sent_tokens = df[sent_token_col]
    else:
        sent_tokens = word_tokens.map(words_to_sents)
    # Calculate
    df[f"{pref}_sent_count"] = sent_tokens.map(len).astype("Int32")
    df[f"{pref}_avg_sent_len"] = sent_tokens.map(average_len)
