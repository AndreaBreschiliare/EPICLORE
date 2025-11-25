"""
Epic Server API Client
Cliente para comunicação com a API HTTP do POL Server
"""

import requests
from typing import Dict, Any, Optional, List
import streamlit as st
from epicserver_config import EPICSERVER_API_URL, CACHE_DURATION

class EpicServerClient:
    """Cliente para a API HTTP do POL Server"""
    
    def __init__(self, base_url: str = EPICSERVER_API_URL):
        self.base_url = base_url.rstrip('/')
    
    def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """
        Faz requisição para a API com tratamento de erros
        
        Args:
            endpoint: Endpoint da API (ex: '/server_status.src')
            
        Returns:
            Dados JSON da resposta
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Não foi possível conectar ao servidor POL em {self.base_url}")
            st.info("💡 Verifique se o servidor está rodando e se o endereço está correto em `epicserver_config.py`")
            return {}
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout na requisição ao servidor POL")
            return {}
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ Erro HTTP: {e}")
            return {}
        except Exception as e:
            st.error(f"❌ Erro inesperado: {e}")
            return {}
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_server_status(_self) -> Dict[str, Any]:
        """Obtém status do servidor"""
        return _self._make_request('/server_status.src')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_accounts(_self) -> Dict[str, Any]:
        """Obtém lista de contas"""
        return _self._make_request('/accounts_api.src')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_characters(_self) -> Dict[str, Any]:
        """Obtém lista de personagens"""
        return _self._make_request('/characters_api.src')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_guilds(_self) -> Dict[str, Any]:
        """Obtém lista de guildas"""
        return _self._make_request('/guilds_api.src')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_parties(_self) -> Dict[str, Any]:
        """Obtém lista de grupos ativos"""
        return _self._make_request('/parties_api.src')
    
    @st.cache_data(ttl=CACHE_DURATION)
    def get_logs(_self, lines: int = 100) -> Dict[str, Any]:
        """Obtém últimas entradas de log"""
        return _self._make_request(f'/logs_api.src?lines={lines}')
    
    def test_connection(self) -> bool:
        """Testa conexão com o servidor POL"""
        try:
            response = requests.get(f"{self.base_url}/server_status.src", timeout=3)
            return response.status_code == 200
        except:
            return False
