# Utilities
from pathlib import Path
from typing import List

# Data handling
import pandas as pd
from collections import Counter

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud

# NLP-specific tools
from nltk.tokenize import word_tokenize


def check_alnum(string: str) -> bool:
    for letter in string:
        if letter.isalnum():
            return True

    return False


def plot_top_words(
    documents: pd.DataFrame,
    label: str,
    word_token_col: str,
    text_col: str,
    stop_words: List[str],
    n_words: int,
    save_path: Path,
):
    """_summary_

    Parameters
    ----------
    documents : pd.DataFrame
        _description_
    label : str
        _description_
    stop_words : List[str]
        _description_
    n_words : int
        _description_
    save_path : Path
        _description_
    """
    _stopwords = [word_tokenize(sw) for sw in stop_words]
    stop_words = []
    for sw in _stopwords:
        stop_words.extend(sw)

    num_docs = documents.shape[0]

    # Create word cloud
    wordcloud = WordCloud(
        background_color="white",
        max_words=200,
        relative_scaling=1,
        collocations=True,
        collocation_threshold=10,
        normalize_plurals=True,
        stopwords=stop_words,
    )
    wordcloud = wordcloud.generate("\n".join(documents[text_col].str.lower().to_list()))

    # Get top N words
    tokens = []
    for tokenset in documents[word_token_col]:
        tokens += tokenset

    tokens = [i for i in tokens if check_alnum(i)]
    tokens = [i for i in tokens if "<" not in i]
    tokens = [i for i in tokens if i not in stop_words]

    words = []
    counts = []
    counter = Counter(tokens)
    top_words = counter.most_common(n=n_words)
    for word, count in top_words:
        words.append(word)
        counts.append(count / num_docs)
    count_df = pd.DataFrame({"word": words, "count": counts})

    # Set up main figure grid
    fig = plt.figure(figsize=(15, 5))
    gs = fig.add_gridspec(nrows=1, ncols=2, width_ratios=[5, 4], wspace=0.3)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    # Add wordcloud
    ax1.imshow(wordcloud)
    ax1.axis("off")

    # Plot top N words
    sns.barplot(data=count_df, y="word", x="count", ax=ax2)
    ax2.set_title(f"Top {n_words} Word Tokens")
    ax2.set_xlabel("Count/Document")
    ax2.set_ylabel("Word Token")

    # Finalize composite figure
    fig.suptitle(f"Words Associated with '{label}' Flair (n={num_docs})", fontsize=22)
    plt.savefig(f"{save_path/ (label + '_word_frequency.png')}")
    plt.show()
    plt.close()
