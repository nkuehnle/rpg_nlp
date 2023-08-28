import pandas as pd
import numpy as np
from pathlib import Path
import warnings


class IncorrectFileTypeWarning(UserWarning):
    pass


def pandas_from_path(path: Path) -> pd.DataFrame:
    file_type = path.suffix
    if ".csv" == file_type:
        data = pd.read_csv(path)
    elif file_type in (".pickle", ".pkl"):
        data = pd.read_pickle(path)
    else:
        warnings.warn(
            message=f"Expected .csv, .pkl, or .pickle, got: {file_type}",
            category=IncorrectFileTypeWarning,
        )

    return data


def save_pandas_to_path(data: pd.DataFrame, path: Path) -> pd.DataFrame:
    file_type = path.suffix
    if ".csv" == file_type:
        data.to_csv(path, sep=",", index=False)
    elif file_type in (".pickle", ".pkl"):
        data.to_pickle(path)
    else:
        warnings.warn(
            message=f"Expected .csv, .pkl, or .pickle, got: {file_type}",
            category=IncorrectFileTypeWarning,
        )

    return data


def fill_missing_cols(data: pd.DataFrame):
    if not ("manually_reviewed" in data.columns):
        data["manually_reviewed"] = False
    if not ("related_link" in data.columns):
        data["related_link"] = False
    if not ("corrected_flair" in data.columns):
        data["corrected_flair"] = np.nan
    data["manually_reviewed"] = data["manually_reviewed"].fillna(False)
    data["related_link"] = data["related_link"].fillna(False)
    data["corrected_flair"] = data["corrected_flair"].fillna(data["submission_flair"])


"manually_reviewed", "related_link", "corrected_flair"
