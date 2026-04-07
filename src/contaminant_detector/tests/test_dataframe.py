import pytest
import pandas as pd

import contaminant_detector._dataframe


def test_parse_samples(abstract_sompy_df: pd.DataFrame) -> None:
    df = contaminant_detector._dataframe.parse_samples(abstract_sompy_df)
    groups = ["a", "b", "c", "d", "e"]
    expected_truth_column = pd.Series(
        [f"truth_{group}" for group in groups], name="truth"
    )
    expected_query_column = pd.Series(
        [f"query_{group}" for group in groups], name="query"
    )
    assert df["truth"].equals(expected_truth_column)
    assert df["query"].equals(expected_query_column)


def test_shorten() -> None:
    epic_name = "123456789-26001Z0001-26NGSHO01-1234-U-98765432"
    epic_name_shortened = "26001Z0001-26NGSHO01"
    non_epic_name = "haemonc_sim_HCC1187"

    assert contaminant_detector._dataframe.shorten(epic_name) == epic_name_shortened
    assert contaminant_detector._dataframe.shorten(non_epic_name) == non_epic_name


def test_get_sample_name_truth(sompy_snv_df: pd.DataFrame) -> None:
    sompycmd = str(sompy_snv_df["sompycmd"].loc[0])
    expected_truth = "123456789-260101S1111-25TSOD10-4321-M"
    actual_truth = contaminant_detector._dataframe.get_sample_name(sompycmd, "truth")
    assert expected_truth == actual_truth


def test_get_sample_name_query(sompy_snv_df: pd.DataFrame) -> None:
    sompycmd = str(sompy_snv_df["sompycmd"].loc[0])
    expected_query = "123456789-260101S0010-26TSOD01-1234-M"
    actual_query = contaminant_detector._dataframe.get_sample_name(sompycmd, "query")
    assert expected_query == actual_query
