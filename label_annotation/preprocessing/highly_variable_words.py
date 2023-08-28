# Modeling mean-variance relationship
from pygam import LinearGAM, s
import pygam.pygam as pygam

# Data processing/typing
import scipy.sparse as sp_sparse
import numpy as np
from scipy import sparse
import numba
import pandas as pd
from typing import Tuple
from pathlib import Path

# Plotting
from matplotlib import pyplot as plt
from matplotlib import rcParams

# Adapted from Scanpy
# https://github.com/scverse/scanpy


def get_mean_var(
    X: sparse.spmatrix | np.ndarray, *, axis=0
) -> Tuple[np.ndarray, np.ndarray]:
    if sparse.issparse(X):
        mean, var = sparse_mean_variance_axis(X, axis=axis)
    else:
        mean = np.mean(X, axis=axis, dtype=np.float64)
        mean_sq = np.multiply(X, X).mean(axis=axis, dtype=np.float64)
        var = mean_sq - mean**2
    # enforce R convention (unbiased estimator) for variance
    var *= X.shape[axis] / (X.shape[axis] - 1)
    return mean, var


def sparse_mean_variance_axis(mtx: sparse.spmatrix, axis: int) -> np.ndarray:
    """
    This code and internal functions are based on sklearns
    `sparsefuncs.mean_variance_axis`.
    Modifications:
    * allow deciding on the output type, which can increase accuracy when calculating
        the mean and variance of 32bit floats.
    * This doesn't currently implement support for null values, but could.
    * Uses numba not cython

    Parameters
    ----------
    mtx : sparse.spmatrix
        _description_
    axis : int
        _description_

    Returns
    -------
    np.ndarray
        _description_

    Raises
    ------
    ValueError
        _description_
    """
    assert axis in (0, 1)
    if isinstance(mtx, sparse.csr_matrix):
        ax_minor = 1
        shape = mtx.shape
    elif isinstance(mtx, sparse.csc_matrix):
        ax_minor = 0
        shape = mtx.shape[::-1]
    else:
        raise ValueError("This function only works on sparse csr and csc matrices")
    if axis == ax_minor:
        return sparse_mean_var_major_axis(
            mtx.data, mtx.indices, mtx.indptr, *shape, np.float64
        )
    else:
        return sparse_mean_var_minor_axis(mtx.data, mtx.indices, *shape, np.float64)


