from typing import List, Sequence, Callable, Set, TypeVar, Generic
import pandas as pd
import numpy as np
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from num2words import num2words
from itertools import chain, combinations
from sklearn.feature_extraction.text import CountVectorizer
from statistics import variance
import re


class MultipleSplitsError(Exception):
    pass


class TokenSplitter:
    def __init__(self, min_subtoken_size: int, max_subtokens: int = 2):
        self.min_subtoken_size = min_subtoken_size
        self.max_subtokens = max_subtokens

    def valid_split_range(self, split_range: Sequence[int]) -> bool:
        prev_val = 0
        for val in split_range:
            if (val - prev_val) < self.min_subtoken_size:
                return False
            prev_val = val
        return True

    def get_splits(self, token: str) -> List[List[str]]:
        # Adapted from http://wordaligned.org/articles/partitioning-with-python
        """Get all possible split of the token that meet the minimum sub-token length.

        Parameters
        ----------
        token : strfrom collections import defaultdict
            _description_

        Returns
        -------
        List[str]
            _description_
        """

        n = len(token)
        # List of ints starting at min_subtokens size and going up to n
        mid = list(range(self.min_subtoken_size, n, 1))
        # Get all combinations of splits up to max_subtokens in in length
        split_ranges = list(
            (d for i in range(1, self.max_subtokens) for d in combinations(mid, i))
        )
        # Filter out splits with intervals less than min_subtoken_size
        split_ranges = [d for d in split_ranges if self.valid_split_range(d)]
        # Get the actual splits by mapping the slice function onto chained vals
        splits = [
            [token[s] for s in map(slice, chain([0], d), chain(d, [n]))]
            for d in split_ranges
        ]
        return splits


K = TypeVar("K")
V = TypeVar("V")


class TokenMapper(Generic[K, V], dict):
    def __missing__(self, key: K) -> List[K]:
        return [key]


def convert_numbers(text: str) -> str:
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
    ORD_SUFF: List[str] = ["st", "nd", "rd", "th"]

    def to_num(match: re.Match) -> str:
        match_str: str = match.group(0)
        match_str = match_str.replace(",", "")
        match_str = match_str.strip()

        check_ord_strings = [suff in match_str.lower() for suff in ORD_SUFF]
        if any(check_ord_strings):
            ind = check_ord_strings.index(True)
            suff = ORD_SUFF[ind]
            num_str = match_str.lower().replace(suff, "")
            return num2words(num_str, to="ordinal")

        else:
            return num2words(match_str)

    # Define pattern
    base_pat = r"[0-9]+"
    deci_pat = r"(\.[0-9]+)"
    thou_pat = r"([0-9]+,+)"
    ord_pat = r"((st)|(nd)|(rd)|(th))"
    pattern = f"{thou_pat}*{base_pat}({deci_pat}|{ord_pat})?"

    return re.sub(pattern=pattern, repl=to_num, string=text, flags=re.IGNORECASE)


