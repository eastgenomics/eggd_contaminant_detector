#!/usr/bin/env python

import logging
import re
import pandas as pd
import seaborn as sns
from pathlib import Path

def read_sompy_df(file):
    df = pd.read_csv(file)
    df = add_truth_and_query_columns(df)
    return df

def add_truth_and_query_columns(df):
    sompycmd = df["sompycmd"][0].split(" ")
    truth = parse_sample_name(sompycmd[1].split("/")[-1])
    query = parse_sample_name(sompycmd[2].split("/")[-1])
    df["truth"] = truth
    df["query"] = query
    return df

def parse_sample_name(query):
    pattern = r'\d+-\d+\w\d+-\d+\w+\d+-\d+-\w'
    try:
        sample_name = re.findall(pattern, query)[0]
    except IndexError:
        logging.warn(f"Could not parse EPIC sample name from {query}; defaulting to full filename")
        return query
    else:
        return sample_name

def plot_snv_recall(df):
    snv_recall = df[df["type"] == "SNVs"]
    if len(snv_recall["truth"].unique()) == 1:
        plot = sns.barplot(snv_recall, x="query", y="recall")
    else:
        hm_data = snv_recall.pivot(index="truth", columns="query", values="recall")
        plot = sns.heatmap(hm_data)
    return plot
