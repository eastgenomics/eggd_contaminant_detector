#!/usr/bin/env python

import logging
import re
from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure


def process_sompy_data(
    input_path: Path, pattern: str = "*.stats.csv", output: str = "agg_sompy_data.csv") -> Path:
    """Aggregates multiple Sompy stats files into a single CSV.

    Reads all stats files matching the pattern, cleans up redundant index columns, 
    and saves the combined dataset to a specified path.

    Args:
        input_path: Directory containing the Sompy stats files.
        pattern: Glob pattern to identify the stats files. Defaults to "*.stats.csv".
        output: Filename for the aggregated CSV. Defaults to "agg_sompy_data.csv".

    Returns:
        Path: The absolute path to the saved aggregate CSV.
    """
    df = read_sompy_stats(input_path, pattern)
    ## First column is unnamed in sompy output for some reason.
    ## It's the row index, but it's per file so it repeats [0,1,2]
    ## and is therefore useless to us
    df.drop(df.columns[0], axis=1, inplace=True)
    output_path = Path(output)
    df.to_csv(output_path)
    return output_path


def read_sompy_stats(path: Path, pattern: str) -> pd.DataFrame:
    """Discovers and concatenates all Sompy stats files in a path.

    Args:
        path: Path object pointing to the directory to search.
        pattern: Glob pattern to match files.

    Returns:
        pd.DataFrame: A single DataFrame containing data from all matched files.
    """
    files = path.glob(pattern)
    df = pd.concat([read_sompy_df(f) for f in files])
    return df


def read_sompy_df(file: Path) -> pd.DataFrame:
    """Reads a single Sompy CSV and injects sample metadata.

    Args:
        file: Path to a Sompy .stats.csv file.

    Returns:
        pd.DataFrame: DataFrame containing stats plus 'truth' and 'query' metadata.
    """
    df = pd.read_csv(file)
    df = add_truth_and_query_columns(df)
    return df


def add_truth_and_query_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Parses the 'sompycmd' column to extract and add sample names.

    Sompy embeds the original file paths in the 'sompycmd' column. This function
    extracts the truth and query filenames and parses them into clean sample names.

    Args:
        df: A DataFrame containing a 'sompycmd' column.

    Returns:
        pd.DataFrame: The modified DataFrame with added 'truth' and 'query' columns.
    """
    sompycmd = df["sompycmd"][0].split(" ")
    truth = parse_sample_name(sompycmd[1].split("/")[-1])
    query = parse_sample_name(sompycmd[2].split("/")[-1])
    df["truth"] = truth
    df["query"] = query
    return df


def parse_sample_name(query: str) -> str:
    """Extracts a specific EPIC sample name pattern from a string.

    The pattern looks for IDs like '123-456A7-89B...'. If the pattern isn't found,
    the function falls back to the full string.

    Args:
        query: The string (usually a filename) containing the sample name.

    Returns:
        str: The extracted sample name or the original string if no match.
    """
    pattern = r"\d+-\d+\w\d+-\d+\w+\d+-\d+-\w"
    try:
        sample_name = re.findall(pattern, query)[0]
    except IndexError:
        logging.warning(
            f"Could not parse EPIC sample name from {query}; defaulting to full filename"
        )
        return query
    else:
        return sample_name


def plot_snv_recall(sompy_data: Path) -> Path:
    """Loads aggregated Sompy data and generates a recall visualization.

    Args:
        sompy_data: Path to the aggregated CSV file.

    Returns:
        Path: Path to the saved visualization image (snv_recall.png).
    """
    df = pd.read_csv(sompy_data)
    plot = generate_plot(df)
    plot.savefig("snv_recall.png")
    return Path("snv_recall.png")


def generate_plot(df: pd.DataFrame) -> Figure:
    """Creates a visualization of SNV recall metrics.

    If the data contains only one truth sample, a barplot is generated.
    If multiple truth samples are present, it generates a heatmap of
    truth vs. query samples.

    Args:
        df: Aggregated Sompy DataFrame.

    Returns:
        Figure: Matplotlib figure containing the generated plot.
    """
    snv_recall = df[df["type"] == "SNVs"]
    if snv_recall["truth"].nunique() == 1:
        ax = sns.barplot(snv_recall, x="query", y="recall")
    else:
        hm_data = snv_recall.pivot(index="truth", columns="query", values="recall")
        ax = sns.heatmap(hm_data, annot=True)
    return ax.get_figure()
