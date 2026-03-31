import pandas as pd

from . import _paths


def parse_samples(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts truth and query sample names from a DataFrame of stats.csv data,
    adding "truth" and "query" columns with the simplified sample names. For example,
    rows where the truth sample is listed as "/in/test/sampleA.vcf.gz" in `sompycmd`
    will be stored in the `truth` column as "sampleA".

    Args:
        df: A pandas DataFrame containing a 'sompycmd' column.

    Returns:
        The sompy DataFrame with the 'truth' and 'query' columns replaced by
        'truth' and 'query' columns showing the base sample name minus the file path
        and suffix (e.g.: "/in/test/test.vcf.gz" -> "test")
    """
    vcf_pattern = r"[^\s]+\.(?:g\.)?g?vcf(?:\.gz)?"
    matches = df["sompycmd"].str.findall(vcf_pattern)
    df["truth"] = matches.str[0].apply(_paths._remove_vcf_extension)
    df["query"] = matches.str[1].apply(_paths._remove_vcf_extension)
    return df
