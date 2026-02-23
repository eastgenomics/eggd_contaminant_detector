#!/usr/bin/env python

import logging
import re
from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure


def process_sompy_data(
    input_path: Path, pattern: str = "*.stats.csv", output: str = "agg_sompy_data.csv"
) -> Path:
    df = read_sompy_stats(input_path, pattern)
    ## First column is unnamed in sompy output for some reason.
    ## It's the row index, but it's per file so it repeats [0,1,2]
    ## and is therefore useless to us
    df.drop(df.columns[0], axis=1, inplace=True)
    output_path = Path(output)
    df.to_csv(output_path)
    return output_path


def read_sompy_stats(path: Path, pattern: str) -> pd.DataFrame:
    files = path.glob(pattern)
    df = pd.concat([read_sompy_df(file) for file in files])
    return df


def read_sompy_df(file: Path) -> pd.DataFrame:
    df = pd.read_csv(file)
    df = add_truth_and_query_columns(df)
    return df


def add_truth_and_query_columns(df: pd.DataFrame) -> pd.DataFrame:
    sompycmd = df["sompycmd"][0].split(" ")
    truth = parse_sample_name(sompycmd[1].split("/")[-1])
    query = parse_sample_name(sompycmd[2].split("/")[-1])
    df["truth"] = truth
    df["query"] = query
    return df


def parse_sample_name(query: str) -> str:
    pattern = r"\d+-\d+\w\d+-\d+\w+\d+-\d+-\w"
    try:
        sample_name = re.findall(pattern, query)[0]
    except IndexError:
        logging.warn(
            f"Could not parse EPIC sample name from {query}; defaulting to full filename"
        )
        return query
    else:
        return sample_name


def plot_snv_recall(sompy_data: Path) -> Path:
    df = pd.read_csv(sompy_data)
    plot = generate_plot(df)
    plot.savefig("snv_recall.png")
    return Path("snv_recall.png")


def generate_plot(df: pd.DataFrame) -> Figure:
    snv_recall = df[df["type"] == "SNVs"]
    if snv_recall["truth"].nunique() == 1:
        ax = sns.barplot(snv_recall, x="query", y="recall")
    else:
        hm_data = snv_recall.pivot(index="truth", columns="query", values="recall")
        ax = sns.heatmap(hm_data, annot=True)
    return ax.get_figure()
