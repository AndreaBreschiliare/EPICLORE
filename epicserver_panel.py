"""
Epic Server Panel - POL Server Manager
Refactored for Clean Code, DRY, and Modern Style.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List

from epicserver_client import EpicServerClient
from epicserver_config import (
    MAX_LOG_LINES,
    MAX_CHARACTERS_DISPLAY,
    CHART_HEIGHT,
    CHART_THEME,
    AUTO_REFRESH_ENABLED,
    REFRESH_INTERVAL
)
import ui_components as ui

# ==============================================================================
# SUB-RENDERERS
# ==============================================================================

def _render_server_health_gauge(online: int, max_players: int):
    """Renders the gauge chart for server occupancy."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=online,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Players Online"},
        delta={'reference': max_players},
        gauge={
            'axis': {'range': [None, max_players]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, max_players * 0.5], 'color': "lightgray"},
                {'range': [max_players * 0.5, max_players * 0.8], 'color': "gray"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': max_players * 0.9
            }
        }
    ))
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# TAB RENDERERS
# ==============================================================================

def render_dashboard_tab(client: EpicServerClient):
    """Server Status Dashboard."""
    st.header("📊 Server Dashboard")
    
    status = client.get_server_status()
    if not status:
        st.warning("⚠️ Server Offline or Unreachable")
        return

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    
    is_online = status.get('status') == 'online'
    ui.render_metric_card(
        "Status",
        status.get('status', 'unknown').upper(),
        delta="Online" if is_online else "Offline",
        col=c1
    )

    ui.render_metric_card(
        "Online Players",
        status.get('online_players', 0),
        delta=f"Max: {status.get('max_players', 0)}",
        col=c2
    )

    uptime = status.get('uptime', 0)
    ui.render_metric_card(
        "Uptime",
        f"{uptime // 3600}h",
        delta=f"{uptime} sec",
        col=c3
    )

    ui.render_metric_card("Version", status.get('version', 'N/A'), col=c4)

    st.divider()
    st.subheader("📈 Occupancy")
    _render_server_health_gauge(status.get('online_players', 0), status.get('max_players', 300))

def render_accounts_tab(client: EpicServerClient):
    """Accounts Management Tab."""
    st.header("👥 Accounts")

    data = client.get_accounts()
    if not data or 'accounts' not in data:
        st.warning("Failed to load accounts.")
        return

    accounts = data['accounts']
    active_count = sum(1 for a in accounts if a.get('enabled', 0) == 1)
    
    c1, c2 = st.columns(2)
    ui.render_metric_card("Total Accounts", data.get('total_accounts', 0), col=c1)
    ui.render_metric_card("Active Accounts", active_count, col=c2)
    
    st.divider()
    
    df = pd.DataFrame(accounts)
    if st.checkbox("Show disabled accounts", value=True):
        filtered_df = df
    else:
        filtered_df = df[df['enabled'] == 1]
        
    ui.render_dataframe_with_search(
        filtered_df, "username",
        widget_id="accounts_list",
        column_config={
            "username": "User",
            "enabled": st.column_config.CheckboxColumn("Active"),
            "last_login": "Last Login",
            "char_count": st.column_config.NumberColumn("Chars")
        }
    )

def render_characters_tab(client: EpicServerClient):
    """Characters Tab."""
    st.header("🎭 Characters")
    
    data = client.get_characters()
    if not data or 'characters' not in data:
        st.warning("Failed to load characters.")
        return

    chars = data['characters']
    online_chars = sum(1 for c in chars if c.get('online', 0) == 1)
    
    c1, c2 = st.columns(2)
    ui.render_metric_card("Total Characters", data.get('total_characters', 0), col=c1)
    ui.render_metric_card("Online Now", online_chars, col=c2)
    
    st.divider()
    
    df = pd.DataFrame(chars)
    if st.checkbox("Online only", value=False):
        df = df[df['online'] == 1]
        
    if len(df) > MAX_CHARACTERS_DISPLAY:
        st.info(f"Showing {MAX_CHARACTERS_DISPLAY} of {len(df)} characters")
        df = df.head(MAX_CHARACTERS_DISPLAY)
        
    ui.render_dataframe_with_search(
        df, "name",
        widget_id="chars_list",
        column_config={
            "name": "Name",
            "online": st.column_config.CheckboxColumn("Online"),
            "strength": "STR", "dexterity": "DEX", "intelligence": "INT"
        }
    )

def render_guilds_tab(client: EpicServerClient):
    """Guilds Tab."""
    st.header("🏰 Guilds")
    
    data = client.get_guilds()
    if not data or 'guilds' not in data:
        st.warning("Failed to load guilds.")
        return

    ui.render_metric_card("Total Guilds", data.get('total_guilds', 0))
    st.divider()
    
    df = pd.DataFrame(data['guilds'])
    ui.render_dataframe_with_search(
        df, "name",
        widget_id="guilds_list",
        column_config={
            "guildid": "ID", "name": "Name", "leader": "Leader",
            "member_count": st.column_config.NumberColumn("Members")
        }
    )

    st.subheader("📊 Membership")
    fig = px.bar(df, x='name', y='member_count', title="Members per Guild")
    fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
    st.plotly_chart(fig, use_container_width=True)

def render_parties_tab(client: EpicServerClient):
    """Parties Tab."""
    st.header("🤝 Active Parties")
    
    data = client.get_parties()
    if not data or 'parties' not in data:
        st.warning("Failed to load parties.")
        return

    ui.render_metric_card("Active Parties", data.get('total_parties', 0))
    st.divider()
    
    for party in data['parties']:
        with st.expander(f"👑 {party['leader']} - {party['member_count']} members"):
            st.write("**Members:**")
            for m in party['members']:
                st.write(f"• {m}")

def render_logs_tab(client: EpicServerClient):
    """Server Logs Tab."""
    st.header("📜 Live Logs")
    
    max_lines = st.slider("Max Lines", 10, 500, MAX_LOG_LINES)
    if st.button("🔄 Refresh Logs", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    data = client.get_logs(max_lines)
    if not data or 'logs' not in data:
        st.warning("Logs unavailable.")
        return

    search = st.text_input("🔍 Filter Logs")
    
    for entry in reversed(data['logs']):
        line = entry.get('line', '')
        src = entry.get('source', 'unknown')
        
        if search and search.lower() not in line.lower():
            continue

        fmt = f"[{src}] {line}"
        if 'ERROR' in line.upper():
            st.error(fmt)
        elif 'WARNING' in line.upper():
            st.warning(fmt)
        else:
            st.text(fmt)

# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def render_epicserver_panel():
    """Main function to render EpicServer Panel."""
    ui.apply_metric_style()
    
    client = EpicServerClient()
    connected = client.test_connection()
    
    def manual_refresh():
        st.cache_data.clear()
        st.rerun()

    ui.render_header_with_refresh(
        "⚙️ Epic Server Analyzer",
        "Real-time Server Management",
        manual_refresh
    )
    
    ui.render_connection_sidebar(
        "Server Connection",
        connected,
        client.base_url,
        AUTO_REFRESH_ENABLED,
        REFRESH_INTERVAL
    )

    tabs = st.tabs(["📊 Dashboard", "👥 Accounts", "🎭 Characters", "🏰 Guilds", "🤝 Parties", "📜 Logs"])
    
    renderers = [
        render_dashboard_tab, render_accounts_tab, render_characters_tab,
        render_guilds_tab, render_parties_tab, render_logs_tab
    ]
    
    for tab, renderer in zip(tabs, renderers):
        with tab:
            renderer(client)

    ui.handle_auto_refresh("Server Connection", REFRESH_INTERVAL)
