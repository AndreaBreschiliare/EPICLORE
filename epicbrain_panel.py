"""
EpicBrain Panel - UO Server Control Panel
Refactored for Clean Code, DRY, and Modern Style.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List

from epicbrain_client import EpicBrainClient
from epicbrain_config import (
    MAX_LOCATIONS_DISPLAY, 
    MIN_INTERACTIONS_NETWORK,
    CHART_HEIGHT,
    CHART_THEME,
    AUTO_REFRESH_ENABLED,
    REFRESH_INTERVAL
)
import ui_components as ui

# ==============================================================================
# SUB-RENDERERS (Single Responsibility Principle)
# ==============================================================================

def _render_executive_metrics(metrics: Dict[str, Any]):
    """Renders the top row metrics for the dashboard."""
    c1, c2, c3, c4 = st.columns(4)
    
    ui.render_metric_card(
        "Active Players",
        metrics.get('active_today', 0),
        help_text="Unique players in period",
        col=c1
    )
    ui.render_metric_card(
        "Peak Activity",
        f"{metrics.get('peak_players', 0)} ({metrics.get('peak_hour', 'N/A')})",
        help_text="Max concurrent players",
        col=c2
    )
    ui.render_metric_card(
        "Avg Session",
        metrics.get('avg_session_duration', 'N/A'),
        help_text="Average play time",
        col=c3
    )
    ui.render_metric_card(
        "Total Logs",
        metrics.get('total_logs', 0),
        help_text="Processed log entries",
        col=c4
    )

def _render_alerts_section(alerts_data: Dict[str, Any]):
    """Renders the system alerts section."""
    alerts = alerts_data.get('alerts', [])
    if not alerts:
        return

    st.subheader("🚨 System Alerts")
    for alert in alerts:
        severity = alert.get('severity', 'info')
        msg = alert.get('message', '')

        if severity == 'high':
            st.error(f"🔴 {msg}")
        elif severity == 'medium':
            st.warning(f"🟡 {msg}")
        else:
            st.info(f"🔵 {msg}")
    st.divider()

def _render_top_locations_chart(location_metrics: Dict[str, Any]):
    """Renders the bar chart for top locations."""
    if not location_metrics or not location_metrics.get('top_locations'):
        st.info("No location data available.")
        return

    df = pd.DataFrame(location_metrics['top_locations'])
    fig = px.bar(
        df, x='visits', y='name', orientation='h',
        title=f"Top {len(df)} Visited Locations",
        labels={'visits': 'Visits', 'name': 'Location'},
        color='unique_players', color_continuous_scale='Viridis'
    )
    fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
    st.plotly_chart(fig, use_container_width=True)

def _render_activity_chart(activity_metrics: Dict[str, Any]):
    """Renders the line chart for hourly activity."""
    if not activity_metrics or not activity_metrics.get('hourly'):
        st.info("No activity data available.")
        return

    df = pd.DataFrame(activity_metrics['hourly'])
    fig = px.line(
        df, x='hour', y='players',
        title="Hourly Activity",
        labels={'hour': 'Hour', 'players': 'Players'},
        markers=True
    )
    fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
    st.plotly_chart(fig, use_container_width=True)

def _render_network_graph(network_data: Dict[str, Any]):
    """Renders the social network graph using Plotly."""
    if not network_data or not network_data.get('nodes') or not network_data.get('edges'):
        st.info("No network data available.")
        return

    nodes = network_data['nodes']
    edges = network_data['edges']
    
    # Edges
    edge_trace = []
    import math
    for edge in edges:
        # Simple circular layout simulation logic
        # In a real app, you might use networkx layout or similar
        source_idx = next((i for i, n in enumerate(nodes) if n['id'] == edge['source']), 0)
        target_idx = next((i for i, n in enumerate(nodes) if n['id'] == edge['target']), 0)
        
        angle_s = 2 * math.pi * source_idx / len(nodes)
        angle_t = 2 * math.pi * target_idx / len(nodes)
        
        x0, y0 = math.cos(angle_s), math.sin(angle_s)
        x1, y1 = math.cos(angle_t), math.sin(angle_t)

        edge_trace.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode='lines', line=dict(width=edge['weight']/5, color='#888'),
            hoverinfo='none', showlegend=False
        ))
    
    # Nodes
    node_x = [math.cos(2 * math.pi * i / len(nodes)) for i in range(len(nodes))]
    node_y = [math.sin(2 * math.pi * i / len(nodes)) for i in range(len(nodes))]
    node_text = [n['id'] for n in nodes]
    node_size = [n['size'] for n in nodes]
    
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers+text',
        text=node_text, textposition="top center",
        marker=dict(size=node_size, color='#1f77b4', line=dict(width=2, color='white')),
        hovertemplate='<b>%{text}</b><extra></extra>'
    )
    
    fig = go.Figure(data=edge_trace + [node_trace])
    fig.update_layout(
        title="Player Interaction Graph", showlegend=False, hovermode='closest',
        height=600, xaxis=dict(visible=False), yaxis=dict(visible=False),
        template=CHART_THEME
    )
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB RENDERERS
# ==============================================================================

def render_dashboard_tab(client: EpicBrainClient):
    """Executive Dashboard Tab."""
    st.header("📊 Executive Dashboard")
    
    # Controls
    c1, c2 = st.columns([3, 1])
    with c1:
        days = st.selectbox("Timeframe", [1, 7, 14, 30], index=1,
                            format_func=lambda x: f"Last {x} days" if x > 1 else "Today")
    with c2:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # Data Fetching
    p_metrics = client.get_player_metrics(days=days)
    l_metrics = client.get_location_metrics(limit=MAX_LOCATIONS_DISPLAY)
    alerts = client.get_alerts()
    a_metrics = client.get_activity_metrics(days=days)

    if not p_metrics:
        st.warning("⚠️ Unable to load metrics.")
        return

    # Rendering
    _render_executive_metrics(p_metrics)
    st.divider()
    _render_alerts_section(alerts)

    c_chart1, c_chart2 = st.columns(2)
    with c_chart1:
        st.subheader("📍 Top Locations")
        _render_top_locations_chart(l_metrics)
    with c_chart2:
        st.subheader("⏰ Activity Trends")
        _render_activity_chart(a_metrics)

    with st.expander("📋 Detailed Location Data"):
        if l_metrics and l_metrics.get('top_locations'):
            ui.render_dataframe_with_search(
                pd.DataFrame(l_metrics['top_locations']),
                search_col="name",
                widget_id="dash_locations",
                column_config={
                    "name": "Location",
                    "visits": st.column_config.NumberColumn("Visits", format="%d"),
                    "unique_players": st.column_config.NumberColumn("Unique Players", format="%d")
                }
            )

def render_activity_map_tab(client: EpicBrainClient):
    """Activity Map Tab."""
    st.header("🗺️ Activity Map")
    
    l_metrics = client.get_location_metrics(limit=50)
    if not l_metrics or not l_metrics.get('top_locations'):
        st.warning("No location data found.")
        return

    df = pd.DataFrame(l_metrics['top_locations'])
    
    # Logic
    max_visits = df['visits'].max()
    df['category'] = df['visits'].apply(
        lambda x: 'Popular' if x > max_visits * 0.6 else 'Average' if x > max_visits * 0.3 else 'Low'
    )
    
    # KPI Summary
    c1, c2, c3 = st.columns(3)
    ui.render_metric_card("🟢 Popular Zones", len(df[df['category'] == 'Popular']), col=c1)
    ui.render_metric_card("🟡 Average Zones", len(df[df['category'] == 'Average']), col=c2)
    ui.render_metric_card("🔴 Quiet Zones", len(df[df['category'] == 'Low']), col=c3)
    
    st.divider()
    
    # Charts
    st.subheader("📈 Distribution")
    fig = px.pie(df, values='visits', names='name', title="Visit Distribution", hole=0.4)
    fig.update_layout(height=500, template=CHART_THEME)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📋 All Locations")
    ui.render_dataframe_with_search(
        df, "name",
        widget_id="map_locations",
        column_config={
            "name": "Location",
            "visits": st.column_config.NumberColumn("Visits"),
            "category": st.column_config.SelectboxColumn("Category", options=['Popular', 'Average', 'Low'])
        }
    )

def render_social_insights_tab(client: EpicBrainClient):
    """Social Insights Tab."""
    st.header("💬 Social Insights")
    
    c1, c2 = st.columns([3, 1])
    min_int = c1.slider("Min Interactions", 1, 20, MIN_INTERACTIONS_NETWORK)
    if c2.button("🔄 Refresh", key="social_refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    s_metrics = client.get_social_metrics(min_interactions=min_int)
    net_data = client.get_network_graph(min_interactions=min_int)
    
    if not s_metrics:
        st.warning("No social data available.")
        return
        
    # Metrics
    c1, c2, c3 = st.columns(3)
    ui.render_metric_card("Unique Players", s_metrics.get('unique_players', 0), col=c1)
    ui.render_metric_card("Total Interactions", s_metrics.get('total_interactions', 0), col=c2)
    ui.render_metric_card("Strong Connections", len(s_metrics.get('interactions', [])),
                          help_text=f"Pairs with >{min_int} interactions", col=c3)

    st.divider()
    st.subheader("🕸️ Network Graph")
    _render_network_graph(net_data)
    
    st.divider()
    st.subheader("🤝 Top Interactions")
    interactions = s_metrics.get('interactions', [])
    if interactions:
        df = pd.DataFrame(interactions[:20])
        fig = px.bar(
            df, x='count',
            y=df.apply(lambda r: f"{r['player1']} ↔ {r['player2']}", axis=1),
            orientation='h', title="Top Interaction Pairs", labels={'x':'Count', 'y':'Pair'},
            color='count', color_continuous_scale='Blues'
        )
        fig.update_layout(height=500, template=CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No interactions match criteria.")

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def render_epicbrain_panel():
    """Main function to render the EpicBrain Panel."""
    ui.apply_metric_style()
    
    client = EpicBrainClient()
    connected = client.test_connection()
    
    # Clear Cache Logic (Manual)
    if st.session_state.get("clear_cache_trigger"):
        st.cache_data.clear()
        st.session_state.clear_cache_trigger = False
    
    def manual_refresh():
        st.session_state.clear_cache_trigger = True
        st.rerun()

    ui.render_header_with_refresh(
        "🧠 EpicBrain Panel",
        "Advanced Analytics & Monitoring",
        manual_refresh
    )

    ui.render_connection_sidebar(
        "Connection Status",
        connected,
        client.base_url,
        AUTO_REFRESH_ENABLED,
        REFRESH_INTERVAL,
        help_text="Check `epicbrain_config.py`"
    )

    tab1, tab2, tab3 = st.tabs(["📊 Executive", "🗺️ Activity Map", "💬 Social Insights"])
    
    with tab1:
        render_dashboard_tab(client)
    with tab2:
        render_activity_map_tab(client)
    with tab3:
        render_social_insights_tab(client)

    ui.handle_auto_refresh("Connection Status", REFRESH_INTERVAL)
