"""
schema_plots.py
===============
Renders Plotly charts declared under the optional ``plots`` key in a model
schema.  All chart types read their data from the prediction results that the
calling tab already has in memory -- no additional model calls are made here.

Supported chart types (``type`` field in each plot descriptor):
    bar          -- vertical bar chart, one bar per label
    horizontal_bar -- horizontal bar chart
    gauge        -- single-value gauge (good for scores / percentages)
    scatter      -- scatter / bubble chart (requires x + y columns in batch results)
    histogram    -- distribution histogram for a single column
    line         -- line chart over an ordered sequence

Each plot descriptor may include:
    type         (required) one of the types above
    title        (optional) chart title
    x_field      (optional) field name for x-axis (from raw_input or result)
    y_field      (optional) field name for y-axis
    color_field  (optional) field name used for color grouping
    value_field  (optional) for gauge: the numeric field to display
    min_val      (optional) for gauge: minimum of the gauge scale (default 0)
    max_val      (optional) for gauge: maximum (default auto from data)
    label        (optional) axis / series label
    height       (optional) chart height in pixels (default 350)

Context passed to each renderer:
    result_value   -- the scalar prediction (float)
    raw_input      -- dict of user inputs {field_name: value}
    batch_df       -- pd.DataFrame (batch mode only, None otherwise)
    schema_fields  -- the fields list from schema, for label lookups

This module is purely additive.  Removing it (and the ``plots`` key from
schema files) leaves all existing behaviour unchanged.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Any


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_schema_plots(
    plots: list[dict],
    result_value: float | None = None,
    raw_input: dict[str, Any] | None = None,
    batch_df: pd.DataFrame | None = None,
    schema_fields: list[dict] | None = None,
) -> None:
    """
    Iterate over all plot descriptors in ``plots`` and render each one.

    Parameters
    ----------
    plots         : List of plot descriptor dicts from schema[``plots``].
    result_value  : Scalar prediction value (may be None in batch-only mode).
    raw_input     : Dict of the most recent single-row user inputs.
    batch_df      : DataFrame with batch prediction results (or None).
    schema_fields : ``schema[``fields``]`` list, used for human-readable labels.
    """
    if not plots:
        return

    raw_input     = raw_input     or {}
    schema_fields = schema_fields or []

    field_label_map = {
        f["name"]: f.get("label", f["name"]) for f in schema_fields
    }

    for descriptor in plots:
        chart_type = descriptor.get("type", "").lower()
        try:
            _render_single_plot(
                descriptor    = descriptor,
                chart_type    = chart_type,
                result_value  = result_value,
                raw_input     = raw_input,
                batch_df      = batch_df,
                field_label_map = field_label_map,
            )
        except Exception as exc:
            st.caption(f"Could not render chart '{descriptor.get('title', chart_type)}': {exc}")


# ---------------------------------------------------------------------------
# Internal dispatcher
# ---------------------------------------------------------------------------

def _render_single_plot(
    descriptor: dict,
    chart_type: str,
    result_value: float | None,
    raw_input: dict,
    batch_df: pd.DataFrame | None,
    field_label_map: dict,
) -> None:
    height  = int(descriptor.get("height", 350))
    title   = descriptor.get("title", "")

    if chart_type == "gauge":
        _render_gauge(descriptor, result_value, raw_input, title, height)

    elif chart_type == "bar":
        _render_bar(descriptor, result_value, raw_input, batch_df, field_label_map, title, height, horizontal=False)

    elif chart_type == "horizontal_bar":
        _render_bar(descriptor, result_value, raw_input, batch_df, field_label_map, title, height, horizontal=True)

    elif chart_type == "scatter":
        _render_scatter(descriptor, batch_df, field_label_map, title, height)

    elif chart_type == "histogram":
        _render_histogram(descriptor, batch_df, field_label_map, title, height)

    elif chart_type == "line":
        _render_line(descriptor, batch_df, field_label_map, title, height)

    else:
        st.caption(f"Unsupported chart type: '{chart_type}'")


# ---------------------------------------------------------------------------
# Gauge
# ---------------------------------------------------------------------------

def _render_gauge(
    descriptor: dict,
    result_value: float | None,
    raw_input: dict,
    title: str,
    height: int,
) -> None:
    """Single-value gauge. Uses result_value by default or a named raw_input field."""
    value_field = descriptor.get("value_field")

    if value_field:
        val = float(raw_input.get(value_field, 0))
    elif result_value is not None:
        val = float(result_value)
    else:
        st.caption("Gauge requires either value_field or a scalar prediction result.")
        return

    min_val = float(descriptor.get("min_val", 0))
    max_val = descriptor.get("max_val")
    if max_val is None:
        max_val = max(val * 1.5, 1.0)
    max_val = float(max_val)

    label = descriptor.get("label", title or "Value")

    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = val,
        title = {"text": label},
        gauge = {
            "axis": {"range": [min_val, max_val]},
            "bar":  {"color": "#4F8EF7"},
            "steps": [
                {"range": [min_val, max_val * 0.33], "color": "#1E293B"},
                {"range": [max_val * 0.33, max_val * 0.66], "color": "#334155"},
                {"range": [max_val * 0.66, max_val], "color": "#475569"},
            ],
            "threshold": {
                "line":  {"color": "#60A5FA", "width": 3},
                "thickness": 0.75,
                "value": val,
            },
        },
    ))
    fig.update_layout(
        title_text    = title,
        height        = height,
        paper_bgcolor = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Bar / horizontal bar
# ---------------------------------------------------------------------------

def _render_bar(
    descriptor: dict,
    result_value: float | None,
    raw_input: dict,
    batch_df: pd.DataFrame | None,
    field_label_map: dict,
    title: str,
    height: int,
    horizontal: bool,
) -> None:
    """
    Bar chart.  Two data sources are supported:

    1. batch_df mode -- x_field and y_field point to columns in batch_df.
       Groups by x_field, aggregates y_field (mean by default).

    2. single-result mode -- ``bars`` key in descriptor is a list of
       {label, field} dicts where field maps to a raw_input value or
       ``__result__`` maps to result_value.
    """
    bars_spec = descriptor.get("bars")
    x_field   = descriptor.get("x_field")
    y_field   = descriptor.get("y_field")
    label     = descriptor.get("label", y_field or "Value")

    if batch_df is not None and x_field and y_field:
        if x_field not in batch_df.columns or y_field not in batch_df.columns:
            st.caption(f"Bar chart fields '{x_field}' / '{y_field}' not found in batch results.")
            return

        agg = batch_df.groupby(x_field, as_index=False)[y_field].mean()
        agg = agg.sort_values(y_field, ascending=False)

        x_label = field_label_map.get(x_field, x_field)
        y_label = field_label_map.get(y_field, y_field)

        if horizontal:
            fig = px.bar(
                agg, x=y_field, y=x_field, orientation="h",
                title=title, labels={y_field: y_label, x_field: x_label},
                color_discrete_sequence=["#4F8EF7"],
            )
        else:
            fig = px.bar(
                agg, x=x_field, y=y_field,
                title=title, labels={y_field: y_label, x_field: x_label},
                color_discrete_sequence=["#4F8EF7"],
            )

    elif bars_spec and result_value is not None:
        labels = []
        values = []
        for bar in bars_spec:
            lbl = bar.get("label", bar.get("field", ""))
            fld = bar.get("field", "")
            if fld == "__result__":
                val = result_value
            else:
                val = float(raw_input.get(fld, 0))
            labels.append(lbl)
            values.append(val)

        df_bar = pd.DataFrame({"label": labels, "value": values})
        if horizontal:
            fig = px.bar(df_bar, x="value", y="label", orientation="h",
                         title=title, labels={"value": label, "label": ""},
                         color_discrete_sequence=["#4F8EF7"])
        else:
            fig = px.bar(df_bar, x="label", y="value",
                         title=title, labels={"value": label, "label": ""},
                         color_discrete_sequence=["#4F8EF7"])

    else:
        st.caption("Bar chart requires either batch results or a 'bars' spec in the schema.")
        return

    fig.update_layout(
        height        = height,
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Scatter
# ---------------------------------------------------------------------------

def _render_scatter(
    descriptor: dict,
    batch_df: pd.DataFrame | None,
    field_label_map: dict,
    title: str,
    height: int,
) -> None:
    if batch_df is None:
        st.caption("Scatter chart requires batch results.")
        return

    x_field     = descriptor.get("x_field")
    y_field     = descriptor.get("y_field")
    color_field = descriptor.get("color_field")
    size_field  = descriptor.get("size_field")

    if not x_field or not y_field:
        st.caption("Scatter chart requires x_field and y_field.")
        return

    missing = [f for f in [x_field, y_field] if f not in batch_df.columns]
    if missing:
        st.caption(f"Scatter chart fields not found in batch results: {missing}")
        return

    x_label = field_label_map.get(x_field, x_field)
    y_label = field_label_map.get(y_field, y_field)

    kwargs: dict = dict(
        x=x_field, y=y_field, title=title,
        labels={x_field: x_label, y_field: y_label},
        opacity=0.7,
    )
    if color_field and color_field in batch_df.columns:
        kwargs["color"] = color_field
    if size_field and size_field in batch_df.columns:
        kwargs["size"] = size_field

    fig = px.scatter(batch_df, **kwargs)
    fig.update_layout(
        height        = height,
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Histogram
# ---------------------------------------------------------------------------

def _render_histogram(
    descriptor: dict,
    batch_df: pd.DataFrame | None,
    field_label_map: dict,
    title: str,
    height: int,
) -> None:
    if batch_df is None:
        st.caption("Histogram requires batch results.")
        return

    x_field = descriptor.get("x_field")
    if not x_field or x_field not in batch_df.columns:
        st.caption(f"Histogram field '{x_field}' not found in batch results.")
        return

    x_label = field_label_map.get(x_field, x_field)
    fig = px.histogram(
        batch_df, x=x_field, nbins=int(descriptor.get("bins", 30)),
        title=title, labels={x_field: x_label},
        color_discrete_sequence=["#4F8EF7"],
    )
    fig.update_layout(
        height        = height,
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Line
# ---------------------------------------------------------------------------

def _render_line(
    descriptor: dict,
    batch_df: pd.DataFrame | None,
    field_label_map: dict,
    title: str,
    height: int,
) -> None:
    if batch_df is None:
        st.caption("Line chart requires batch results.")
        return

    x_field     = descriptor.get("x_field")
    y_field     = descriptor.get("y_field")
    color_field = descriptor.get("color_field")

    if not x_field or not y_field:
        st.caption("Line chart requires x_field and y_field.")
        return

    missing = [f for f in [x_field, y_field] if f not in batch_df.columns]
    if missing:
        st.caption(f"Line chart fields not found in batch results: {missing}")
        return

    x_label = field_label_map.get(x_field, x_field)
    y_label = field_label_map.get(y_field, y_field)

    kwargs: dict = dict(
        x=x_field, y=y_field, title=title,
        labels={x_field: x_label, y_field: y_label},
    )
    if color_field and color_field in batch_df.columns:
        kwargs["color"] = color_field

    fig = px.line(batch_df, **kwargs)
    fig.update_layout(
        height        = height,
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font_color    = "#CBD5E1",
    )
    st.plotly_chart(fig, use_container_width=True)
