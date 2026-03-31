import pandas as pd

import sompy._stats


def test_parse_samples(sompy_df: pd.DataFrame):
    df = sompy._stats.parse_samples(sompy_df)
    groups = ["a", "b", "c", "d", "e"]
    expected_truth_column = pd.Series(
        [f"truth_{group}" for group in groups], name="truth"
    )
    expected_query_column = pd.Series(
        [f"query_{group}" for group in groups], name="query"
    )
    assert df["truth"].equals(expected_truth_column)
    assert df["query"].equals(expected_query_column)
