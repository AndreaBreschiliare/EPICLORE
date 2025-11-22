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
        h1 {
            text-align: center;
            font-size: 3.5rem;
            margin-bottom: 1rem;
            border-bottom: 2px solid #e6c200;
            padding-bottom: 20px;
        }
        [data-testid="stSidebar"] {
            background-color: #11141a;
            border-right: 1px solid #30363d;
        }
        .stTextArea textarea {
            background-color: #161b22 !important;
            color: #e6e6e6 !important;
            border: 1px solid #30363d !important;
            font-family: 'Lato', sans-serif;
            border-radius: 8px;
        }
        .stButton > button {
            background: linear-gradient(180deg, #2e2e2e 0%, #1a1a1a 100%);
            color: #e6c200 !important;
            border: 1px solid #e6c200 !important;
            font-family: 'Cinzel', serif;
            font-weight: bold;
            border-radius: 6px;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .stButton > button:hover {
            background: linear-gradient(180deg, #e6c200 0%, #b39700 100%);
            color: #0e1117 !important;
            box-shadow: 0 0 15px rgba(230, 194, 0, 0.6);
            transform: translateY(-2px);
            border-color: #fff !important;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #30363d; }
        .stTabs [data-baseweb="tab"] { background-color: transparent; border-radius: 4px 4px 0 0; color: #8b949e; font-family: 'Cinzel', serif; }
        .stTabs [aria-selected="true"] { background-color: #161b22; color: #e6c200; border: 1px solid #e6c200; border-bottom: none; }
        .streamlit-expanderHeader { background-color: #161b22; color: #e6c200 !important; border: 1px solid #30363d; font-family: 'Cinzel', serif; }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()
st.title("🏰 World Architect")
st.markdown("<div style='text-align: center; color: #8b949e; margin-top: -20px; margin-bottom: 30px;'>O Grimório Vivo de Lore & Criação</div>", unsafe_allow_html=True)

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
# NOVO: Cache do Grafo de Conexões
if "grafo_dot" not in st.session_state: st.session_state.grafo_dot = ""

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

# --- 4. CARREGAMENTO DOS DADOS ---
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
# NOVO CACHE
if not st.session_state.grafo_dot: st.session_state.grafo_dot = caches_salvos.get("grafo_dot", "")

# --- 5. INTERFACE ---
st.sidebar.header("⚙️ Configuração Mágica")
api_key = st.sidebar.text_input("Chave do Oráculo (API Key)", type="password")

modelo_escolhido = "gemini-pro" 

if api_key:
    genai.configure(api_key=api_key)
    try:
        lista_modelos = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if "exp" not in m.name:
                    lista_modelos.append(m.name)
        if lista_modelos:
            lista_modelos.sort(key=lambda x: "flash" not in x)
            modelo_escolhido = st.sidebar.selectbox("Inteligência:", lista_modelos, index=0)
    except Exception as e:
        st.sidebar.error(f"Erro IA: {e}")

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro Banco: {e}")
    st.stop()

# --- ABAS ---
abas = [
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", 
    "📚 Glossário", "🌳 Genealogia", "🕸️ Teia de Conexões", "📉 Timeline", "📊 Dashboards", "🗺️ Mapa"
]
# Adicionado tab_conexoes
tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_genealogia, tab_conexoes, tab_timeline, tab_dashboard, tab_mapa = st.tabs(abas)

# === ABA 1: EDITOR ===
with tab_editor:
    st.info("💾 As escrituras são salvas automaticamente nos arquivos etéreos (Nuvem).")
    def criar_secao_editor(titulo, filtro):
        st.markdown(f"### {titulo}")
        cols = st.columns(2)
        idx = 0
        for cat in CATEGORIAS:
            mostrar = False
            if filtro == "Geral" and ("Timeline" not in cat and "Povo" not in cat): mostrar = True
            elif filtro != "Geral" and filtro in cat: mostrar = True
            if mostrar:
                with cols[idx % 2]:
                    val_atual = lore_data.get(cat, "")
                    novo_val = st.text_area(cat, value=val_atual, height=500, key=f"txt_{cat}")
                    if st.button(f"💾 Salvar {cat}", key=f"btn_{cat}"):
                        salvar_categoria(cat, novo_val)
                        st.success("Salvo!")
                        st.rerun()
                idx += 1
        st.divider()
    criar_secao_editor("📜 Documentos Gerais & Cosmologia", "Geral")
    criar_secao_editor("⏳ Timeline", "Timeline")
    criar_secao_editor("🏰 Povos", "Povo")

# === ABA 2: CHAT ===
with tab_chat:
    c1, c2 = st.columns([4, 1])
    c1.header("🔮 Oráculo da Lore")
    if c2.button("🗑️ Esquecer Tudo"):
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
        if st.session_state.auditoria_dados: st.success("📂 Relatório recuperado dos arquivos.")
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
        if st.button("🔄 Iniciar Caça às Bruxas (Contradições)"):
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

# === ABA 8: TEIA DE CONEXÕES (NOVA) ===
with tab_conexoes:
    st.header("🕸️ Teia de Influência Geopolítica")
    st.markdown("Mapa visual de aliados (Verde), inimigos (Vermelho) e suseranos (Dourado).")

    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.grafo_dot: st.success("📂 Rede carregada.")
        if st.button("🔄 Mapear Teia Política"):
            with st.spinner("Desenhando a teia de intrigas..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    
                    prompt_grafo = f"""
                    Atue como um Mestre de Espionagem.
                    TAREFA: Leia o lore e desenhe um GRAFO DE CONEXÕES (Graphviz DOT) entre Reinos, Facções e Personagens Chave.
                    
                    REGRAS VISUAIS OBRIGATÓRIAS:
                    1. Use 'digraph G {{ layout=neato; overlap=false; splines=true; bgcolor="#0e1117"; ... }}'
                    2. ESTILO DOS NÓS:
                       - Reinos/Povos: shape=box, style=filled, fillcolor="#2b2b2b", fontcolor="white", color="#e6c200"
                       - Personagens: shape=ellipse, style=filled, fillcolor="#1a1a1a", fontcolor="white", color="white"
                    3. ESTILO DAS ARESTAS (Use cores para indicar relação):
                       - Aliado/Amigo/Comércio: color="#00ff00" (Verde Neon)
                       - Inimigo/Guerra/Rival: color="#ff0000" (Vermelho Neon)
                       - Suserano/Vassalo/Neutro: color="#e6c200" (Dourado)
                    
                    Identifique as 15-20 conexões mais importantes.
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    
                    RESPONDA APENAS COM O CÓDIGO DOT ENTRE CRASES.
                    """
                    
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_grafo)
                    dot_code = extrair_dot(res.text)
                    
                    if dot_code:
                        st.session_state.grafo_dot = dot_code
                        salvar_cache_analise("grafo_dot", dot_code)
                        st.success("Teia gerada!")
                        st.rerun()
                    else: st.error("Erro ao gerar DOT.")
                except Exception as e: st.error(f"Erro: {e}")

    if st.session_state.grafo_dot:
        try:
            st.graphviz_chart(st.session_state.grafo_dot)
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
    st.header("📊 Sala de Guerra: Poder & Influência")
    
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.dashboard_dados: st.success("📂 Dados táticos recuperados.")
        
        if st.button("🔄 Calcular Balança de Poder"):
            with st.spinner("O Estrategista está avaliando os exércitos e economias..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    
                    prompt_dash = f"""
                    Atue como um Estrategista Militar e Político.
                    Leia o lore abaixo e identifique as 6 a 10 maiores FACÇÕES ou POVOS (ex: Elfos, Orcs, Imperio X).
                    
                    Para cada um, atribua uma nota de 0 a 100 nestes quesitos:
                    - Militar (Força bruta, exércitos)
                    - Magia (Poder arcano/divino)
                    - Economia (Riqueza, recursos)
                    - Influencia (Poder político, aliados)
                    
                    SAÍDA JSON OBRIGATÓRIA:
                    [
                        {{ "Entidade": "Império Aiglano", "Militar": 90, "Magia": 20, "Economia": 80, "Influencia": 70 }},
                        {{ "Entidade": "Tribos Orcs", "Militar": 70, "Magia": 40, "Economia": 10, "Influencia": 5 }},
                        ...
                    ]
                    
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    """
                    
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_dash)
                    dados_dash = extrair_json(res.text)
                    
                    if dados_dash:
                        st.session_state.dashboard_dados = dados_dash
                        salvar_cache_analise("dashboard_dados", dados_dash)
                        st.success("Análise estratégica concluída!")
                        st.rerun()
                    else: st.error("Erro ao extrair dados JSON.")
                except Exception as e: st.error(f"Erro: {e}")

    # Renderiza os Gráficos
    if st.session_state.dashboard_dados:
        df_dash = pd.DataFrame(st.session_state.dashboard_dados)
        
        # 1. Gráfico de Barras (Comparativo)
        st.subheader("⚔️ Comparativo de Forças")
        fig_bar = px.bar(
            df_dash, 
            x="Entidade", 
            y=["Militar", "Magia", "Economia", "Influencia"], 
            barmode="group",
            title="Militar vs Magia vs Economia",
            color_discrete_sequence=["#e63946", "#a8dadc", "#e6c200", "#457b9d"] # Vermelho, Azul claro, Ouro, Azul
        )
        fig_bar.update_layout(
            font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22",
            legend_title_text='Atributo'
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
        c1, c2 = st.columns(2)
        
        with c1:
            # 2. Gráfico de Pizza (Influência Total)
            st.subheader("🌍 Dominância Global (Influência)")
            fig_pie = px.pie(
                df_dash, 
                values='Influencia', 
                names='Entidade', 
                title='Participação no Poder Político',
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.RdBu
            )
            fig_pie.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with c2:
            # 3. Gráfico de Radar (Spider)
            st.subheader("🕸️ Perfil das Facções")
            entidade_selecionada = st.selectbox("Ver Detalhes De:", df_dash["Entidade"].unique())
            
            dados_entidade = df_dash[df_dash["Entidade"] == entidade_selecionada].iloc[0]
            
            # Prepara dados para Radar
            categorias_radar = ["Militar", "Magia", "Economia", "Influencia"]
            valores_radar = [dados_entidade[c] for c in categorias_radar]
            
            fig_radar = px.line_polar(
                r=valores_radar, 
                theta=categorias_radar, 
                line_close=True,
                range_r=[0, 100]
            )
            fig_radar.update_traces(fill='toself', line_color='#e6c200')
            fig_radar.update_layout(
                font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117",
                polar=dict(bgcolor="#161b22", radialaxis=dict(visible=True, range=[0, 100]))
            )
            st.plotly_chart(fig_radar, use_container_width=True)

# === ABA 11: MAPA ===
with tab_mapa:
    st.header("🗺️ Cartografia")
    mapa_b64 = carregar_mapa()
    if mapa_b64: st.image(base64.b64decode(mapa_b64), caption="Mapa Mundi", use_container_width=True)
    else: st.info("Sem mapa.")
    st.markdown("---")
    arquivo_mapa = st.file_uploader("Upload", type=["jpg", "jpeg", "png", "webp"])
    if arquivo_mapa:
        if st.button("📤 Enviar para a Nuvem"):
            try:
                b64_string = comprimir_imagem(arquivo_mapa)
                salvar_mapa_b64(b64_string)
                st.success("Salvo!")
                st.rerun()
            except Exception as e: st.error(str(e))
