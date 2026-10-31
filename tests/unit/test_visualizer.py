"""Unit tests for the EDAVisualizer module."""

from pathlib import Path
from dataset.visualizer import EDAVisualizer


def test_visualizer_initialization():
    """Verify visualizer initializes with active dataset."""
    vis = EDAVisualizer()
    assert len(vis.df) == 12000
    assert vis.output_dir.exists()


def test_plot_individual_charts(tmp_path: Path):
    """Verify individual chart generation methods create valid non-empty image files."""
    vis = EDAVisualizer(output_dir=tmp_path)

    amount_fig = vis.plot_amount_distribution()
    assert amount_fig.exists()
    assert amount_fig.stat().st_size > 15000  # Non-trivial PNG

    fraud_fig = vis.plot_fraud_vs_legit_distribution()
    assert fraud_fig.exists()
    assert fraud_fig.stat().st_size > 15000

    corr_fig = vis.plot_correlation_heatmap()
    assert corr_fig.exists()
    assert corr_fig.stat().st_size > 15000


def test_generate_all_visualisations(tmp_path: Path):
    """Verify that batch generation creates all 8 figures."""
    vis = EDAVisualizer(output_dir=tmp_path)
    saved = vis.generate_all_visualisations()

    assert len(saved) == 8
    for p in saved:
        assert p.exists()
        assert p.suffix == ".png"
        assert p.stat().st_size > 10000