class EmbeddingAwareTokenizer:
    def __init__(
        self,
        embedding_vocab: Sequence[str],
        min_counts_common_token: int,
        min_subtoken_size: int,
        max_subtokens: int,
        unknown_token: str = "",
    ):
        self.embedding_vocab: Set[str] = set([w.lower() for w in embedding_vocab])
        self.min_counts_common_token = min_counts_common_token
        self.unknown_token = unknown_token
        self.min_subtoken_size = min_subtoken_size
        self.max_subtokens = max_subtokens
        self.splitter = TokenSplitter(min_subtoken_size, max_subtokens)
        self.common_vocab: Set[str] = set()
        self.token_mappings: TokenMapper[str, List[str]] = TokenMapper()
        self._fitted: bool = False

    @property
    def token_mapping_keys(self) -> Set[str]:
        keys = set([k for k in self.token_mappings.keys()])
        return keys

    @property
    def vocab(self) -> Set[str]:
        vocab = self.embedding_vocab.union(self.common_vocab)
        return vocab

    def _tokenize(self, text: str) -> List[str]:
        """_summary_

        Parameters
        ----------
        text : str
            _description_

        Returns
        -------
        List[str]
            _description_
        """
        initial_tokens = word_tokenize(text)
        tokens: List[str] = []
        for token in initial_tokens:
            tokens.extend(self.token_mappings[token])

        known_terms = self.common_vocab.union(self.token_mapping_keys).union(
            self.embedding_vocab
        )

        # If there are unknown tokens, get the POS tags
        if any([t not in known_terms for t in tokens]):
            if self.unknown_token == "":
                pos_tags = pos_tag(tokens)

                for i, token in enumerate(pos_tags):
                    if token[0] not in known_terms:
                        ptag = "<" + token[1] + ">"
                        tokens[i] = ptag
                        self.token_mappings[token] = ptag
            else:
                for i, token in enumerate(tokens):
                    if token not in known_terms:
                        tokens[i] = self.unknown_token
                        self.token_mappings[token] = self.unknown_token
        return tokens

    def tokenize(self, text: str) -> List[str]:
        """_summary_

        Parameters
        ----------
        text : str
            _description_

        Returns
        -------
        List[str]
            _description_
        """
        text = text.lower()
        text = convert_numbers(text)
        tokens = self._tokenize(text)

        return tokens

    def get_count_df(self, corpus: pd.Series, tokenizer: Callable) -> pd.DataFrame:
        """_summary_

        Parameters
        ----------
        corpus : pd.Series
            _description_
        tokenizer : Callable
            _description_

        Returns
        -------
        pd.DataFrame
            _description_
        """
        vectorizer = CountVectorizer(tokenizer=tokenizer, token_pattern=None)
        count_vector = vectorizer.fit_transform([corpus])
        counts = count_vector.toarray().sum(axis=0)
        count_df = pd.DataFrame(
            {"token": vectorizer.get_feature_names_out(), "count": counts}
        )

        return count_df

    def map_delimited_tokens(self, count_df: pd.DataFrame, delim: str) -> pd.DataFrame:
        """Takes a dataframe of tokens that may contain spelling variations with
        different delimiter usage and picks a prefered variation.
        The prefered variation will be the most common one in the embedding vocab list.
        If no variations are in the known tokens, it will go with the most common.

        Updates token mappings to include a mapping of each variant to the prefered token
        (contained in a list for compatibility with subtoken splitting).

        Returns the original dataframe with the variant rows merged/summed.

        Parameters
        ----------
        count_df : pd.DataFrame
            _description_
        delim : str
            _description_

        Returns
        -------
        pd.DataFrame
            _description_
        """
        df = count_df.copy()
        df["base_token"] = df["token"].str.replace(delim, "", regex=False)
        embedding_vocab = self.embedding_vocab
        df["is_known"] = df["token"].isin(embedding_vocab)
        df = df[df["base_token"].str.len() > 1]
        df = df.sort_values(by=["is_known", "count"], ascending=[False, False])
        preferred_variations: Sequence[str] = df[
            ~df["base_token"].duplicated(keep="first")
            & df["base_token"].duplicated(keep=False)
        ]["token"]

        mappings = {}
        for token in preferred_variations:
            basic_token = token.replace(delim, "")
            variant_mask = (df["base_token"] == basic_token) & (df["token"] != token)
            variants = df.loc[variant_mask, "token"]
            for v in variants:
                mappings[v] = [token]

        self.token_mappings.update(mappings)

        df = df.groupby(["base_token"], as_index=False).agg(
            {"count": "sum", "token": "first"}
        )

        return df

    def check_valid_split(self, split: List[str], vocab: Set[str]) -> bool:
        """_summary_

        Parameters
        ----------
        split : List[str]
            _description_
        vocab : Set
            _description_

        Returns
        -------
        bool
            _description_
        """
        return all([token in vocab for token in split])

    def get_best_split(self, token: str, vocab: Set[str]) -> List[str]:
        """_summary_

        Parameters
        ----------
        token : str
            _description_

        Returns
        -------
        List[str]
            _description_
        """

        def subtoken_variance(subtokens: List[str]) -> float:
            lengths = [len(subtoken) for subtoken in subtokens]
            return variance(lengths)

        alpha_token = re.sub(
            pattern=r"[^A-Z]", repl="", string=token, flags=re.IGNORECASE
        )
        splits = self.splitter.get_splits(alpha_token)
        valid_splits = [
            split for split in splits if self.check_valid_split(split, vocab)
        ]
        if any(valid_splits):
            length = min([len(split) for split in valid_splits])
            valid_splits = [split for split in valid_splits if len(split) == length]
            split_variances = [subtoken_variance(split) for split in valid_splits]
            min_variance = min(split_variances)
            num_matching = len(
                [svar for svar in split_variances if svar == min_variance]
            )
            if num_matching == 1:
                best_split = valid_splits[split_variances.index(min_variance)]
                return best_split
            else:
                return [token]
        else:
            return [token]

    def map_delim_splits(self, count_df: pd.DataFrame, delim: str):
        """_summary_

        Parameters
        ----------
        count_df : pd.DataFrame
            _description_
        delim : str
            _description_
        """

        # Use only tokens containing the delimiter
        df = count_df[count_df["token"].str.contains(delim, regex=False)].copy()
        # Get and check the splits
        df["split_tokens"] = df["token"].str.split(delim, regex=False)
        df["split_tokens"] = df["split_tokens"].map(
            lambda tokens: [t for t in tokens if t != ""]
        )
        vocab = self.embedding_vocab.union(self.common_vocab)
        df["valid_splits"] = df["split_tokens"].map(
            lambda toks: sum([t in vocab for t in toks]) > 0
        )

        # Create and add mappings
        mappings = df[df["valid_splits"]].set_index("token")["split_tokens"].to_dict()
        self.token_mappings.update(mappings)

        # Update original DF for return
        count_df = count_df[~count_df["token"].isin([k for k in mappings.keys()])]

        for token, subtokens in mappings.items():
            added_count = df[df["token"] == token]["count"]
            subtoken_rows = count_df["token"].isin(subtokens)
            count_df.loc[subtoken_rows, "count"] = (
                count_df.loc[subtoken_rows, "count"] + added_count
            )

        return count_df

    def map_compound_tokens(self, count_df: pd.DataFrame) -> pd.DataFrame:
        """Takes a table of tokens that may be compounds of other shorter tokens and
        finds such instances.
        The function will ensure that the original tokens are split into no more than
        N subtokens (self.max_subtokens) of at least K length per subtoken
        (self.min_subtoken_length), where all of the subtokens are considered "common").
        If multiple valid instances exist, it will pick the one where the
        variation in subtoken length is smallest (where individual tokens tend to be
        longer/more complex). If there is still more than one instance, it will raise a
        MultipleSplitsError.

        Add a mappings for each variant to the prefered token (contained in a
        list for compatibility with subtoken splitting) to self.token_mappings


        Parameters
        ----------
        count_df : pd.DataFrame
            _description_
        delimiters : List[str], optional
            _description_, by default ["-", "'", "."]

        Returns
        -------
        pd.DataFrame
            _description_
        """
        df = count_df.copy()
        # Should not already be in the common vocab
        df = df[~df["token"].isin(self.common_vocab)].copy()
        # Ignore instances that are too short to actually split
        df = df[df["token"].str.len() >= (2 * self.min_subtoken_size)]
        # Only check words that actually contain letters
        df = df[df["token"].str.contains(r"(?i)[A-Z]")]
        # For better performance skip really long words
        df = df[df["token"].str.len() <= 25]

        # Find any tokens with a valid split (i.e. 2 or more subtokens
        vocab = self.common_vocab
        df["best_split"] = df["token"].map(
            lambda token: self.get_best_split(token, vocab)
        )
        df = df[df["best_split"].map(len) > 1]
        mappings = df.set_index("token")["best_split"].to_dict()
        self.token_mappings.update(mappings)

        # Get anything still remaining
        count_df = count_df[~count_df["token"].isin([k for k in mappings.keys()])]

        return df

    def fit(self, corpus: str):
        """_summary_

        Parameters
        ----------
        corpus : str
            _description_
        """
        if not (isinstance(corpus, str)):
            if isinstance(corpus, (list, pd.Series, np.ndarray)):
                corpus = "\n".join(corpus)
            else:
                raise TypeError(
                    "Expected a single string or a list, Pandas series or numpy array of strings"
                )

        corpus = corpus.lower()

        count_df = self.get_count_df(corpus, tokenizer=word_tokenize)
        # Check for tokens that differ only by hyphenation or apostrophe
        for d in ["-", "'", "."]:
            count_df = self.map_delimited_tokens(count_df=count_df, delim=d)

        # Update vocabulary and DF
        common_tokens = count_df["count"] >= self.min_counts_common_token
        self.common_vocab.update(count_df[common_tokens]["token"])
        count_df = count_df[~count_df["token"].isin(self.embedding_vocab)]

        # Check if there are any delimited terms that can be split
        for d in ["-", "'", "."]:
            count_df = self.map_delim_splits(count_df=count_df, delim=d)

        # Update vocabulary
        common_tokens = count_df["count"] >= self.min_counts_common_token
        self.common_vocab.update(count_df[common_tokens]["token"])
        # Check for tokens that can be split into two or more subtokens
        count_df = self.map_compound_tokens(count_df)

        self._fitted = True

    def fit_transform(self, corpus: pd.Series) -> pd.Series:
        """_summary_

        Parameters
        ----------
        corpus : pd.Series
            _description_

        Returns
        -------
        pd.Series
            _description_
        """
        if not isinstance(corpus, pd.Series):
            corpus = pd.Series(corpus)
        corpus_str = "\n".join(corpus)
        corpus = convert_numbers(corpus)
        self.fit(corpus_str)
        tokenized_corpus = corpus.map(self.tokenize)
        return tokenized_corpus

def do_nothing(tokens: List[str]):
    """
    Return pre-determined tokens to sklearn count vectorizer
    If this is a string (i.e. for stopwords), return the string as a list

    Parameters
    ----------
    tokens : List[str]
        _description_

    Returns
    -------
    _type_
        _description_
    """
    if isinstance(tokens, str):
        return [tokens]
    else:
        return tokens