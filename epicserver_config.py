"""
Configurações do Epic Server Analyzer
Centralize aqui as configurações de conexão com o POL Server
"""

# POL Server HTTP API Configuration
EPICSERVER_API_URL = "http://localhost:3008"  # Porta padrão do POL HTTP server

# Cache settings
CACHE_DURATION = 60  # 1 minuto em segundos

# Auto-refresh settings
AUTO_REFRESH_ENABLED = True
REFRESH_INTERVAL = 30  # 30 segundos

# Display settings
MAX_LOG_LINES = 100
MAX_CHARACTERS_DISPLAY = 50
CHART_HEIGHT = 400
CHART_THEME = "streamlit"  # ou "plotly", "plotly_white", "plotly_dark"
