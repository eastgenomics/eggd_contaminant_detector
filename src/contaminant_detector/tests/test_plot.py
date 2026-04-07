import pytest
from pytest_mock import MockerFixture
import pandas as pd

import contaminant_detector._plot as plot


def test_heatmap(snv_df_plus_names: pd.DataFrame) -> None:
    fig = plot.heatmap(
        data=snv_df_plus_names,
        x="contaminated_samples",
        y="candidates",
        z="recall",
        xlab="contaminated samples",
        ylab="candidates",
        title="some test title",
        colour_scheme="YlOrRd",
        slope_params=(0.0, 0.4, 1.0),
        figsize=(10, 6),
    )

    ax = fig.axes[0]

    x_ticks = [t.get_text() for t in ax.get_xticklabels()]
    cand_labels = [
        "260101S0010-26TSOD01",
        "260101S0011-26TSOD01",
        "260101S0012-26TSOD01",
    ]
    for lab in cand_labels:
        assert any(lab in str(tick) for tick in x_ticks)

    y_ticks = [t.get_text() for t in ax.get_yticklabels()]
    contam_labels = ["260101S1111-25TSOD10", "260101S1112-25TSOD11"]
    for lab in contam_labels:
        assert any(lab in str(tick) for tick in y_ticks)


def test_barplot(snv_df_one_sample: pd.DataFrame) -> None:
    fig = plot.barplot(
        data=snv_df_one_sample,
        x="candidates",
        y="recall",
        xlab="candidates",
        ylab="contamination (recall)",
        title=str(snv_df_one_sample["contaminated_samples"].iloc[0]),
        figsize=(10, 6),
    )
    ax = fig.axes[0]
    x_ticks = [t.get_text() for t in ax.get_xticklabels()]
    cand_labels = [
        "260101S0010-26TSOD01",
        "260101S0011-26TSOD01",
        "260101S0012-26TSOD01",
    ]
    for lab in cand_labels:
        assert any(lab in str(tick) for tick in x_ticks)


def test_generate_heatmap_trigger(
    snv_df_plus_names: pd.DataFrame, mocker: MockerFixture
) -> None:
    mock_figobj = mocker.MagicMock()
    mock_heatmap = mocker.patch("contaminant_detector._plot.heatmap")
    mock_heatmap.return_value = mock_figobj

    mocker.patch("contaminant_detector._plot.barplot")

    fig = plot._generate_comparison_plot(snv_df_plus_names, metric="recall")

    mock_heatmap.assert_called_once()
    assert fig == mock_figobj


def test_generate_barplot_trigger(
    snv_df_one_sample: pd.DataFrame, mocker: MockerFixture
) -> None:
    mock_figobj = mocker.MagicMock()
    mock_barplot = mocker.patch("contaminant_detector._plot.barplot")
    mock_barplot.return_value = mock_figobj

    mocker.patch("contaminant_detector._plot.heatmap")

    fig = plot._generate_comparison_plot(snv_df_one_sample, metric="recall")

    mock_barplot.assert_called_once()
    assert fig == mock_figobj
