"""
EpicBrain Panel - Painel de Controle do Servidor UO
Componentes visuais para monitoramento e gestão
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
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

def render_metric_card(label: str, value: Any, delta: str = None, help_text: str = None):
    """Renderiza um card de métrica"""
    st.metric(label=label, value=value, delta=delta, help=help_text)

def render_dashboard_tab(client: EpicBrainClient):
    """
    Renderiza a aba de Dashboard Executivo
    """
    st.header("📊 Dashboard Executivo")
    
    # Filtro de período
    col_filter1, col_filter2 = st.columns([3, 1])
    with col_filter1:
        days = st.selectbox(
            "Período de análise",
            options=[1, 7, 14, 30],
            index=1,
            format_func=lambda x: f"Últimos {x} dias" if x > 1 else "Hoje"
        )
    with col_filter2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Obter dados
    player_metrics = client.get_player_metrics(days=days)
    location_metrics = client.get_location_metrics(limit=MAX_LOCATIONS_DISPLAY)
    alerts = client.get_alerts()
    
    if not player_metrics:
        st.warning("⚠️ Não foi possível carregar os dados. Verifique a conexão com a API.")
        return
    
    # === SEÇÃO 1: CARDS DE MÉTRICAS ===
    st.subheader("📈 Métricas Principais")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        render_metric_card(
            "Jogadores Ativos",
            player_metrics.get('active_today', 0),
            help_text="Jogadores únicos no período selecionado"
        )
    
    with col2:
        render_metric_card(
            "Pico de Atividade",
            f"{player_metrics.get('peak_players', 0)} ({player_metrics.get('peak_hour', 'N/A')})",
            help_text="Maior número de jogadores simultâneos"
        )
    
    with col3:
        render_metric_card(
            "Sessão Média",
            player_metrics.get('avg_session_duration', 'N/A'),
            help_text="Duração média das sessões"
        )
    
    with col4:
        render_metric_card(
            "Total de Logs",
            player_metrics.get('total_logs', 0),
            help_text="Total de registros processados"
        )
    
    st.divider()
    
    # === SEÇÃO 2: ALERTAS ===
    if alerts and alerts.get('alerts'):
        st.subheader("🚨 Alertas do Sistema")
        
        for alert in alerts['alerts']:
            severity = alert.get('severity', 'info')
            message = alert.get('message', '')
            
            if severity == 'high':
                st.error(f"🔴 {message}")
            elif severity == 'medium':
                st.warning(f"🟡 {message}")
            elif severity == 'low':
                st.info(f"🔵 {message}")
            else:
                st.success(f"✅ {message}")
        
        st.divider()
    
    # === SEÇÃO 3: GRÁFICOS ===
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.subheader("📍 Top Localizações")
        
        if location_metrics and location_metrics.get('top_locations'):
            df_locations = pd.DataFrame(location_metrics['top_locations'])
            
            fig = px.bar(
                df_locations,
                x='visits',
                y='name',
                orientation='h',
                title=f"Top {len(df_locations)} Locais Mais Visitados",
                labels={'visits': 'Visitas', 'name': 'Local'},
                color='unique_players',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de localização disponível")
    
    with col_chart2:
        st.subheader("⏰ Atividade por Hora")
        
        activity_metrics = client.get_activity_metrics(days=days)
        
        if activity_metrics and activity_metrics.get('hourly'):
            df_hourly = pd.DataFrame(activity_metrics['hourly'])
            
            fig = px.line(
                df_hourly,
                x='hour',
                y='players',
                title="Jogadores por Hora",
                labels={'hour': 'Hora', 'players': 'Jogadores'},
                markers=True
            )
            fig.update_layout(height=CHART_HEIGHT, template=CHART_THEME)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado de atividade disponível")
    
    # === SEÇÃO 4: TABELA DETALHADA ===
    with st.expander("📋 Detalhes de Localizações"):
        if location_metrics and location_metrics.get('top_locations'):
            df_locations = pd.DataFrame(location_metrics['top_locations'])
            st.dataframe(
                df_locations,
                use_container_width=True,
                column_config={
                    "name": "Local",
                    "visits": st.column_config.NumberColumn("Visitas", format="%d"),
                    "unique_players": st.column_config.NumberColumn("Jogadores Únicos", format="%d")
                }
            )

def render_activity_map_tab(client: EpicBrainClient):
    """
    Renderiza a aba de Mapa de Atividade
    """
    st.header("🗺️ Mapa de Atividade")
    
    # Obter dados
    location_metrics = client.get_location_metrics(limit=50)
    
    if not location_metrics or not location_metrics.get('top_locations'):
        st.warning("⚠️ Nenhum dado de localização disponível")
        return
    
    df_locations = pd.DataFrame(location_metrics['top_locations'])
    
    # === SEÇÃO 1: ANÁLISE DE POPULARIDADE ===
    st.subheader("📊 Análise de Popularidade")
    
    # Classificar áreas
    max_visits = df_locations['visits'].max()
    df_locations['categoria'] = df_locations['visits'].apply(
        lambda x: 'Popular' if x > max_visits * 0.6 
        else 'Média' if x > max_visits * 0.3 
        else 'Baixa'
    )
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        popular = len(df_locations[df_locations['categoria'] == 'Popular'])
        st.metric("🟢 Áreas Populares", popular)
    
    with col2:
        media = len(df_locations[df_locations['categoria'] == 'Média'])
        st.metric("🟡 Áreas Médias", media)
    
    with col3:
        baixa = len(df_locations[df_locations['categoria'] == 'Baixa'])
        st.metric("🔴 Áreas com Baixa Atividade", baixa)
    
    st.divider()
    
    # === SEÇÃO 2: VISUALIZAÇÃO ===
    st.subheader("📈 Distribuição de Atividade")
    
    # Gráfico de pizza
    fig_pie = px.pie(
        df_locations,
        values='visits',
        names='name',
        title="Distribuição de Visitas por Local",
        hole=0.4
    )
    fig_pie.update_layout(height=500, template=CHART_THEME)
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # === SEÇÃO 3: TABELA COMPLETA ===
    st.subheader("📋 Todas as Localizações")
    
    st.dataframe(
        df_locations,
        use_container_width=True,
        column_config={
            "name": "Local",
            "visits": st.column_config.NumberColumn("Visitas", format="%d"),
            "unique_players": st.column_config.NumberColumn("Jogadores Únicos", format="%d"),
            "categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=['Popular', 'Média', 'Baixa']
            )
        }
    )

def render_social_insights_tab(client: EpicBrainClient):
    """
    Renderiza a aba de Insights Sociais
    """
    st.header("💬 Insights Sociais")
    
    # Controles
    col1, col2 = st.columns([3, 1])
    with col1:
        min_interactions = st.slider(
            "Mínimo de interações para exibir",
            min_value=1,
            max_value=20,
            value=MIN_INTERACTIONS_NETWORK,
            help="Filtrar conexões com menos interações"
        )
    with col2:
        if st.button("🔄 Atualizar", use_container_width=True, key="social_refresh"):
            st.cache_data.clear()
            st.rerun()
    
    # Obter dados
    social_metrics = client.get_social_metrics(min_interactions=min_interactions)
    network_data = client.get_network_graph(min_interactions=min_interactions)
    
    if not social_metrics:
        st.warning("⚠️ Não foi possível carregar dados sociais")
        return
    
    # === SEÇÃO 1: MÉTRICAS GERAIS ===
    st.subheader("📊 Métricas Sociais")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Jogadores Únicos",
            social_metrics.get('unique_players', 0)
        )
    
    with col2:
        st.metric(
            "Total de Interações",
            social_metrics.get('total_interactions', 0)
        )
    
    with col3:
        interactions = social_metrics.get('interactions', [])
        st.metric(
            "Conexões Fortes",
            len(interactions),
            help=f"Pares com {min_interactions}+ interações"
        )
    
    st.divider()
    
    # === SEÇÃO 2: REDE DE INTERAÇÕES ===
    st.subheader("🕸️ Rede de Interações")
    
    if network_data and network_data.get('nodes') and network_data.get('edges'):
        nodes = network_data['nodes']
        edges = network_data['edges']
        
        # Criar grafo com Plotly
        edge_trace = []
        for edge in edges:
            # Encontrar posições dos nós (simuladas)
            source_idx = next((i for i, n in enumerate(nodes) if n['id'] == edge['source']), 0)
            target_idx = next((i for i, n in enumerate(nodes) if n['id'] == edge['target']), 0)
            
            # Posições circulares simples
            import math
            angle_source = 2 * math.pi * source_idx / len(nodes)
            angle_target = 2 * math.pi * target_idx / len(nodes)
            
            x0, y0 = math.cos(angle_source), math.sin(angle_source)
            x1, y1 = math.cos(angle_target), math.sin(angle_target)
            
            edge_trace.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=edge['weight']/5, color='#888'),
                    hoverinfo='none',
                    showlegend=False
                )
            )
        
        # Nós
        import math
        node_x = [math.cos(2 * math.pi * i / len(nodes)) for i in range(len(nodes))]
        node_y = [math.sin(2 * math.pi * i / len(nodes)) for i in range(len(nodes))]
        node_text = [n['id'] for n in nodes]
        node_size = [n['size'] for n in nodes]
        
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="top center",
            marker=dict(
                size=node_size,
                color='#1f77b4',
                line=dict(width=2, color='white')
            ),
            hovertemplate='<b>%{text}</b><extra></extra>'
        )
        
        # Criar figura
        fig = go.Figure(data=edge_trace + [node_trace])
        fig.update_layout(
            title="Grafo de Interações entre Jogadores",
            showlegend=False,
            hovermode='closest',
            height=600,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            template=CHART_THEME
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhuma rede de interações disponível com os filtros atuais")
    
    st.divider()
    
    # === SEÇÃO 3: TOP INTERAÇÕES ===
    st.subheader("🤝 Top Interações")
    
    interactions = social_metrics.get('interactions', [])
    
    if interactions:
        df_interactions = pd.DataFrame(interactions[:20])  # Top 20
        
        fig = px.bar(
            df_interactions,
            x='count',
            y=df_interactions.apply(lambda row: f"{row['player1']} ↔ {row['player2']}", axis=1),
            orientation='h',
            title="Pares com Mais Interações",
            labels={'x': 'Interações', 'y': 'Jogadores'},
            color='count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=500, template=CHART_THEME)
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabela detalhada
        with st.expander("📋 Ver Todas as Interações"):
            st.dataframe(
                df_interactions,
                use_container_width=True,
                column_config={
                    "player1": "Jogador 1",
                    "player2": "Jogador 2",
                    "count": st.column_config.NumberColumn("Interações", format="%d")
                }
            )
    else:
        st.info("Nenhuma interação encontrada com os filtros atuais")

def render_epicbrain_panel():
    """
    Renderiza o painel completo do EpicBrain
    """
    st.title("🧠 EpicBrain - Painel de Controle")
    st.markdown("*Monitoramento e análise do servidor Ultima Online*")
    
    # Inicializar cliente
    client = EpicBrainClient()
    
    # Testar conexão
    with st.sidebar:
        st.subheader("🔌 Status da Conexão")
        
        if client.test_connection():
            st.success("✅ Conectado à API")
        else:
            st.error("❌ API não disponível")
            st.info(f"Tentando conectar em: `{client.base_url}`")
            st.markdown("Verifique `epicbrain_config.py`")
        
        st.divider()
        
        # Auto-refresh
        if AUTO_REFRESH_ENABLED:
            st.checkbox(
                "🔄 Auto-atualizar",
                value=True,
                help=f"Atualiza a cada {REFRESH_INTERVAL}s",
                key="auto_refresh"
            )
    
    # Abas principais
    tab1, tab2, tab3 = st.tabs([
        "📊 Dashboard Executivo",
        "🗺️ Mapa de Atividade",
        "💬 Insights Sociais"
    ])
    
    with tab1:
        render_dashboard_tab(client)
    
    with tab2:
        render_activity_map_tab(client)
    
    with tab3:
        render_social_insights_tab(client)
    
    # Auto-refresh
    if AUTO_REFRESH_ENABLED and st.session_state.get('auto_refresh', False):
        import time
        time.sleep(REFRESH_INTERVAL)
        st.rerun()
