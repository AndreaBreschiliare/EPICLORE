"""
Shared UI Components for World Architect Pro Panels.
Promotes DRY and consistent "Modern Site Style".
"""

import streamlit as st
import pandas as pd
from typing import Any, Optional, List, Dict, Callable
import time

# ==============================================================================
# STYLING CONSTANTS
# ==============================================================================
METRIC_CSS = """
<style>
    div[data-testid="stMetric"] {
        background-color: #1f2937;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #374151;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    div[data-testid="stMetric"]:hover {
        border-color: #e6c200;
    }
</style>
"""

# ==============================================================================
# COMPONENT FUNCTIONS
# ==============================================================================

def apply_metric_style():
    """Injects custom CSS for metrics."""
    st.markdown(METRIC_CSS, unsafe_allow_html=True)

def render_metric_card(
    label: str,
    value: Any,
    delta: Optional[str] = None,
    help_text: Optional[str] = None,
    col: Any = None
):
    """
    Renders a consistent metric card.
    Args:
        label: The title of the metric.
        value: The value to display.
        delta: Optional change indicator.
        help_text: Optional tooltip.
        col: Streamlit column object (optional). If None, uses st.
    """
    container = col if col else st
    container.metric(label=label, value=value, delta=delta, help=help_text)

def render_connection_sidebar(
    title: str,
    connected: bool,
    base_url: str,
    auto_refresh_enabled: bool,
    refresh_interval: int,
    help_text: str = ""
):
    """
    Renders the connection status and settings in the sidebar.
    """
    with st.sidebar:
        st.subheader(f"🔌 {title}")

        if connected:
            st.success("✅ Online")
        else:
            st.error("❌ Offline")
            st.caption(f"Target: `{base_url}`")
            if help_text:
                st.info(help_text)

        st.divider()

        if auto_refresh_enabled:
            st.checkbox(
                "🔄 Auto-Refresh",
                value=st.session_state.get(f"auto_refresh_{title}", True),
                key=f"auto_refresh_{title}",
                help=f"Updates every {refresh_interval}s"
            )

def handle_auto_refresh(key_suffix: str, interval: int):
    """
    Handles the auto-refresh logic.
    """
    if st.session_state.get(f"auto_refresh_{key_suffix}", False):
        time.sleep(interval)
        st.rerun()

def render_header_with_refresh(title: str, subtitle: str, on_refresh: Callable[[], None]):
    """
    Renders a page header with a refresh button aligned to the right.
    """
    c1, c2 = st.columns([5, 1])
    with c1:
        st.title(title)
        st.markdown(f"*{subtitle}*")
    with c2:
        st.write("") # Spacer
        if st.button("🔄 Refresh", key=f"btn_refresh_{title.lower().replace(' ', '_')}", use_container_width=True):
            on_refresh()

def render_dataframe_with_search(
    df: pd.DataFrame,
    search_col: str,
    widget_id: str,
    placeholder: str = "Search...",
    column_config: Dict = None
):
    """
    Renders a dataframe with a standardized search bar.

    Args:
        df: The DataFrame to display.
        search_col: The column name to search within.
        widget_id: A unique string identifier for the widgets (prevents DuplicateWidgetID error).
        placeholder: Text for search input.
        column_config: Streamlit column configuration.
    """
    if df.empty:
        st.info("No data available.")
        return

    search_term = st.text_input(
        f"🔍 Filter",
        placeholder=placeholder,
        key=f"search_{widget_id}"
    )

    if search_term:
        # Case insensitive partial match
        filtered_df = df[df[search_col].astype(str).str.contains(search_term, case=False, na=False)]
    else:
        filtered_df = df

    st.dataframe(
        filtered_df,
        use_container_width=True,
        column_config=column_config
    )
    return filtered_df
