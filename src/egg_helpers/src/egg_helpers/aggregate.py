import pandas as pd
from pathlib import Path

def read_csvs(path: Path, pattern: str) -> pd.DataFrame:
    """Discovers and concatenates all CSV files in a path.

    Args:
        path: Path object pointing to the directory to search.
        pattern: Glob pattern to match files.

    Returns:
        pd.DataFrame: A single DataFrame containing data from all matched files.
    """
    files = path.glob(pattern)
    df = pd.concat([pd.read_csv(f) for f in files])
    return df