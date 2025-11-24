"""
Configurações do EpicBrain Panel
Centralize aqui as configurações de conexão com a API
"""

# API Configuration
EPICBRAIN_API_URL = "http://localhost:8000"  # Altere para o IP/porta corretos
EPICBRAIN_API_KEY = ""  # Adicione se necessário

# Cache settings
CACHE_DURATION = 300  # 5 minutos em segundos

# Auto-refresh settings
AUTO_REFRESH_ENABLED = True
REFRESH_INTERVAL = 60  # 1 minuto em segundos

# Visualization settings
MAX_LOCATIONS_DISPLAY = 10
MIN_INTERACTIONS_NETWORK = 3
CHART_HEIGHT = 400
CHART_THEME = "streamlit"  # ou "plotly", "plotly_white", "plotly_dark"
