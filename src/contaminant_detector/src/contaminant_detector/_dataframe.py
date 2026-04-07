import pandas as pd
from . import _fs


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
    df["truth"] = matches.str[0].apply(_fs.remove_vcf_extension)
    df["query"] = matches.str[1].apply(_fs.remove_vcf_extension)
    return df


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
