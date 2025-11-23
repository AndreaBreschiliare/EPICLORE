import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai
import json
import re
import base64
from PIL import Image
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_image_coordinates import streamlit_image_coordinates

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="World Architect Pro", layout="wide", page_icon="🏰")

# --- 🎨 ESTILO VISUAL ---
def aplicar_estilo_visual():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap');
        .stApp {
            background-color: #0e1117;
            background-image: radial-gradient(circle at 50% 0, #1c2331, #0e1117);
            color: #d4d4d4;
            font-family: 'Lato', sans-serif;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Cinzel', serif;
            color: #e6c200 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-weight: 700;
        }
        .stButton > button {
            background: linear-gradient(180deg, #2e2e2e 0%, #1a1a1a 100%);
            color: #e6c200 !important;
            border: 1px solid #e6c200 !important;
            font-family: 'Cinzel', serif;
        }
        /* Ajuste para o componente de coordenadas */
        iframe[title="streamlit_image_coordinates.streamlit_image_coordinates"] {
            border: 2px solid #e6c200;
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()

# --- INICIALIZAÇÃO SEGURA DE ESTADO ---
caches_salvos = {} 
if "sugestoes_ia" not in st.session_state: st.session_state.sugestoes_ia = {}
if "erros_ia" not in st.session_state: st.session_state.erros_ia = {}
if "resumo_erros" not in st.session_state: st.session_state.resumo_erros = ""
if "auditoria_dados" not in st.session_state: st.session_state.auditoria_dados = []
if "messages" not in st.session_state: st.session_state.messages = []
if "glossario" not in st.session_state: st.session_state.glossario = {}
if "arvore_dot" not in st.session_state: st.session_state.arvore_dot = ""
if "timeline_dados" not in st.session_state: st.session_state.timeline_dados = []
if "dashboard_dados" not in st.session_state: st.session_state.dashboard_dados = []
if "grafo_dot" not in st.session_state: st.session_state.grafo_dot = ""
# NOVO: Estado para marcadores do mapa
if "mapa_pins" not in st.session_state: st.session_state.mapa_pins = []

# --- 1. CONEXÃO COM O BANCO DE DADOS (FIREBASE) ---
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro no Segredo (Secrets): {e}")
        st.stop()

db = firestore.client()

# --- 2. FUNÇÕES DE SUPORTE E CACHE ---
def carregar_lore():
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc = doc_ref.get()
    if doc.exists: return doc.to_dict()
    else:
        dados_iniciais = {cat: "" for cat in CATEGORIAS}
        doc_ref.set(dados_iniciais)
        return dados_iniciais

def carregar_mapa():
    doc_ref = db.collection("mundos").document("mapa_oficial")
    doc = doc_ref.get()
    if doc.exists: return doc.to_dict().get("imagem_b64", None)
    return None

# NOVO: Carregar e Salvar Marcadores (Pins)
def carregar_pins():
    doc_ref = db.collection("mundos").document("mapa_pins")
    doc = doc_ref.get()
    if doc.exists: return doc.to_dict().get("lista", [])
    return []

def salvar_pins(lista_pins):
    doc_ref = db.collection("mundos").document("mapa_pins")
    doc_ref.set({"lista": lista_pins})

def carregar_cache_analises():
    doc_ref = db.collection("mundos").document("cache_analises")
    doc = doc_ref.get()
    if doc.exists: return doc.to_dict()
    return {}

def salvar_categoria(categoria, texto):
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc_ref.set({categoria: texto}, merge=True)

def salvar_mapa_b64(b64_string):
    doc_ref = db.collection("mundos").document("mapa_oficial")
    doc_ref.set({"imagem_b64": b64_string})

def salvar_cache_analise(tipo, dados):
    doc_ref = db.collection("mundos").document("cache_analises")
    doc_ref.set({tipo: dados}, merge=True)

def extrair_json(texto):
    try:
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except:
        return None

def extrair_dot(texto):
    try:
        match = re.search(r"```(?:dot|graphviz)\n(.*?)\n```", texto, re.DOTALL)
        if match: return match.group(1)
        if "digraph" in texto:
            inicio = texto.find("digraph")
            fim = texto.rfind("}") + 1
            return texto[inicio:fim]
        return None
    except:
        return None

def comprimir_imagem(arquivo_upload):
    image = Image.open(arquivo_upload)
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    max_width = 1600
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int((float(image.height) * float(ratio)))
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# --- 3. LISTA DE CATEGORIAS ---
CATEGORIAS = [
    "Absencia - Caos", "Radiancia - Ordem", "Warp", "Os 4 Cavaleiros",
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    "Timeline - Cataclisma", "Timeline - Badlands", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

# --- 4. CARREGAMENTO ---
caches_salvos = carregar_cache_analises()
if not st.session_state.sugestoes_ia: st.session_state.sugestoes_ia = caches_salvos.get("sugestoes", {})
if not st.session_state.erros_ia: st.session_state.erros_ia = caches_salvos.get("erros", {})
if not st.session_state.resumo_erros: st.session_state.resumo_erros = caches_salvos.get("resumo_erros", "")
if not st.session_state.auditoria_dados: st.session_state.auditoria_dados = caches_salvos.get("auditoria", [])
if not st.session_state.messages: st.session_state.messages = caches_salvos.get("chat_history", [])
if not st.session_state.glossario: st.session_state.glossario = caches_salvos.get("glossario", {})
if not st.session_state.arvore_dot: st.session_state.arvore_dot = caches_salvos.get("arvore_dot", "")
if not st.session_state.timeline_dados: st.session_state.timeline_dados = caches_salvos.get("timeline_dados", [])
if not st.session_state.dashboard_dados: st.session_state.dashboard_dados = caches_salvos.get("dashboard_dados", [])
if not st.session_state.grafo_dot: st.session_state.grafo_dot = caches_salvos.get("grafo_dot", "")
if not st.session_state.mapa_pins: st.session_state.mapa_pins = carregar_pins()

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro Banco: {e}")
    st.stop()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.title("🏰 World Architect")
    st.header("⚙️ Configuração")
    api_key = st.text_input("Chave do Oráculo (API Key)", type="password")
    
    modelo_escolhido = "gemini-pro" 
    if api_key:
        genai.configure(api_key=api_key)
        try:
            lista = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and "exp" not in m.name]
            lista.sort(key=lambda x: "flash" not in x)
            modelo_escolhido = st.selectbox("Cérebro da IA:", lista, index=0)
        except: pass

    st.divider()
    st.subheader("🔍 Busca Global")
    termo_busca = st.text_input("Procurar no Lore:", placeholder="Ex: Elfos")
    if termo_busca:
        resultados = []
        for cat, texto in lore_data.items():
            if termo_busca.lower() in texto.lower():
                resultados.append(cat)
        if resultados:
            st.success(f"Encontrado em {len(resultados)} seções:")
            for r in resultados:
                st.caption(f"• {r}")
        else:
            st.warning("Não encontrado.")

# --- ABAS ---
abas = [
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", 
    "📚 Glossário", "🌳 Genealogia", "🕸️ Conexões", "📉 Timeline", "📊 Dashboards", "🗺️ Mapa"
]
tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_genealogia, tab_conexoes, tab_timeline, tab_dashboard, tab_mapa = st.tabs(abas)

# === ABA 1: EDITOR ===
with tab_editor:
    col_titulo, col_filtro = st.columns([3, 1])
    with col_titulo:
        st.info("As escrituras são salvas automaticamente nos arquivos etéreos (Nuvem).")
    with col_filtro:
        filtro_visualizacao = st.selectbox(
            "📑 Índice (Filtrar):", 
            ["Ver Tudo", "Geral/Cosmologia", "Timeline", "Povos"]
        )

    def criar_secao_editor(titulo, filtro_chave):
        if filtro_visualizacao != "Ver Tudo":
            if filtro_visualizacao == "Geral/Cosmologia" and filtro_chave != "Geral": return
            if filtro_visualizacao == "Timeline" and filtro_chave != "Timeline": return
            if filtro_visualizacao == "Povos" and filtro_chave != "Povo": return

        st.markdown(f"### {titulo}")
        cols = st.columns(2)
        idx = 0
        for cat in CATEGORIAS:
            mostrar = False
            if filtro_chave == "Geral" and ("Timeline" not in cat and "Povo" not in cat): mostrar = True
            elif filtro_chave != "Geral" and filtro_chave in cat: mostrar = True
            
            if mostrar:
                with cols[idx % 2]:
                    val_atual = lore_data.get(cat, "")
                    novo_val = st.text_area(cat, value=val_atual, height=500, key=f"txt_{cat}")
                    if st.button(f"💾 Salvar {cat}", key=f"btn_{cat}"):
                        salvar_categoria(cat, novo_val)
                        st.toast(f"Alterações em '{cat}' salvas com sucesso!", icon="✅")
                idx += 1
        st.divider()

    criar_secao_editor("📜 Documentos Gerais & Cosmologia", "Geral")
    criar_secao_editor("⏳ Timeline", "Timeline")
    criar_secao_editor("🏰 Povos", "Povo")

# === ABA 2: CHAT ===
with tab_chat:
    c1, c2 = st.columns([4, 1])
    c1.header("🔮 Oráculo da Lore")
    if c2.button("🗑️ Limpar"):
        st.session_state.messages = []
        salvar_cache_analise("chat_history", [])
        st.rerun()

    if not api_key: st.warning("O Oráculo precisa da Chave (API Key).")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Consulte os espíritos..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"): st.markdown(prompt)
            lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
            sys_prompt = f"Lore: {json.dumps(lore_ativo, ensure_ascii=False)}\nUsuário: {prompt}"
            with st.chat_message("assistant"):
                try:
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(sys_prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    salvar_cache_analise("chat_history", st.session_state.messages)
                except Exception as e: st.error(str(e))

# === ABA 3: AUDITORIA ===
with tab_aval:
    st.header("⚖️ O Julgamento Final")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.auditoria_dados: st.success("📂 Carregado da memória.")
        if st.button("🔄 Convocar Novo Julgamento"):
            with st.spinner("O Juiz está analisando os autos..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_auditoria = f"""
                    Atue como Crítico Literário CÍNICO. Analise: {json.dumps(lore_ativo, ensure_ascii=False)}. 
                    Avalie 10 pilares. JSON OBRIGATÓRIO: [{{ "titulo": "...", "nota": 8, "analise": "...", "melhorias": "..." }}]
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_auditoria)
                    dados = extrair_json(res.text)
                    if dados:
                        st.session_state.auditoria_dados = dados
                        salvar_cache_analise("auditoria", dados)
                        st.rerun()
                    else: st.write(res.text)
                except Exception as e: st.error(str(e))
        
        if st.session_state.auditoria_dados:
             for item in st.session_state.auditoria_dados:
                with st.expander(f"{item['titulo']} - Nota {item['nota']}"):
                    st.progress(item['nota']/10)
                    st.info(item['analise'])
                    st.warning(item['melhorias'])

# === ABA 4: SUGESTÕES ===
with tab_sugestao:
    st.header("💡 A Musa Inspiradora")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.sugestoes_ia: st.success("📂 Inspirações recuperadas.")
        if st.button("🔄 Pedir Novas Ideias"):
            with st.spinner("Sonhando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items()}
                    prompt = f"""
                    Co-Autor. Para CADA categoria, 3 a 5 TÓPICOS (Bullet Points).
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    JSON: {{ "Categoria": "• Ideia 1\\n• Ideia 2", ... }}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt)
                    dados = extrair_json(res.text)
                    if dados:
                        st.session_state.sugestoes_ia = dados
                        salvar_cache_analise("sugestoes", dados)
                        st.rerun()
                    else: st.error("Erro JSON")
                except Exception as e: st.error(f"Erro: {e}")
    
    def criar_secao_sugestao(titulo, filtro):
        st.markdown(f"### {titulo}")
        cols = st.columns(2)
        idx = 0
        for cat in CATEGORIAS:
            mostrar = False
            if filtro == "Geral" and ("Timeline" not in cat and "Povo" not in cat): mostrar = True
            elif filtro != "Geral" and filtro in cat: mostrar = True
            if mostrar:
                with cols[idx % 2]:
                    sug = st.session_state.sugestoes_ia.get(cat, "...")
                    st.text_area(f"💡 {cat}", value=sug, height=250, disabled=True)
                idx += 1
        st.divider()
        
    if st.session_state.sugestoes_ia:
        criar_secao_sugestao("Geral", "Geral")
        criar_secao_sugestao("Timeline", "Timeline")
        criar_secao_sugestao("Povos", "Povo")

# === ABA 5: INCOERÊNCIAS ===
with tab_erros:
    st.header("⚡ O Inquisidor Lógico")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.erros_ia: st.success("📂 Inquérito recuperado.")
        if st.button("🔄 Iniciar Caça às Bruxas"):
            with st.spinner("O Inquisidor afia suas lâminas..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_erros = f"""
                    Auditor Lógico. Cruze dados. Ache contradições. Use Bullet Points.
                    JSON: {{ "resumo_geral": "...", "detalhes": {{ "Categoria": "• 🔴 ERRO: ...", ... }} }}
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_erros)
                    dados_json = extrair_json(res.text)
                    if dados_json:
                        st.session_state.resumo_erros = dados_json.get("resumo_geral", "")
                        st.session_state.erros_ia = dados_json.get("detalhes", {})
                        salvar_cache_analise("erros", st.session_state.erros_ia)
                        salvar_cache_analise("resumo_erros", st.session_state.resumo_erros)
                        st.rerun()
                    else: st.write(res.text)
                except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.resumo_erros: st.info(f"📝 **Veredito:**\n\n{st.session_state.resumo_erros}")

    def criar_secao_erros(titulo, filtro):
        st.markdown(f"### {titulo}")
        cols = st.columns(2)
        idx = 0
        for cat in CATEGORIAS:
            mostrar = False
            if filtro == "Geral" and ("Timeline" not in cat and "Povo" not in cat): mostrar = True
            elif filtro != "Geral" and filtro in cat: mostrar = True
            if mostrar:
                with cols[idx % 2]:
                    val = lore_data.get(cat, "")
                    st.text_area(f"📄 {cat}", value=val, height=150, disabled=True, key=f"view_{cat}")
                    erro = st.session_state.erros_ia.get(cat, None)
                    if erro: st.error(f"🚨 **PROBLEMAS:**\n\n{erro}")
                    else: st.success("✅ Aprovado")
                idx += 1
        st.divider()
        
    if st.session_state.erros_ia:
        criar_secao_erros("Geral", "Geral")
        criar_secao_erros("Timeline", "Timeline")
        criar_secao_erros("Povos", "Povo")

# === ABA 6: GLOSSÁRIO ===
with tab_glossario:
    st.header("📚 O Grande Arquivo")
    if not api_key: st.warning("Insira a API Key.")
    else:
        c_btn, c_info = st.columns([1, 3])
        with c_btn:
            if st.button("🔄 Reescrever Dicionário"):
                with st.spinner("Catalogando..."):
                    try:
                        lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                        prompt = f"""
                        Bibliotecário. Extraia termos (Nomes, Cidades, Magias). Definição curta.
                        JSON: {{ "Termo": "Definição...", ... }}
                        LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                        """
                        model = genai.GenerativeModel(modelo_escolhido)
                        res = model.generate_content(prompt)
                        dados = extrair_json(res.text)
                        if dados:
                            st.session_state.glossario = dados
                            salvar_cache_analise("glossario", dados)
                            st.success("Feito!")
                            st.rerun()
                        else: st.error("Erro JSON")
                    except Exception as e: st.error(f"Erro: {e}")
        
        with c_info:
            if st.session_state.glossario: st.info(f"Verbetes Catalogados: {len(st.session_state.glossario)}")

    st.divider()
    c_leitor, c_termos = st.columns([2, 1])
    with c_leitor:
        txt_escolhido = st.selectbox("Ler Pergaminho:", CATEGORIAS)
        conteudo = lore_data.get(txt_escolhido, "")
        st.text_area("Leitura:", value=conteudo, height=600, disabled=True)
    with c_termos:
        st.subheader("🔍 Notas de Rodapé")
        if not st.session_state.glossario: st.warning("Gere o glossário!")
        elif not conteudo: st.write("...")
        else:
            encontrados = [(t, d) for t, d in st.session_state.glossario.items() if t in conteudo]
            if encontrados:
                for t, d in encontrados:
                    with st.expander(f"🔹 {t}"): st.write(d)
            else: st.info("Nenhum termo mágico encontrado.")

# === ABA 7: GENEALOGIA ===
with tab_genealogia:
    st.header("🌳 Linhagens e Alianças")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.arvore_dot: st.success("📂 Diagrama recuperado.")
        if st.button("🔄 Desenhar Árvore"):
            with st.spinner("Traçando linhagens..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_genealogia = f"""
                    Atue como Genealogista. GRAPHVIZ DOT.
                    REGRAS: digraph G {{ rankdir=LR; ... }}
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    RESPONDA APENAS CODIGO DOT.
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_genealogia)
                    dot_code = extrair_dot(res.text)
                    if dot_code:
                        st.session_state.arvore_dot = dot_code
                        salvar_cache_analise("arvore_dot", dot_code)
                        st.success("Feito!")
                        st.rerun()
                    else: st.error("Erro no DOT.")
                except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.arvore_dot:
        try:
            st.graphviz_chart(st.session_state.arvore_dot)
        except Exception as e: st.error(f"Erro visual: {e}")

# === ABA 8: CONEXÕES (CORRIGIDA) ===
with tab_conexoes:
    st.header("🕸️ Teia de Influência")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.grafo_dot: st.success("📂 Rede carregada.")
        if st.button("🔄 Mapear Teia Política"):
            with st.spinner("Desenhando a teia..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_grafo = f"""
                    Atue como um Designer. Crie um GRAFO DE CONEXÕES (DOT) para MODO ESCURO.
                    
                    graph [bgcolor="#0e1117", layout=fdp, K=2.5, overlap=false, splines=curved];
                    node [shape=rect, style="filled,rounded", fillcolor="#1f1f1f", color="#e6c200", fontcolor="#ffea00", penwidth=2, fontname="Arial", fontsize=14];
                    edge [penwidth=1.2, fontname="Arial", fontsize=11];
                    
                    - Aliado: color="#00ff00" fontcolor="#00ff00"
                    - Inimigo: color="#ff3333" fontcolor="#ff3333"
                    - Neutro: color="#e6c200" fontcolor="#e6c200"
                    
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    RESPONDA APENAS CODIGO DOT.
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_grafo)
                    dot_code = extrair_dot(res.text)
                    if dot_code:
                        st.session_state.grafo_dot = dot_code
                        salvar_cache_analise("grafo_dot", dot_code)
                        st.success("Feito!")
                        st.rerun()
                    else: st.error("Erro no DOT.")
                except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.grafo_dot:
        try:
            st.graphviz_chart(st.session_state.grafo_dot, use_container_width=True)
        except Exception as e: st.error(f"Erro visual: {e}")

# === ABA 9: TIMELINE VISUAL ===
with tab_timeline:
    st.header("📉 A Marcha do Tempo")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.timeline_dados: st.success("📂 Cronologia recuperada.")
        if st.button("🔄 Gerar Gráfico Temporal"):
            with st.spinner("Calculando eras..."):
                try:
                    lore_timelines = {k:v for k,v in lore_data.items() if "Timeline" in k and v.strip()}
                    prompt_time = f"""
                    Analise Timelines. Extraia eventos.
                    SAIDA JSON: [{{ "ano_numerico": 100, "data_exibicao": "Ano 100", "evento": "...", "grupo": "..." }}]
                    LORE: {json.dumps(lore_timelines, ensure_ascii=False)}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_time)
                    dados_tl = extrair_json(res.text)
                    if dados_tl:
                        st.session_state.timeline_dados = dados_tl
                        salvar_cache_analise("timeline_dados", dados_tl)
                        st.success("Processado!")
                        st.rerun()
                    else: st.error("Erro JSON.")
                except Exception as e: st.error(str(e))

    if st.session_state.timeline_dados:
        try:
            df = pd.DataFrame(st.session_state.timeline_dados)
            if not df.empty:
                fig = px.scatter(
                    df, x="ano_numerico", y="grupo", hover_name="data_exibicao", 
                    hover_data={"ano_numerico": False, "grupo": False, "evento": True}, 
                    color="grupo", title="Linha do Tempo (Passe o mouse)", height=600, size_max=15
                )
                fig.update_traces(marker=dict(size=14, line=dict(width=2, color='#e6c200')))
                fig.update_layout(
                    font_family="Lato", font_color="#d4d4d4", title_font_family="Cinzel", title_font_color="#e6c200",
                    paper_bgcolor="#0e1117", plot_bgcolor="#161b22", xaxis=dict(gridcolor="#30363d"), yaxis=dict(gridcolor="#30363d")
                )
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Sem dados.")
        except Exception as e: st.error(f"Erro gráfico: {e}")

# === ABA 10: DASHBOARDS ===
with tab_dashboard:
    st.header("📊 Sala de Guerra")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.dashboard_dados: st.success("📂 Dados táticos recuperados.")
        if st.button("🔄 Calcular Balança de Poder"):
            with st.spinner("O Estrategista está avaliando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_dash = f"""
                    Estrategista Militar. Avalie 6-10 facções. Notas 0-100: Militar, Magia, Economia, Influencia.
                    SAÍDA JSON: [{{ "Entidade": "...", "Militar": 90, ... }}]
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_dash)
                    dados_dash = extrair_json(res.text)
                    if dados_dash:
                        st.session_state.dashboard_dados = dados_dash
                        salvar_cache_analise("dashboard_dados", dados_dash)
                        st.success("Feito!")
                        st.rerun()
                    else: st.error("Erro JSON.")
                except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.dashboard_dados:
        df_dash = pd.DataFrame(st.session_state.dashboard_dados)
        st.subheader("⚔️ Comparativo")
        fig_bar = px.bar(df_dash, x="Entidade", y=["Militar", "Magia", "Economia", "Influencia"], barmode="group", title="Atributos", color_discrete_sequence=["#e63946", "#a8dadc", "#e6c200", "#457b9d"])
        fig_bar.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22", legend_title_text='Atributo')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌍 Influência Global")
            fig_pie = px.pie(df_dash, values='Influencia', names='Entidade', title='Poder Político', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
            fig_pie.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117")
            st.plotly_chart(fig_pie, use_container_width=True)
        with c2:
            st.subheader("🕸️ Radar")
            entidade = st.selectbox("Facção:", df_dash["Entidade"].unique())
            dados = df_dash[df_dash["Entidade"] == entidade].iloc[0]
            cats = ["Militar", "Magia", "Economia", "Influencia"]
            vals = [dados[c] for c in cats]
            fig_r = px.line_polar(r=vals, theta=cats, line_close=True, range_r=[0, 100])
            fig_r.update_traces(fill='toself', line_color='#e6c200')
            fig_r.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", polar=dict(bgcolor="#161b22", radialaxis=dict(visible=True, range=[0, 100])))
            st.plotly_chart(fig_r, use_container_width=True)

# === ABA 11: MAPA INTERATIVO ===
with tab_mapa:
    st.header("🗺️ Cartografia Oficial")
    
    # Toggle de Modos
    modo_mapa = st.radio("Modo:", ["👁️ Explorar (Zoom/Hover)", "📍 Editar (Adicionar Pins)"], horizontal=True)
    
    mapa_b64 = carregar_mapa()
    
    if mapa_b64:
        # Decodifica imagem para usar em ambas as libs
        imagem_bytes = base64.b64decode(mapa_b64)
        imagem_pil = Image.open(io.BytesIO(imagem_bytes))
        
        if modo_mapa == "👁️ Explorar (Zoom/Hover)":
            # MODO PLOTLY (Visualização Rica)
            if st.session_state.mapa_pins:
                # Cria DataFrame dos pins
                df_pins = pd.DataFrame(st.session_state.mapa_pins)
                
                # Cria figura vazia mas com tamanho da imagem
                fig = px.scatter(
                    df_pins, 
                    x="x", y="y", 
                    hover_name="nome", 
                    hover_data={"x":False, "y":False, "desc":True},
                    title="Mapa Interativo"
                )
                
                # Adiciona a imagem de fundo
                fig.add_layout_image(
                    dict(
                        source=imagem_pil,
                        xref="x", yref="y",
                        x=0, y=0,
                        sizex=imagem_pil.width, sizey=imagem_pil.height,
                        sizing="stretch",
                        opacity=1,
                        layer="below"
                    )
                )
                
                # Ajusta eixos para corresponder aos pixels da imagem
                fig.update_xaxes(visible=False, range=[0, imagem_pil.width])
                fig.update_yaxes(visible=False, range=[imagem_pil.height, 0]) # Inverte Y para bater com coordenadas de imagem
                
                # Estilo dos pontos
                fig.update_traces(marker=dict(size=15, color='#e6c200', symbol='circle', line=dict(width=2, color='black')))
                
                fig.update_layout(
                    width=imagem_pil.width, height=imagem_pil.height,
                    margin=dict(l=0, r=0, t=0, b=0),
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    hoverlabel=dict(bgcolor="#161b22", font_size=14, font_family="Lato")
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.image(imagem_pil, caption="Sem pins ainda. Mude para 'Editar' para adicionar.", use_container_width=True)

        else:
            # MODO EDITOR (Clique para adicionar)
            st.info("Clique na imagem para marcar um local.")
            
            # Componente de clique
            coords = streamlit_image_coordinates(imagem_pil, key="click_map")
            
            if coords:
                st.write(f"📍 Ponto selecionado: {coords['x']}, {coords['y']}")
                
                with st.form("form_pin"):
                    nome_pin = st.text_input("Nome do Local")
                    desc_pin = st.text_area("Descrição / Lore")
                    
                    # Sugestão inteligente: Vincular a uma categoria existente
                    vinculo = st.selectbox("Vincular a Texto Existente (Opcional):", ["Nenhum"] + CATEGORIAS)
                    
                    if st.form_submit_button("💾 Salvar Pin"):
                        if vinculo != "Nenhum":
                            # Se vinculou, pega o resumo do texto
                            texto_vinc = lore_data.get(vinculo, "")[:200] + "..."
                            if not desc_pin: desc_pin = texto_vinc # Preenche se estiver vazio
                        
                        novo_pin = {"x": coords['x'], "y": coords['y'], "nome": nome_pin, "desc": desc_pin}
                        
                        # Adiciona na lista e salva
                        pins_atuais = st.session_state.mapa_pins
                        pins_atuais.append(novo_pin)
                        salvar_pins(pins_atuais)
                        st.session_state.mapa_pins = pins_atuais # Atualiza estado
                        st.success("Pin adicionado!")
                        st.rerun()

    else:
        st.info("Sem mapa.")

    st.markdown("---")
    with st.expander("Carregar Novo Mapa (Substitui o atual)"):
        arquivo_mapa = st.file_uploader("Upload", type=["jpg", "jpeg", "png", "webp"])
        if arquivo_mapa:
            if st.button("📤 Enviar"):
                try:
                    b64 = comprimir_imagem(arquivo_mapa)
                    salvar_mapa_b64(b64)
                    st.success("Salvo!")
                    st.rerun()
                except Exception as e: st.error(str(e))
