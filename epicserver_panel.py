"""
Epic Server Panel - Painel de Gestão do Servidor POL
Componentes visuais para monitoramento e gestão
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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

def render_dashboard_tab(client: EpicServerClient):
    """
    Renderiza a aba de Dashboard - Status do Servidor
    """
    st.header("📊 Dashboard do Servidor")
    
    # Botão de atualizar
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obter status do servidor
    status = client.get_server_status()
    
    if not status:
        st.warning("⚠️ Servidor POL offline ou inacessível")
        return
    
    # Cards de métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Status",
            status.get('status', 'unknown').upper(),
            delta="Online" if status.get('status') == 'online' else "Offline"
        )
    
    with col2:
        st.metric(
            "Jogadores Online",
            status.get('online_players', 0),
            delta=f"Max: {status.get('max_players', 0)}"
        )
    
    with col3:
        uptime_seconds = status.get('uptime', 0)
        uptime_hours = uptime_seconds // 3600
        st.metric(
            "Uptime",
            f"{uptime_hours}h",
            delta=f"{uptime_seconds} segundos"
        )
    
    with col4:
        st.metric(
            "Versão",
            status.get('version', 'N/A')
        )
    
    st.divider()
    
    # Gráfico de ocupação
    st.subheader("📈 Ocupação do Servidor")
    
    online = status.get('online_players', 0)
    max_players = status.get('max_players', 300)
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = online,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Jogadores"},
        delta = {'reference': max_players},
        gauge = {
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

def render_accounts_tab(client: EpicServerClient):
    """
    Renderiza a aba de Contas
    """
    st.header("👥 Contas do Servidor")
    
    # Obter dados
    accounts_data = client.get_accounts()
    
    if not accounts_data or 'accounts' not in accounts_data:
        st.warning("⚠️ Não foi possível carregar dados de contas")
        return
    
    # Métricas
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Contas", accounts_data.get('total_accounts', 0))
    with col2:
        enabled_count = sum(1 for acc in accounts_data['accounts'] if acc.get('enabled', 0) == 1)
        st.metric("Contas Ativas", enabled_count)
    
    st.divider()
    
    # Tabela de contas
    if accounts_data['accounts']:
        df = pd.DataFrame(accounts_data['accounts'])
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 Buscar conta", placeholder="Nome de usuário...")
        with col2:
            show_disabled = st.checkbox("Mostrar contas desabilitadas", value=True)
        
        # Aplicar filtros
        if search:
            df = df[df['username'].str.contains(search, case=False, na=False)]
        
        if not show_disabled:
            df = df[df['enabled'] == 1]
        
        # Exibir tabela
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "username": "Usuário",
                "enabled": st.column_config.CheckboxColumn("Ativo"),
                "last_login": "Último Login",
                "char_count": st.column_config.NumberColumn("Personagens", format="%d")
            }
        )

def render_characters_tab(client: EpicServerClient):
    """
    Renderiza a aba de Personagens
    """
    st.header("🎭 Personagens")
    
    # Obter dados
    chars_data = client.get_characters()
    
    if not chars_data or 'characters' not in chars_data:
        st.warning("⚠️ Não foi possível carregar dados de personagens")
        return
    
    # Métricas
    total_chars = chars_data.get('total_characters', 0)
    online_chars = sum(1 for char in chars_data['characters'] if char.get('online', 0) == 1)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de Personagens", total_chars)
    with col2:
        st.metric("Online Agora", online_chars)
    
    st.divider()
    
    # Tabela de personagens
    if chars_data['characters']:
        df = pd.DataFrame(chars_data['characters'])
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 Buscar personagem", placeholder="Nome...")
        with col2:
            online_only = st.checkbox("Apenas online", value=False)
        
        # Aplicar filtros
        if search:
            df = df[df['name'].str.contains(search, case=False, na=False)]
        
        if online_only:
            df = df[df['online'] == 1]
        
        # Limitar exibição
        if len(df) > MAX_CHARACTERS_DISPLAY:
            st.info(f"Mostrando {MAX_CHARACTERS_DISPLAY} de {len(df)} personagens")
            df = df.head(MAX_CHARACTERS_DISPLAY)
        
        # Exibir tabela
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "name": "Nome",
                "online": st.column_config.CheckboxColumn("Online"),
                "x": "X",
                "y": "Y",
                "z": "Z",
                "strength": "STR",
                "dexterity": "DEX",
                "intelligence": "INT"
            }
        )

def render_guilds_tab(client: EpicServerClient):
    """
    Renderiza a aba de Guildas
    """
    st.header("🏰 Guildas")
    
    # Obter dados
    guilds_data = client.get_guilds()
    
    if not guilds_data or 'guilds' not in guilds_data:
        st.warning("⚠️ Não foi possível carregar dados de guildas")
        return
    
    # Métricas
    st.metric("Total de Guildas", guilds_data.get('total_guilds', 0))
    
    st.divider()
    
    # Tabela de guildas
    if guilds_data['guilds']:
        df = pd.DataFrame(guilds_data['guilds'])
        
        st.dataframe(
            df,
            use_container_width=True,
            column_config={
                "guildid": "ID",
                "name": "Nome da Guilda",
                "leader": "Líder",
                "member_count": st.column_config.NumberColumn("Membros", format="%d")
            }
        )
        
        # Gráfico de membros
        st.subheader("📊 Distribuição de Membros")
        fig = px.bar(
            df,
            x='name',
            y='member_count',
            title="Membros por Guilda",
            labels={'name': 'Guilda', 'member_count': 'Membros'}
        )
        fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)

def render_parties_tab(client: EpicServerClient):
    """
    Renderiza a aba de Grupos
    """
    st.header("🤝 Grupos Ativos")
    
    # Obter dados
    parties_data = client.get_parties()
    
    if not parties_data or 'parties' not in parties_data:
        st.warning("⚠️ Não foi possível carregar dados de grupos")
        return
    
    # Métricas
    st.metric("Grupos Ativos", parties_data.get('total_parties', 0))
    
    st.divider()
    
    # Listar grupos
    if parties_data['parties']:
        for party in parties_data['parties']:
            with st.expander(f"👑 {party['leader']} - {party['member_count']} membros"):
                st.write("**Membros:**")
                for member in party['members']:
                    st.write(f"• {member}")
    else:
        st.info("Nenhum grupo ativo no momento")

def render_logs_tab(client: EpicServerClient):
    """
    Renderiza a aba de Logs
    """
    st.header("📜 Logs do Servidor")
    
    # Controles
    col1, col2 = st.columns([3, 1])
    with col1:
        max_lines = st.slider("Número de linhas", 10, 500, MAX_LOG_LINES)
    with col2:
        if st.button("🔄 Atualizar", use_container_width=True, key="logs_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    # Obter logs
    logs_data = client.get_logs(max_lines)
    
    if not logs_data or 'logs' not in logs_data:
        st.warning("⚠️ Não foi possível carregar logs")
        return
    
    # Filtro de busca
    search = st.text_input("🔍 Filtrar logs", placeholder="Buscar texto...")
    
    # Exibir logs
    st.subheader(f"Últimas {logs_data.get('total_entries', 0)} entradas")
    
    for log_entry in reversed(logs_data['logs']):
        line = log_entry.get('line', '')
        source = log_entry.get('source', 'unknown')
        
        if search and search.lower() not in line.lower():
            continue
        
        # Colorir por tipo
        if 'ERROR' in line or 'error' in line:
            st.error(f"[{source}] {line}")
        elif 'WARNING' in line or 'warning' in line:
            st.warning(f"[{source}] {line}")
        else:
            st.text(f"[{source}] {line}")

def render_epicserver_panel():
    """
    Renderiza o painel completo do Epic Server Analyzer
    """
    st.title("⚙️ Epic Server Analyzer")
    st.markdown("*Gestão e monitoramento do servidor POL em tempo real*")
    
    # Inicializar cliente
    client = EpicServerClient()
    
    # Testar conexão (Exibir no painel principal)
    col_status, col_url = st.columns([1, 3])
    with col_status:
        if client.test_connection():
            st.success("✅ Conectado ao POL")
        else:
            st.error("❌ POL Offline")
    
    with col_url:
        if not client.test_connection():
            st.info(f"Tentando conectar em: `{client.base_url}` (Verifique `epicserver_config.py`)")
    
    st.divider()
    
    # Abas principais
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dashboard",
        "👥 Accounts",
        "🎭 Characters",
        "🏰 Guilds",
        "🤝 Parties",
        "📜 Logs"
    ])
    
    with tab1:
        render_dashboard_tab(client)
    
    with tab2:
        render_accounts_tab(client)
    
    with tab3:
        render_characters_tab(client)
    
    with tab4:
        render_guilds_tab(client)
    
    with tab5:
        render_parties_tab(client)
    
    with tab6:
        render_logs_tab(client)
