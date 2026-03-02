#!/usr/bin/env python

from typing import Tuple, Optional

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure

def generate_comparison_plot(df: pd.DataFrame, 
                             group_a: str,
                             group_b: str,
                             metric: str,
                             colour_scheme: str="YlOrRd",
                             slope_params: Optional[Tuple[float, float, float]]=None,
                             figsize: Tuple[int, int]=(10, 6)) -> Figure:
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
    if df[group_a].nunique() == 1:
        fig = barplot(data=df,
                      x=group_b,
                      y=metric,
                      xlab=group_b,
                      ylab=metric,
                      title=df[group_a].iloc[0],
                      figsize=figsize)
    else:
        fig = heatmap(data=df, 
                      x=group_a, 
                      y=group_b, 
                      z=metric, 
                      xlab=group_a,
                      ylab=group_b,
                      title=None,
                      colour_scheme=colour_scheme,
                      slope_params=slope_params,
                      figsize=figsize)
    fig.tight_layout()
    return fig

def barplot(data: pd.DataFrame,
            x: str,
            y: str,
            xlab: str,
            ylab: str,
            title: str,
            figsize: Tuple[int, int]) -> Figure:
    fig, ax = plt.subplots(figsize=figsize)
    sns.barplot(data=data, x=x, y=y, ax=ax, legend=False)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    return fig

def heatmap(data: pd.DataFrame, 
            x: str,
            y: str,
            z: str,
            xlab: str,
            ylab: str,
            title: Optional[str],
            colour_scheme: str,
            figsize: Tuple[int, int],
            slope_params: Optional[Tuple[float, float, float]]) -> Figure:
    fig, ax = plt.subplots(figsize=figsize)
    hm_data = data.pivot(index=x, columns=y, values=z)
    params = {"cmap": colour_scheme,
              "annot": True,
              "fmt": ".3f",
              "ax": ax}
    if slope_params:
        if len(slope_params) < 3:
            raise TypeError(f"Malformed argument to `slope_params`; expected 3-tuple, got {slope_params}")
        params["norm"] = TwoSlopeNorm(vmin=slope_params[0], vcenter=slope_params[1], vmax=slope_params[2])
    sns.heatmap(hm_data, **params)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    return fig