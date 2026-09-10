"""Plots package: TimeSeriesPlotWidget and export presentation utilities."""
from .time_series_plot import TimeSeriesPlotWidget
from .export import (
    PlotPresentationDialog, PLOT_STYLE_OPTIONS, parse_plot_style,
    apply_pyqtgraph_curve_style, get_matplotlib_plot_kwargs,
    calculate_lowest_density_quadrant, calculate_percentile_limits,
    PUBLICATION_PRESETS
)

__all__ = [
    "TimeSeriesPlotWidget",
    "PlotPresentationDialog",
    "PLOT_STYLE_OPTIONS",
    "parse_plot_style",
    "apply_pyqtgraph_curve_style",
    "get_matplotlib_plot_kwargs",
    "calculate_lowest_density_quadrant",
    "calculate_percentile_limits",
    "PUBLICATION_PRESETS"
]
