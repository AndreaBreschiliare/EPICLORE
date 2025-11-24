"""
EpicBrain API Client
Cliente para comunicação com a API do Epic Brain
"""

import requests
from typing import Dict, Any, Optional
import streamlit as st
from epicbrain_config import EPICBRAIN_API_URL, EPICBRAIN_API_KEY, CACHE_DURATION

class EpicBrainClient:
    """Cliente para a API do Epic Brain"""
    
    def __init__(self, base_url: str = EPICBRAIN_API_URL, api_key: str = EPICBRAIN_API_KEY):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['Authorization'] = f'Bearer {api_key}'
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Faz requisição para a API com tratamento de erros
        
        Args:
            endpoint: Endpoint da API (ex: '/analytics/metrics/players')
            params: Parâmetros da query string
            
        Returns:
            Dados JSON da resposta
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Não foi possível conectar à API em {self.base_url}")
            st.info("💡 Verifique se a API está rodando e se o endereço está correto em `epicbrain_config.py`")
            return {}
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout na requisição à API")
            return {}
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ Erro HTTP: {e}")
            return {}
        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")
            return {}
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_player_metrics(_self, days: int = 7) -> Dict[str, Any]:
        """Obtém métricas de jogadores"""
        return _self._make_request('/analytics/metrics/players', {'days': days})
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_location_metrics(_self, limit: int = 10) -> Dict[str, Any]:
        """Obtém métricas de localizações"""
        return _self._make_request('/analytics/metrics/locations', {'limit': limit})
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_activity_metrics(_self, days: int = 7) -> Dict[str, Any]:
        """Obtém métricas de atividade temporal"""
        return _self._make_request('/analytics/metrics/activity', {'days': days})
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_social_metrics(_self, min_interactions: int = 3) -> Dict[str, Any]:
        """Obtém métricas de interações sociais"""
        return _self._make_request('/analytics/metrics/social', {'min_interactions': min_interactions})
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_alerts(_self) -> Dict[str, Any]:
        """Obtém alertas do sistema"""
        return _self._make_request('/analytics/metrics/alerts')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_network_graph(_self, min_interactions: int = 5) -> Dict[str, Any]:
        """Obtém dados do grafo de rede social"""
        return _self._make_request('/analytics/network', {'min_interactions': min_interactions})
    
    def test_connection(self) -> bool:
        """Testa conexão com a API"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
