#!/usr/bin/env python

from typing import Optional

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure


def _generate_comparison_plot(
    df: pd.DataFrame,
    metric: str,
    colour_scheme: str = "YlOrRd",
    slope_params: Optional[tuple[float, float, float]] = None,
    figsize: tuple[int, int] = (18, 6),
) -> Figure:
    """
    If the data contains only one unique entry in group A, a barplot is generated.
    If multiple unique entries in group A, it generates a heatmap. Please note that
    in this case, the mappings between entries in group A and group B must be of equal
    length.

    Args:
        df: DataFrame of your dataset

    Returns:
        Figure: Matplotlib figure containing the generated plot.
    """
    df = set_sample_names(df)
    if df["contaminated_samples"].nunique() == 1:
        fig = barplot(
            data=df,
            x="candidates",
            y=metric,
            xlab="candidates",
            ylab=metric,
            title=df["contaminated_samples"].iloc[0],
            figsize=figsize,
        )
    else:
        fig = heatmap(
            data=df,
            x="contaminated_samples",
            y="candidates",
            z=metric,
            xlab="contaminated_samples",
            ylab="candidates",
            title=None,
            colour_scheme=colour_scheme,
            slope_params=slope_params,
            figsize=figsize,
        )
    fig.tight_layout()
    return fig


def set_sample_names(sompy_df: pd.DataFrame) -> pd.DataFrame:
    sompy_df["contaminated_samples"] = (
        sompy_df["sompycmd"].apply(get_sample_name, sample="truth").apply(shorten)
    )
    sompy_df["candidates"] = (
        sompy_df["sompycmd"].apply(get_sample_name, sample="query").apply(shorten)
    )
    return sompy_df


def get_sample_name(sompycmd: str, sample: str = "truth") -> str:
    parts = sompycmd.split(" ")
    if sample == "truth":
        vcf_path = parts[-2]
    elif sample == "query":
        vcf_path = parts[-1]
    else:
        raise ValueError("Invalid key to `sample`: pick one of `truth`, `query`")

    vcf = vcf_path.split("/")[-1]
    sample_name = vcf.removesuffix(".vcf.gz")
    return sample_name


def shorten(name: str) -> str:
    parts = name.split("-")
    if len(parts) >= 3:
        return f"{parts[1]}-{parts[2]}"
    return name


def barplot(
    data: pd.DataFrame,
    x: str,
    y: str,
    xlab: str,
    ylab: str,
    title: str,
    figsize: tuple[int, int],
) -> Figure:
    fig, ax = plt.subplots(figsize=figsize)
    sns.barplot(data=data, x=x, y=y, ax=ax, legend=False)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    plt.xticks(rotation=45, ha="right")
    return fig


def heatmap(
    data: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    xlab: str,
    ylab: str,
    title: Optional[str],
    colour_scheme: str,
    figsize: tuple[int, int],
    slope_params: Optional[tuple[float, float, float]],
) -> Figure:
    fig, ax = plt.subplots(figsize=figsize)
    hm_data = data.pivot(index=x, columns=y, values=z)
    params = {"cmap": colour_scheme, "annot": True, "fmt": ".3f", "ax": ax}
    if slope_params:
        if len(slope_params) != 3:
            raise TypeError(
                f"Malformed argument to `slope_params`; expected 3-tuple, got {slope_params}"
            )
        params["norm"] = TwoSlopeNorm(
            vmin=slope_params[0], vcenter=slope_params[1], vmax=slope_params[2]
        )
    # Invoking "# type: ignore" to silence potentially-erroneous
    # mypy behaviour - see https://github.com/python/mypy/issues/18481
    sns.heatmap(hm_data, **params)  # type: ignore

    # In seaborn, "X" on a heatmap is actually the side where the y-axis would normally be, and
    # "Y" is along the bottom where the x-axis would normally be. Since we want the longer data
    # to be on the bottom, we need to swap the xlab and ylab around:
    ax.set_xlabel(ylab)
    ax.set_ylabel(xlab)
    if title:
        ax.set_title(title)
    plt.xticks(rotation=45, ha="right")
    return fig
