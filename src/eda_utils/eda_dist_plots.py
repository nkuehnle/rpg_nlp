# Utilities
from pathlib import Path
from typing import List, Optional

# Data handling / generic ML
import pandas as pd
import numpy as np

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns


def _get_nice_title(pref: str) -> str:
    pref = pref.replace("_", " ").replace("md", "markdown")
    pref = " ".join([w.capitalize() for w in pref.split(" ")])
    return pref


def _get_nice_col_name(col_name: str, pref: str) -> str:
    col_name = col_name.replace(f"{pref}_", "")
    col_name = col_name.replace("_", " ")
    col_name = " ".join([c.capitalize() for c in col_name.split(" ")])
    return col_name


def _get_pref_data(
    df: pd.DataFrame, pref: str, color: Optional[str] = None
) -> pd.DataFrame:
    """_summary_

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        String contained in all variables of interest. Also used as prefix for saving
    color : Optional[str], optional
        _description_, by default None

    Returns
    -------
    pd.DataFrame
        _description_
    """
    var_cols: List[str] = [c for c in df.columns if pref in c]
    cols = var_cols + [color]
    cols = [c for c in cols if isinstance(c, str)]
    plot_data = df[cols].copy()
    for col in var_cols:
        plot_data[col] = plot_data[col].astype("float32")

    plot_data = plot_data.rename(
        columns={col: _get_nice_col_name(col, pref) for col in var_cols}
    )

    return plot_data


def pref_pairplot(
    df: pd.DataFrame,
    pref: str,
    save_path: Path,
    color: Optional[str] = "submission_flair",
):
    """
    Generates/plots a pairplot in Seaborn using columns that contain the
    designated prefix string.

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        String contained in all variables of interest. Also used as prefix for saving
    save_path : Path
        _description_
    color : Optional[str], optional
        _description_, by default "submission_flair"
    """
    plot_data = _get_pref_data(df=df, pref=pref, color=color)

    sns.pairplot(plot_data, hue=color, diag_kind="kde", corner=True)
    plt.suptitle(_get_nice_title(pref))

    # Save and show
    plt.savefig(f"{save_path/f'{pref}_pairplot.pdf'}")
    plt.show()
    plt.close()


def pref_violinplots(
    df: pd.DataFrame,
    pref: str,
    save_path: Path,
    color: Optional[str] = "submission_flair",
    exclude_outliers: bool = True,
):
    """Generates/plots a grid of violinplots in Seaborn for each variable that contains
    the prefix string (excludes quartiles +/- IQR*1.5 outliers to accomodate view)

    Parameters
    ----------
    df : pd.DataFrame
        _description_
    pref : str
        String contained in all variables of interest. Also used as prefix for output
    pref : str
        String contained in all variables of interest. Also used as prefix for saving
    color : Optional[str], optional
        _description_, by default "submission_flair"
    exclude_outliers : bool, optional
        _description_, by default True
    """
    # Get copy of data ready
    plot_data = _get_pref_data(df=df, pref=pref, color=color)

    col_names = plot_data.columns.tolist()
    if color:
        col_names.remove(color)

    # Create plot grid
    size = len(col_names)
    rows = round(size / 2)
    h_ratios = [5.25 for _ in range(rows)]
    fig = plt.figure(figsize=(20, 6 * rows))
    gs = fig.add_gridspec(
        nrows=rows,
        ncols=2,
        width_ratios=[9, 9],
        height_ratios=h_ratios,
        wspace=0.2,
        hspace=0.3,
    )

    # Fill plot grid
    all_inds = np.ones(len(plot_data), dtype=bool)
    for i, col in enumerate(col_names):
        grid_col = i % 2
        grid_row = i // 2
        ax = fig.add_subplot(gs[grid_row, grid_col])

        if exclude_outliers:
            q75, q25 = np.percentile(plot_data[col], [75, 25])
            iqr = q75 - q25
            inds_to_use = (plot_data[col] <= q75 + (1.5 * iqr)) & (
                plot_data[col] >= q25 - (1.5 * iqr)
            )
        else:
            inds_to_use = all_inds

        sns.violinplot(data=plot_data[inds_to_use], x=color, y=col, ax=ax)

        # Add nice labels
        ax.set_xlabel(None)
        for label in ax.get_xticklabels():
            label.set_rotation(45)
            label.set_fontsize(10)
        ax.set_ylabel(col)
    plt.suptitle(_get_nice_title(pref))

    # Save and show
    plt.savefig(f"{save_path/f'{pref}_violinplots.pdf'}")
    plt.show()
    plt.close()