@numba.njit(cache=True)
def sparse_mean_var_minor_axis(
    data: np.ndarray, indices: np.ndarray, major_len: int, minor_len: int, dtype: type
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes mean and variance for a sparse matrix for the minor axis.
    Given arrays for a csr matrix, returns the means and variances for each
    column back.

    Parameters
    ----------
    data : np.ndarray
        _description_
    indices : np.ndarray
        _description_
    major_len : int
        _description_
    minor_len : int
        _description_
    dtype : type
        _description_

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        _description_
    """
    non_zero = indices.shape[0]

    means: np.ndarray = np.zeros(minor_len, dtype=dtype)
    variances: np.ndarray = np.zeros_like(means, dtype=dtype)

    counts = np.zeros(minor_len, dtype=np.int64)

    for i in range(non_zero):
        col_ind = indices[i]
        means[col_ind] += data[i]

    for i in range(minor_len):
        means[i] /= major_len

    for i in range(non_zero):
        col_ind = indices[i]
        diff = data[i] - means[col_ind]
        variances[col_ind] += diff * diff
        counts[col_ind] += 1

    for i in range(minor_len):
        variances[i] += (major_len - counts[i]) * means[i] ** 2
        variances[i] /= major_len

    return means, variances


@numba.njit(cache=True)
def sparse_mean_var_major_axis(
    data: np.ndarray,
    indices: np.ndarray,
    indptr: np.ndarray,
    major_len: int,
    minor_len: int,
    dtype: type,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes mean and variance for a sparse array for the major axis.
    Given arrays for a csr matrix, returns the means and variances for each
    row back.

    Parameters
    ----------
    data : np.ndarray
        _description_
    indices : np.ndarray
        _description_
    indptr : np.ndarray
        _description_
    major_len : int
        _description_
    minor_len : int
        _description_
    dtype : type
        _description_

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]
        _description_
    """
    means: np.ndarray = np.zeros(major_len, dtype=dtype)
    variances: np.ndarray = np.zeros_like(means, dtype=dtype)

    for i in range(major_len):
        startptr = indptr[i]
        endptr = indptr[i + 1]
        counts = endptr - startptr

        for j in range(startptr, endptr):
            means[i] += data[j]
        means[i] /= minor_len

        for j in range(startptr, endptr):
            diff = data[j] - means[i]
            variances[i] += diff * diff

        variances[i] += (minor_len - counts) * means[i] ** 2
        variances[i] /= minor_len

    return means, variances


def seurat_v3_highly_variable_selection(
    X: np.ndarray, feature_names: np.ndarray, lam: float, n_splines: int, n_top: int
) -> Tuple[pd.DataFrame, pygam.LinearGAM]:
    """
    For further implementation details see https://www.overleaf.com/read/ckptrbgzzzpg

    Parameters
    ----------
    X : np.array
        _description_
    feature_names : np.ndarray
        _description_
    lam : float
        _description_
    n_splines : int
        _description_
    n_top : int, optional
        _description_

    Returns
    -------
    Tuple[pd.DataFrame, pygam.LinearGAM]
        _description_
    """
    df = pd.DataFrame(index=feature_names)
    df["means"], df["variances"] = get_mean_var(X)

    batch_info = pd.Categorical(np.zeros(X.shape[0], dtype=int))

    norm_vars = []
    for b in np.unique(batch_info):
        X_batch = X[batch_info == b]

        mean, var = get_mean_var(X_batch)
        not_const = var > 0
        estimat_var = np.zeros(X.shape[1], dtype=np.float64)

        y = np.log10(var[not_const])
        x = np.log10(mean[not_const])
        model = LinearGAM(s(0), n_splines=n_splines, lam=lam).fit(x, y)
        estimat_var[not_const] = model.predict(x)
        reg_std = np.sqrt(10**estimat_var)

        batch_counts = X_batch.astype(np.float64).copy()
        # clip large values as in Seurat
        N = X_batch.shape[0]
        vmax = np.sqrt(N)
        clip_val = reg_std * vmax + mean
        if sp_sparse.issparse(batch_counts):
            batch_counts = sp_sparse.csr_matrix(batch_counts)
            mask = batch_counts.data > clip_val[batch_counts.indices]
            batch_counts.data[mask] = clip_val[batch_counts.indices[mask]]

            squared_batch_counts_sum = np.array(batch_counts.power(2).sum(axis=0))
            batch_counts_sum = np.array(batch_counts.sum(axis=0))
        else:
            clip_val_broad = np.broadcast_to(clip_val, batch_counts.shape)
            np.putmask(
                batch_counts,
                batch_counts > clip_val_broad,
                clip_val_broad,
            )

            squared_batch_counts_sum = np.square(batch_counts).sum(axis=0)
            batch_counts_sum = batch_counts.sum(axis=0)

        norm_var = (1 / ((N - 1) * np.square(reg_std))) * (
            (N * np.square(mean))
            + squared_batch_counts_sum
            - 2 * batch_counts_sum * mean
        )
        norm_vars.append(norm_var.reshape(1, -1))

    norm_vars_arr = np.concatenate(norm_vars, axis=0)
    # argsort twice gives ranks, small rank means most variable
    ranked_norm_vars = np.argsort(np.argsort(-norm_vars_arr, axis=1), axis=1)

    # this is done in SelectIntegrationFeatures() in Seurat v3
    ranked_norm_vars = ranked_norm_vars.astype(np.float32)
    num_batches_high_var = np.sum((ranked_norm_vars < n_top).astype(int), axis=0)
    ranked_norm_vars[ranked_norm_vars >= n_top] = np.nan
    ma_ranked = np.ma.masked_invalid(ranked_norm_vars)
    median_ranked = np.ma.median(ma_ranked, axis=0).filled(np.nan)

    df["highly_variable_nbatches"] = num_batches_high_var
    df["highly_variable_rank"] = median_ranked
    df["variances_norm"] = np.mean(norm_vars_arr, axis=0)

    sorted_index = (
        df[["highly_variable_rank", "highly_variable_nbatches"]]
        .sort_values(
            ["highly_variable_rank", "highly_variable_nbatches"],
            ascending=[True, False],
            na_position="last",
        )
        .index
    )
    df["highly_variable"] = False
    df.loc[sorted_index[: int(n_top)], "highly_variable"] = True

    df = df.drop(["highly_variable_nbatches"], axis=1)

    return df, model


def get_highly_variable_words(
    X: np.ndarray,
    feature_names: np.ndarray,
    lam: float,
    n_splines: int,
    n_top: int = 5000,
) -> pd.DataFrame:
    """
    Plot dispersions or normalized variance versus means for words.

    Produces Supp. Fig. 5c of Zheng et al. (2017) and MeanVarPlot() and
    VariableFeaturePlot() of Seurat.

    Parameters
    ----------
    X : np.array
        _description_
    feature_names : np.ndarray
        _description_
    lam : float
        _description_
    n_splines : int
        _description_
    n_top : int, optional
        _description_, by default 5000

    Returns
    -------
    pd.DataFrame
        _description_
    """
    result, model = seurat_v3_highly_variable_selection(
        X, feature_names, lam, n_splines, n_top
    )

    return result
