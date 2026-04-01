import pytest
import pandas as pd
import contaminant_detector._run
from pathlib import Path


def test_plot_recall(sompy_csv_dir: Path, tmp_path: Path) -> None:
    sompy_files = [f for f in sompy_csv_dir.glob("*.stats.csv")]
    sompy_csv, recall_plot = contaminant_detector._run.plot_recall(
        sompy_files, tmp_path / "out"
    )
    df = pd.read_csv(sompy_csv)
    assert len(df) == 6
    assert recall_plot.is_file()
    assert recall_plot.exists()
