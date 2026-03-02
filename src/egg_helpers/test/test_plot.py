import pytest
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from egg_helpers.plot import generate_comparison_plot

@pytest.fixture
def barplot_df() -> pd.DataFrame:
    """Data with one Group A entry -> should trigger barplot."""
    return pd.DataFrame({
        "truth": ["T1", "T1"],
        "query":  ["Q1", "Q2"],
        "recall": [0.95, 0.80]
    })

@pytest.fixture
def heatmap_df() -> pd.DataFrame:
    """Data with multiple Group A entries -> should trigger heatmap."""
    return pd.DataFrame({
        "truth": ["T1", "T1", "T2", "T2"],
        "query":  ["Q1", "Q2", "Q1", "Q2"],
        "recall": [0.9, 0.4, 0.1, 0.8]
    })

def test_triggers_barplot_correctly(barplot_df: pd.DataFrame) -> None:
    fig = generate_comparison_plot(
        barplot_df, 
        group_a="truth",
        group_b="query", 
        metric="recall"
    )
    ax = fig.axes[0]
    
    # Assertions
    assert len(ax.patches) == 2  # Two bars drawn
    assert ax.get_title() == "T1"
    assert ax.get_ylabel() == "recall"
    
    plt.close(fig)

def test_triggers_heatmap_correctly(heatmap_df: pd.DataFrame) -> None:
    fig = generate_comparison_plot(
        heatmap_df, 
        group_a="truth",
        group_b="query", 
        metric="recall"
    )
    ax = fig.axes[0]
    
    # Heatmaps don't have patches; they have a QuadMesh in collections
    assert len(ax.collections) > 0 
    
    # Verify the axis labels match the data pivot
    yticklabels = [t.get_text() for t in ax.get_yticklabels()]
    assert "T1" in yticklabels
    assert "T2" in yticklabels
    
    plt.close(fig)

def test_two_slope_norm_application(heatmap_df: pd.DataFrame) -> None:
    params = (0, 0.4, 1.0)
    fig = generate_comparison_plot(
        heatmap_df,
        group_a="truth",
        group_b="query",
        metric="recall",
        slope_params=params
    )
    
    # Access the QuadMesh and check its norm
    mesh = fig.axes[0].collections[0]
    assert isinstance(mesh.norm, TwoSlopeNorm)
    assert mesh.norm.vcenter == 0.4
    
    plt.close(fig)

def test_invalid_slope_params_raises_error(heatmap_df: pd.DataFrame) -> None:
    invalid_slope_params = (0, 1)
    with pytest.raises(TypeError):
        generate_comparison_plot(
            heatmap_df,
            group_a="truth",
            group_b="query", 
            metric="recall",
            slope_params=invalid_slope_params
        )