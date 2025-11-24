# Dependências necessárias para o EpicBrain Panel

Para rodar o EpicBrain Panel, você precisa instalar as seguintes bibliotecas:

```bash
pip install requests plotly pandas
```

## Arquivos Criados

1. **epicbrain_config.py** - Configurações (URL da API, cache, etc.)
2. **epicbrain_client.py** - Cliente para comunicação com a API
3. **epicbrain_panel.py** - Componentes visuais do painel
4. **world_cloud.py** - Modificado para incluir a aba EpicBrain

## Como Configurar

1. Edite o arquivo `epicbrain_config.py` e altere a linha:
   ```python
   EPICBRAIN_API_URL = "http://localhost:8000"
   ```
   Para o IP e porta corretos da sua API Epic Brain.

2. Certifique-se de que a API Epic Brain está rodando.

3. Execute o World Cloud normalmente:
   ```bash
   streamlit run world_cloud.py
   ```

## Endpoints da API Necessários

A API Epic Brain deve ter os seguintes endpoints funcionando:
- `/health` - Health check
- `/analytics/metrics/players` - Métricas de jogadores
- `/analytics/metrics/locations` - Locais mais visitados
- `/analytics/metrics/activity` - Atividade temporal
- `/analytics/metrics/social` - Interações sociais
- `/analytics/metrics/alerts` - Alertas do sistema
- `/analytics/network` - Grafo de rede social

Todos esses endpoints foram criados no arquivo `src/api/analytics.py` do projeto Epic Brain.
