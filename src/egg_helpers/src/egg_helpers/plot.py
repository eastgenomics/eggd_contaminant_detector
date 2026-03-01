#!/usr/bin/env python

from typing import Tuple

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from matplotlib.figure import Figure

def generate_comparison_plot(df: pd.DataFrame, 
                             group_a: str,
                             group_b: str,
                             metric: str,
                             xlab: str,
                             ylab: str,
                             title: str,
                             colour_scheme: str="YlOrRd",
                             slope_params: Tuple[int, int, int]=None,
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
                      xlab=xlab,
                      ylab=ylab,
                      title=title,
                      figsize=figsize)
    else:
        fig = heatmap(data=df, 
                      x=group_a, 
                      y=group_b, 
                      z=metric, 
                      xlab=xlab,
                      ylab=ylab,
                      title=title,
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
            title: str,
            colour_scheme: str,
            figsize: Tuple[int, int],
            slope_params: Tuple[int, int, int]) -> Figure:
    fig, ax = plt.subplots(figsize=figsize)
    hm_data = data.pivot(index=x, columns=y, values=z)
    if slope_params:
        if len(slope_params) == 3:
            norm = TwoSlopeNorm(vmin=slope_params[0], vcenter=slope_params[1], vmax=slope_params[2])
            sns.heatmap(hm_data, annot=True, fmt=".3f", norm=norm, cmap=colour_scheme, ax=ax)
        else:
            raise TypeError("wrong slope parameter format. It's a 3-tuple of vmin, vcenter and vmax.")
    else:
        sns.heatmap(hm_data, annot=True, fmt=".3f", cmap=colour_scheme, ax=ax)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    return fig