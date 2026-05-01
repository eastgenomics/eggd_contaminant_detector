import pandas as pd
from . import _fs


def set_sample_names(sompy_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts sample names from sompycmd field, and stores the result in new
    fields - this will be stored in the "contaminated_samples" or "candidates"
    fields for truth and query samples respectively. Names will be shortened
    if they conform to the EPIC sample name format.
    """
    sompy_df["contaminated_samples"] = (
        sompy_df["sompycmd"].apply(get_sample_name, sample="truth").apply(shorten)
    )
    sompy_df["candidates"] = (
        sompy_df["sompycmd"].apply(get_sample_name, sample="query").apply(shorten)
    )
    return sompy_df


def get_sample_name(sompycmd: str, sample: str = "truth") -> str:
    """Parses the sompycmd field for the truth or query VCF paths"""
    parts = sompycmd.split(" ")
    if sample == "truth":
        vcf_path = parts[-2]
    elif sample == "query":
        vcf_path = parts[-1]
    else:
        raise ValueError("Invalid key to `sample`: pick one of `truth`, `query`")

    vcf = vcf_path.split("/")[-1]
    sample_name = _fs.remove_vcf_extension(vcf)
    return sample_name


def shorten(name: str) -> str:
    """Shortens the sample name if stored in EPIC format"""
    parts = name.split("-")
    if len(parts) >= 3:
        return f"{parts[1]}-{parts[2]}"
    return name
