import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
import urllib.parse
import random
# --- IMPORT NOVO PARA O GRAFO ---
from streamlit_agraph import agraph, Node, Edge, Config
from epicbrain_panel import render_epicbrain_panel
from epicserver_panel import render_epicserver_panel

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL
# ==============================================================================
st.set_page_config(
    page_title="World Architect Pro", 
    layout="wide", 
    page_icon="🏰",
    initial_sidebar_state="expanded"
)

def aplicar_estilo_visual():
    st.markdown("""
    <style>
        /* Importação de Fontes: Cinzel (Medieval) e Lato (Leitura) */
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap');
        
        /* --- GERAL --- */
        .stApp {
            background-color: #0e1117;
            background-image: radial-gradient(circle at 50% 0, #1c2331, #0e1117);
            color: #d4d4d4;
            font-family: 'Lato', sans-serif;
        }
        
        /* --- TÍTULOS --- */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Cinzel', serif;
            color: #e6c200 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-weight: 700;
        }
        
        /* --- BARRA LATERAL --- */
        [data-testid="stSidebar"] {
            background-color: #11141a;
            border-right: 1px solid #30363d;
        }
        
        /* --- INPUTS --- */
        .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #161b22 !important;
            color: #e6e6e6 !important;
            border: 1px solid #30363d !important;
            font-family: 'Lato', sans-serif;
            border-radius: 8px;
        }
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: #e6c200 !important;
            box-shadow: 0 0 8px rgba(230, 194, 0, 0.3);
        }
        
        /* --- BOTÕES --- */
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
            width: 100%;
        }
        .stButton > button:hover {
            background: linear-gradient(180deg, #e6c200 0%, #b39700 100%);
            color: #0e1117 !important;
            box-shadow: 0 0 15px rgba(230, 194, 0, 0.6);
            transform: translateY(-2px);
            border-color: #fff !important;
        }
        
        /* --- TOAST --- */
        div[data-testid="stToast"] {
            background-color: #161b22;
            border: 1px solid #e6c200;
            color: #e6c200;
            font-family: 'Cinzel', serif;
        }
        
        /* --- ABAS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            border-bottom: 1px solid #30363d;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-radius: 4px 4px 0 0;
            color: #8b949e;
            font-family: 'Cinzel', serif;
        }
        .stTabs [aria-selected="true"] {
            background-color: #161b22;
            color: #e6c200;
            border: 1px solid #e6c200;
            border-bottom: none;
        }

        /* --- CARDS DE NPC --- */
        .npc-card {
            background-color: #1f2937;
            border: 1px solid #e6c200;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }
        .npc-img-container {
            flex-shrink: 0;
        }
        .npc-avatar {
            width: 100px;
            height: 100px;
            border-radius: 8px;
            object-fit: cover;
            border: 2px solid #e6c200;
            transition: transform 0.2s;
            cursor: pointer;
        }
        .npc-avatar:hover {
            transform: scale(1.05);
        }
        .npc-content {
            flex-grow: 1;
        }
        .npc-header {
            font-family: 'Cinzel', serif;
            font-size: 1.4em;
            color: #e6c200;
            border-bottom: 1px solid #444;
            padding-bottom: 8px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .npc-sub {
            font-size: 0.7em;
            color: #aaa;
            font-family: 'Lato';
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-left: 10px;
        }
        .npc-body {
            font-size: 0.95em;
            color: #ddd;
            line-height: 1.6;
        }
        .npc-label {
            color: #e6c200;
            font-weight: bold;
            font-size: 0.9em;
            margin-right: 5px;
        }
        .npc-lore {
            margin-top: 10px;
            font-style: italic;
            color: #bbb;
            background: rgba(0,0,0,0.2);
            padding: 10px;
            border-radius: 6px;
            border-left: 3px solid #e6c200;
        }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()

# ==============================================================================
# 2. DADOS E CONSTANTES DO RPG
# ==============================================================================

CATEGORIAS = [
    "Absencia - Caos", "Radiancia - Ordem", "Warp", "Os 4 Cavaleiros",
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    "Timeline - Cataclisma", "Timeline - Badlands", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

CULTURAS = [
    "Aiglana", "Har'oloth", "Povos do Leste", "Björska", 
    "Alüriel", "Badûran", "Gulthrak", "Polkinea"
]


# ==============================================================================
# 3. INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if "sugestoes_ia" not in st.session_state:
    st.session_state.sugestoes_ia = {}
if "erros_ia" not in st.session_state:
    st.session_state.erros_ia = {}
if "resumo_erros" not in st.session_state:
    st.session_state.resumo_erros = ""
if "auditoria_dados" not in st.session_state:
    st.session_state.auditoria_dados = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "glossario" not in st.session_state:
    st.session_state.glossario = {}
if "timeline_dados" not in st.session_state:
    st.session_state.timeline_dados = []
if "dashboard_dados" not in st.session_state:
    st.session_state.dashboard_dados = []
if "mapa_pins" not in st.session_state:
    st.session_state.mapa_pins = []
if "npcs" not in st.session_state:
    st.session_state.npcs = []
    
# Variáveis temporárias para NPC
if "temp_npc_nome" not in st.session_state:
    st.session_state.temp_npc_nome = ""
if "temp_npc_img" not in st.session_state:
    st.session_state.temp_npc_img = ""
if "temp_npc_lore" not in st.session_state:
    st.session_state.temp_npc_lore = ""

# ==============================================================================
# 4. CONEXÃO COM O FIREBASE
# ==============================================================================
# ==============================================================================
# 4. CONEXÃO COM O FIREBASE
# ==============================================================================
FIREBASE_AVAILABLE = False
db = None

if not firebase_admin._apps:
    try:
        if "textkey" in st.secrets:
            key_dict = json.loads(st.secrets["textkey"])
            cred = credentials.Certificate(key_dict)
            firebase_admin.initialize_app(cred)
            FIREBASE_AVAILABLE = True
        else:
            st.warning("⚠️ Segredo 'textkey' não encontrado. Modo offline ativado.")
    except Exception as e:
        st.warning(f"⚠️ Aviso: Firebase não conectado. Modo offline ativado. Erro: {e}")
else:
    FIREBASE_AVAILABLE = True

if FIREBASE_AVAILABLE:
    try:
        db = firestore.client()
    except Exception as e:
        st.warning(f"⚠️ Erro ao conectar ao Firestore: {e}")
        FIREBASE_AVAILABLE = False
        db = None

# ==============================================================================
# 5. FUNÇÕES AUXILIARES
# ==============================================================================

def enviar_alerta_email(categoria_alterada):
    if "email" not in st.secrets: return False
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        usuario = st.secrets["email"]["usuario"]
        senha = st.secrets["email"]["senha"]
        destinatario = st.secrets["email"]["destinatario"]
        msg = MIMEMultipart()
        msg['From'] = usuario
        msg['To'] = destinatario
        msg['Subject'] = f"🔔 Alteração: {categoria_alterada}"
        fuso = pytz.timezone('America/Sao_Paulo')
        hora = datetime.now(fuso).strftime("%d/%m/%Y às %H:%M")
        texto = f"A seção '{categoria_alterada}' foi modificada e salva no banco de dados às {hora}."
        msg.attach(MIMEText(texto, 'plain'))
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(usuario, senha)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

# --- LORE ---
def carregar_lore():
    if not FIREBASE_AVAILABLE or not db:
        return {cat: "" for cat in CATEGORIAS}
        
    try:
        doc_ref = db.collection("mundos").document("lore_oficial")
        doc = doc_ref.get()
        if doc.exists: return doc.to_dict()
        else:
            dados_iniciais = {cat: "" for cat in CATEGORIAS}
            doc_ref.set(dados_iniciais)
            return dados_iniciais
    except:
        return {cat: "" for cat in CATEGORIAS}

def salvar_categoria(categoria, texto):
    if not FIREBASE_AVAILABLE or not db:
        st.warning("⚠️ Modo offline: Alterações não serão salvas na nuvem.")
        return
        
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc_ref.set({categoria: texto}, merge=True)
    enviar_alerta_email(categoria)

# --- NPCs ---
def carregar_npcs():
    if not FIREBASE_AVAILABLE or not db: return []
    
    try:
        doc = db.collection("mundos").document("npc_database").get()
        if doc.exists: return doc.to_dict().get("lista", [])
        return []
    except: return []

def salvar_npc(novo_npc):
    if not FIREBASE_AVAILABLE or not db:
        st.warning("⚠️ Modo offline: NPC não salvo.")
        return

    npcs = carregar_npcs()
    npcs.append(novo_npc)
    db.collection("mundos").document("npc_database").set({"lista": npcs})

def deletar_npc_index(index):
    if not FIREBASE_AVAILABLE or not db: return

    npcs = carregar_npcs()
    if 0 <= index < len(npcs):
        npcs.pop(index)
        db.collection("mundos").document("npc_database").set({"lista": npcs})

# --- MAPAS E CACHE ---
def salvar_mapa_b64(b64_string):
    if not FIREBASE_AVAILABLE or not db: return
    db.collection("mundos").document("mapa_oficial").set({"imagem_b64": b64_string})

def carregar_mapa():
    if not FIREBASE_AVAILABLE or not db: return None
    try:
        doc = db.collection("mundos").document("mapa_oficial").get()
        if doc.exists: return doc.to_dict().get("imagem_b64", None)
        return None
    except: return None

def carregar_pins():
    if not FIREBASE_AVAILABLE or not db: return []
    try:
        doc = db.collection("mundos").document("mapa_pins").get()
        if doc.exists: return doc.to_dict().get("lista", [])
        return []
    except: return []

def salvar_pins(lista_pins):
    if not FIREBASE_AVAILABLE or not db: return
    db.collection("mundos").document("mapa_pins").set({"lista": lista_pins})

def carregar_cache_analises():
    if not FIREBASE_AVAILABLE or not db: return {}
    try:
        doc = db.collection("mundos").document("cache_analises").get()
        if doc.exists: return doc.to_dict()
        return {}
    except: return {}

def salvar_cache_analise(tipo, dados):
    if not FIREBASE_AVAILABLE or not db: return
    doc_ref = db.collection("mundos").document("cache_analises")
    doc_ref.set({tipo: dados}, merge=True)

# --- RELACIONAMENTOS (GRAPH) - NOVO ---
def carregar_relacoes():
    if not FIREBASE_AVAILABLE or not db: return []
    try:
        doc = db.collection("mundos").document("relacoes_graph").get()
        if doc.exists:
            return doc.to_dict().get("lista", [])
        return []
    except: return []

def salvar_relacoes(lista):
    if not FIREBASE_AVAILABLE or not db: return
    db.collection("mundos").document("relacoes_graph").set({"lista": lista})

def adicionar_relacao(origem, destino, tipo, cor):
    rels = carregar_relacoes()
    # Evita duplicatas exatas
    novo = {"source": origem, "target": destino, "type": tipo, "color": cor}
    if novo not in rels:
        rels.append(novo)
        salvar_relacoes(rels)
        return True
    return False

def deletar_relacao(idx):
    rels = carregar_relacoes()
    if 0 <= idx < len(rels):
        rels.pop(idx)
        salvar_relacoes(rels)

# --- UTILS ---
def extrair_json(texto):
    try:
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except: return None

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

# ==============================================================================
# 6. CARREGAMENTO INICIAL
# ==============================================================================
caches_salvos = carregar_cache_analises()

if not st.session_state.sugestoes_ia: st.session_state.sugestoes_ia = caches_salvos.get("sugestoes", {})
if not st.session_state.erros_ia: st.session_state.erros_ia = caches_salvos.get("erros", {})
if not st.session_state.resumo_erros: st.session_state.resumo_erros = caches_salvos.get("resumo_erros", "")
if not st.session_state.auditoria_dados: st.session_state.auditoria_dados = caches_salvos.get("auditoria", [])
if not st.session_state.messages: st.session_state.messages = caches_salvos.get("chat_history", [])
if not st.session_state.glossario: st.session_state.glossario = caches_salvos.get("glossario", {})
if not st.session_state.timeline_dados: st.session_state.timeline_dados = caches_salvos.get("timeline_dados", [])
if not st.session_state.dashboard_dados: st.session_state.dashboard_dados = caches_salvos.get("dashboard_dados", [])
if not st.session_state.mapa_pins: st.session_state.mapa_pins = carregar_pins()
if not st.session_state.npcs: st.session_state.npcs = carregar_npcs()

try: lore_data = carregar_lore()
except Exception as e: 
    st.error(f"Erro ao carregar Lore: {e}")
    lore_data = {cat: "" for cat in CATEGORIAS}

# ==============================================================================
# 7. BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.title("🏰 World Architect")
    st.header("⚙️ Configuração")
    api_key = st.text_input("Chave do Oráculo (API Key)", type="password")
    
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
                modelo_escolhido = st.selectbox("Cérebro da IA:", lista_modelos, index=0)
            
            if st.button("🕵️ Listar Todos os Modelos (Debug)"):
                st.write("--- Modelos Disponíveis ---")
                for m in genai.list_models():
                    st.write(f"**{m.name}**")
                    st.caption(f"Métodos: {m.supported_generation_methods}")
                st.write("---------------------------")

        except Exception as e: st.error(f"Erro ao listar modelos: {e}")

    st.divider()
    st.subheader("🔍 Busca Global")
    termo_busca = st.text_input("Procurar no Lore:", placeholder="Ex: Elfos")
    if termo_busca:
        resultados = []
        for cat, texto in lore_data.items():
            if termo_busca.lower() in texto.lower(): resultados.append(cat)
        if resultados:
            st.success(f"Encontrado em {len(resultados)} seções:")
            for r in resultados: st.caption(f"• {r}")
        else: st.warning("Termo não encontrado.")

# ==============================================================================
# 8. ABAS (ATUALIZADO COM TEIA E EPICBRAIN)
# ==============================================================================
abas = [
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", 
    "📚 Glossário", "📉 Timeline", "📊 Dashboards", "🗺️ Mapa", "🎲 NPCs", 
    "📜 Quests", "🕸️ Teia", "🎮 EpicBrain", "⚙️ Epic Server"
]

tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_timeline, tab_dashboard, tab_mapa, tab_npc, tab_quests, tab_teia, tab_epicbrain, tab_epicserver = st.tabs(abas)

# ==============================================================================
# ABA 1: EDITOR
# ==============================================================================
with tab_editor:
    col_titulo, col_filtro = st.columns([3, 1])
    with col_titulo:
        st.info("💾 As escrituras são salvas automaticamente nos arquivos etéreos (Nuvem).")
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
                        st.toast(f"Alterações em '{cat}' salvas com sucesso! Email enviado.", icon="📧")
                idx += 1
        st.divider()

    criar_secao_editor("📜 Documentos Gerais & Cosmologia", "Geral")
    criar_secao_editor("⏳ Timeline", "Timeline")
    criar_secao_editor("🏰 Povos", "Povo")

# ==============================================================================
# ABA 2: CHAT
# ==============================================================================
with tab_chat:
    c1, c2 = st.columns([4, 1])
    c1.header("🔮 Oráculo da Lore")
    if c2.button("🗑️ Limpar Chat"):
        st.session_state.messages = []
        salvar_cache_analise("chat_history", [])
        st.rerun()

    if not api_key:
        st.warning("O Oráculo precisa da Chave (API Key) na barra lateral.")
    else:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        if prompt := st.chat_input("Consulte os espíritos sobre seu mundo..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
            sys_prompt = f"""
            Você é o Guardião Sábio deste mundo de fantasia.
            Use APENAS o lore abaixo para responder.
            LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
            PERGUNTA DO USUÁRIO: {prompt}
            """
            
            with st.chat_message("assistant"):
                try:
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(sys_prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    salvar_cache_analise("chat_history", st.session_state.messages)
                except Exception as e:
                    st.error(f"Erro na IA: {e}")

# ==============================================================================
# ABA 3: AUDITORIA
# ==============================================================================
with tab_aval:
    st.header("⚖️ O Julgamento Final")
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.auditoria_dados:
            st.success("📂 Relatório recuperado da memória.")
            
        if st.button("🔄 Convocar Novo Julgamento (Modo Crítico)"):
            with st.spinner("O Juiz está analisando os autos..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_auditoria = f"""
                    VOCÊ É UM EDITOR LITERÁRIO SÊNIOR, CÍNICO E EXTREMAMENTE CRÍTICO.
                    SUA MISSÃO: Analisar o worldbuilding e DESTRUIR qualquer incoerência.
                    
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    
                    AVALIE 10 PILARES (Nota 0-10): Coerência, História, Cultura, Política, Economia, Magia, Religião, Geografia, Conflitos, Singularidade.
                    
                    FORMATO JSON OBRIGATÓRIO:
                    [
                        {{
                            "titulo": "1. Coerência Interna",
                            "nota": 4,
                            "analise": "Texto crítico e ácido.",
                            "melhorias": "Sugestão prática."
                        }},
                        ...
                    ]
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_auditoria)
                    dados = extrair_json(res.text)
                    if dados:
                        st.session_state.auditoria_dados = dados
                        salvar_cache_analise("auditoria", dados)
                        st.rerun()
                    else:
                        st.error("Erro na resposta da IA.")
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Erro: {e}")
        
        if st.session_state.auditoria_dados:
             for item in st.session_state.auditoria_dados:
                with st.expander(f"{item['titulo']} - Nota {item['nota']}"):
                    st.progress(item['nota']/10)
                    st.info(f"**Análise:** {item['analise']}")
                    st.warning(f"**Exigência:** {item['melhorias']}")

# ==============================================================================
# ABA 4: SUGESTÕES
# ==============================================================================
with tab_sugestao:
    st.header("💡 A Musa Inspiradora")
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.sugestoes_ia:
            st.success("📂 Inspirações recuperadas da memória.")
            
        if st.button("🔄 Pedir Novas Ideias (Tópicos Curtos)"):
            with st.spinner("Sonhando com seu mundo..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items()}
                    prompt = f"""
                    Atue como um Co-Autor Criativo.
                    TAREFA: Para CADA categoria listada abaixo, escreva 3 a 5 TÓPICOS (Bullet Points) de ideias novas.
                    LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    FORMATO JSON DE SAÍDA: {{ "Categoria": "• Ideia 1\\n• Ideia 2", ... }}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt)
                    dados = extrair_json(res.text)
                    if dados:
                        st.session_state.sugestoes_ia = dados
                        salvar_cache_analise("sugestoes", dados)
                        st.rerun()
                    else:
                        st.error("Erro JSON.")
                except Exception as e:
                    st.error(f"Erro: {e}")
    
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
                    sug = st.session_state.sugestoes_ia.get(cat, "Clique para gerar.")
                    st.text_area(f"💡 {cat}", value=sug, height=250, disabled=True)
                idx += 1
        st.divider()
        
    if st.session_state.sugestoes_ia:
        criar_secao_sugestao("Geral", "Geral")
        criar_secao_sugestao("Timeline", "Timeline")
        criar_secao_sugestao("Povos", "Povo")

# ==============================================================================
# ABA 5: INCOERÊNCIAS
# ==============================================================================
with tab_erros:
    st.header("⚡ O Inquisidor Lógico")
    with st.expander("📘 Metodologia", expanded=False):
        st.markdown("Cruzamento de dados N x N.")

    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.erros_ia:
            st.success("📂 Inquérito recuperado da memória.")
            
        if st.button("🔄 Iniciar Caça às Bruxas (Contradições)"):
            with st.spinner("O Inquisidor afia suas lâminas..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_erros = f"""
                    VOCÊ É UM INVESTIGADOR FORENSE DE LÓGICA.
                    TAREFA: Cruze TODOS os dados. Se A contradiz B, aponte. Use Bullet Points.
                    FORMATO JSON: 
                    {{ 
                        "resumo_geral": "Veredito ácido...", 
                        "detalhes": {{ "Categoria": "• 🔴 ERRO CRÍTICO: ...", ... }} 
                    }}
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
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
                    else:
                        st.write(res.text)
                except Exception as e:
                    st.error(f"Erro: {e}")

    if st.session_state.resumo_erros:
        st.info(f"📝 **Veredito Implacável:**\n\n{st.session_state.resumo_erros}")

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
                    if erro:
                        st.error(f"🚨 **PROBLEMAS:**\n\n{erro}")
                    else:
                        st.success("✅ Aprovado")
                idx += 1
        st.divider()
        
    if st.session_state.erros_ia:
        criar_secao_erros("Geral", "Geral")
        criar_secao_erros("Timeline", "Timeline")
        criar_secao_erros("Povos", "Povo")

# ==============================================================================
# ABA 6: GLOSSÁRIO
# ==============================================================================
with tab_glossario:
    st.header("📚 O Grande Arquivo")
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        c_btn, c_info = st.columns([1, 3])
        with c_btn:
            if st.button("🔄 Reescrever Dicionário"):
                with st.spinner("Catalogando termos..."):
                    try:
                        lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                        prompt = f"""
                        Bibliotecário. Extraia termos importantes (Nomes, Cidades, Magias). Definição curta.
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
            if st.session_state.glossario:
                st.info(f"Verbetes Catalogados: {len(st.session_state.glossario)}")

    st.divider()
    c_leitor, c_termos = st.columns([2, 1])
    with c_leitor:
        txt_escolhido = st.selectbox("Ler Pergaminho:", CATEGORIAS)
        conteudo = lore_data.get(txt_escolhido, "")
        st.text_area("Leitura:", value=conteudo, height=600, disabled=True)
    with c_termos:
        st.subheader("🔍 Notas de Rodapé")
        if st.session_state.glossario and conteudo:
            encontrados = [(t, d) for t, d in st.session_state.glossario.items() if t in conteudo]
            if encontrados:
                for t, d in encontrados:
                    with st.expander(f"🔹 {t}"): st.write(d)
            else:
                st.info("Nenhum termo encontrado.")

# ==============================================================================
# ABA 7: TIMELINE VISUAL
# ==============================================================================
with tab_timeline:
    st.header("📉 A Marcha do Tempo")
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.timeline_dados:
            st.success("📂 Cronologia recuperada.")
        if st.button("🔄 Gerar Gráfico Temporal"):
            with st.spinner("Calculando eras..."):
                try:
                    lore_timelines = {k:v for k,v in lore_data.items() if "Timeline" in k and v.strip()}
                    prompt_time = f"""
                    Analise Timelines. Extraia eventos.
                    SAIDA JSON: [{{ "ano_numerico": 100, "data_exibicao": "Ano 100", "evento": "Guerra X", "grupo": "Elfos" }}]
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
                    df, x="ano_numerico", y="grupo", 
                    hover_name="data_exibicao", 
                    hover_data={"ano_numerico": False, "grupo": False, "evento": True}, 
                    color="grupo", title="Linha do Tempo (Passe o mouse)", height=600, size_max=15
                )
                fig.update_traces(marker=dict(size=14, line=dict(width=2, color='#e6c200')))
                fig.update_layout(
                    font_family="Lato", font_color="#d4d4d4", 
                    title_font_family="Cinzel", title_font_color="#e6c200",
                    paper_bgcolor="#0e1117", plot_bgcolor="#161b22", 
                    xaxis=dict(gridcolor="#30363d"), yaxis=dict(gridcolor="#30363d")
                )
                st.plotly_chart(fig, use_container_width=True)
            else: st.warning("Sem dados.")
        except Exception as e: st.error(f"Erro gráfico: {e}")

# ==============================================================================
# ABA 8: DASHBOARDS
# ==============================================================================
with tab_dashboard:
    st.header("📊 Sala de Guerra")
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.dashboard_dados:
            st.success("📂 Dados táticos recuperados.")
        if st.button("🔄 Calcular Balança de Poder"):
            with st.spinner("O Estrategista está avaliando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_dash = f"""
                    Estrategista Militar. Avalie 6-10 facções. Dê notas 0-100: Militar, Magia, Economia, Influencia.
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
        fig_bar.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig_bar, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌍 Influência")
            fig_pie = px.pie(df_dash, values='Influencia', names='Entidade', title='Poder Político', hole=0.4)
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

# ==============================================================================
# ABA 9: MAPA INTERATIVO (COM PINS 📍 E EXCLUSÃO)
# ==============================================================================
with tab_mapa:
    st.header("🗺️ Cartografia Oficial")
    
    # Controles Superiores
    col_ctrl, col_upload = st.columns([3, 1])
    with col_ctrl:
        # Alterna entre ver o mapa bonito ou clicar para editar
        modo_mapa = st.radio("Modo:", ["👁️ Explorar (Zoom/Hover)", "📍 Editar (Adicionar/Remover)"], horizontal=True)
    
    mapa_b64 = carregar_mapa()
    
    if mapa_b64:
        # Decodifica a imagem do banco
        img_bytes = base64.b64decode(mapa_b64)
        img_pil = Image.open(io.BytesIO(img_bytes))
        
        # --- MODO EXPLORADOR (Visualização com Zoom) ---
        if modo_mapa == "👁️ Explorar (Zoom/Hover)":
            if st.session_state.mapa_pins:
                df_pins = pd.DataFrame(st.session_state.mapa_pins)
                
                # Cria o gráfico
                fig = px.scatter(
                    df_pins, 
                    x="x", y="y", 
                    hover_name="nome", 
                    hover_data={"x":False, "y":False, "desc":True}, 
                    title="Mapa Interativo"
                )
                
                # Configura o Pin como Emoji Grande 📍
                fig.update_traces(
                    mode="text",          
                    text="📍",            
                    textfont_size=35,     
                    textposition="top center", 
                    hoverlabel=dict(bgcolor="#0e1117", bordercolor="#e6c200", font_size=14, font_family="Lato")
                )
                
                # Imagem de fundo
                fig.add_layout_image(
                    dict(
                        source=img_pil, xref="x", yref="y", x=0, y=0, 
                        sizex=img_pil.width, sizey=img_pil.height, 
                        sizing="stretch", opacity=1, layer="below"
                    )
                )
                
                # Ajustes visuais (remove eixos)
                fig.update_xaxes(visible=False, range=[0, img_pil.width])
                fig.update_yaxes(visible=False, range=[img_pil.height, 0]) 
                fig.update_layout(
                    width=img_pil.width, height=img_pil.height, 
                    margin=dict(l=0, r=0, t=0, b=0), 
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    dragmode="pan"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.image(img_pil, caption="Mapa sem pins cadastrados.", use_container_width=True)
        
        # --- MODO EDITOR (Adicionar e Remover) ---
        else:
            st.info("📍 Clique no mapa para criar um ponto. Use a lista abaixo para remover.")
            
            # Captura o clique
            coords = streamlit_image_coordinates(img_pil, key="click_map")
            
            # 1. FORMULÁRIO DE ADICIONAR
            if coords:
                st.markdown(f"**Ponto Selecionado:** X={coords['x']}, Y={coords['y']}")
                with st.form("pin_form"):
                    st.subheader("📌 Novo Local")
                    nome_pin = st.text_input("Nome do Local")
                    desc_pin = st.text_area("Descrição")
                    vinculo = st.selectbox("Vincular a Texto (Opcional):", ["Nenhum"] + CATEGORIAS)
                    
                    if st.form_submit_button("💾 Salvar Pin"):
                        if vinculo != "Nenhum":
                            txt_completo = lore_data.get(vinculo, "")
                            resumo = txt_completo[:150] + "..." if len(txt_completo) > 150 else txt_completo
                            if not desc_pin: desc_pin = resumo
                        
                        novo_pin = {"x": coords['x'], "y": coords['y'], "nome": nome_pin, "desc": desc_pin}
                        
                        pins = st.session_state.mapa_pins
                        pins.append(novo_pin)
                        salvar_pins(pins) # Salva no Banco
                        st.session_state.mapa_pins = pins
                        st.success("Pin criado!")
                        st.rerun()

            st.divider()
            
            # 2. LISTA DE GERENCIAMENTO (APAGAR PINS)
            with st.expander("🗑️ Gerenciar Pins Existentes (Excluir)", expanded=True):
                if not st.session_state.mapa_pins:
                    st.caption("Nenhum pin para apagar.")
                else:
                    # Cria uma tabela visual simples
                    st.markdown("### Lista de Locais")
                    for i, pin in enumerate(st.session_state.mapa_pins):
                        c_nome, c_coords, c_btn = st.columns([3, 2, 1])
                        
                        with c_nome:
                            st.write(f"**{i+1}. {pin['nome']}**")
                        with c_coords:
                            st.caption(f"X: {pin['x']} | Y: {pin['y']}")
                        with c_btn:
                            # Botão de Apagar
                            if st.button("🗑️", key=f"del_pin_{i}", help=f"Apagar {pin['nome']}"):
                                # Remove da lista
                                lista_atual = st.session_state.mapa_pins
                                removido = lista_atual.pop(i)
                                
                                # Atualiza Banco e Session
                                salvar_pins(lista_atual)
                                st.session_state.mapa_pins = lista_atual
                                
                                st.toast(f"Local '{removido['nome']}' removido!", icon="🗑️")
                                st.rerun()
    else:
        st.warning("⚠️ Nenhum mapa carregado.")

    # --- UPLOAD NO RODAPÉ ---
    st.markdown("---")
    with st.expander("🗺️ Trocar Imagem do Mapa"):
        arquivo_mapa = st.file_uploader("Upload Imagem", type=["jpg", "png", "webp"])
        if arquivo_mapa:
            if st.button("📤 Substituir Mapa"):
                try:
                    b64 = comprimir_imagem(arquivo_mapa)
                    salvar_mapa_b64(b64)
                    st.success("Mapa atualizado!")
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")
                    
# ==============================================================================
# ABA 10: NPCs (VERSÃO FINAL - BOTÃO REMOVER FOTO + REGRAS)
# ==============================================================================
with tab_npc:
    st.header("🎲 Banco de NPCs")
    
    # Layout: Coluna de Criação (Esquerda) | Coluna de Lista (Direita)
    c_criar, c_lista = st.columns([1, 1.5])
    
    with c_criar:
        st.subheader("🛠️ Criar NPC")
        
        # --- 1. CONFIGURAÇÃO (Gênero -> Cultura -> Raça) ---
        
        # GÊNERO
        genero_npc = st.radio("Gênero", ["Masculino", "Feminino"], horizontal=True)
        
        # CULTURA
        culturas_rpg = [
            "Império de Aiglana", 
            "Povo do Leste", 
            "Gulthrak (Horda)", 
            "Har'oloth (Subterrâneo)", 
            "Badûran (Fortaleza)",
            "Alüriel (Reino Élfico)",
            "Björska (Nortenhos)",
            "Polkinea/Pequenilho"
        ]
        cultura_sel = st.selectbox("Cultura", culturas_rpg)

        # RAÇA (Lógica de Travamento)
        todas_racas = ["Humano", "Elfo", "Anão", "Orc", "Drow", "Pequenilho"]
        
        # Mapa: Se escolher a cultura X, a raça trava em Y
        mapa_raca_travada = {
            "Gulthrak (Horda)": ["Orc"],
            "Har'oloth (Subterrâneo)": ["Drow"],
            "Badûran (Fortaleza)": ["Anão"],
            "Alüriel (Reino Élfico)": ["Elfo"],
            "Björska (Nortenhos)": ["Humano"],
            "Polkinea/Pequenilho": ["Pequenilho"]
        }
        
        # Impérios (Aiglana e Leste) liberam todas. O resto obedece o mapa.
        if cultura_sel in ["Império de Aiglana", "Povo do Leste"]:
            lista_racas_disp = todas_racas
            travado = False
            msg_raca = "🔓 Império: Todas as raças permitidas."
        else:
            lista_racas_disp = mapa_raca_travada.get(cultura_sel, todas_racas)
            travado = True
            msg_raca = None

        raca_sel = st.selectbox("Raça", lista_racas_disp, disabled=travado)
        if msg_raca: st.caption(msg_raca)

        # --- 2. CLASSE (Lógica de Exclusividade) ---
        
        lista_classes_total = [
            # Sábio
            "Necromante", "Clérigo", "Druida", "Magus", "Dançarino das Sombras (Caster)", 
            "Xamã", "Granadeiro", "Lâmina Arcana", "Arqueiro Arcano", "Engenheiro de Artilharia", "Valsharess",
            # Guerreiro
            "Arqueiro", "Caçador", "Combatente", "Defensor", "Paladino", "Aklat'tur", 
            "Bárbaro", "Monge", "Samurai", "Mutante", "Construtor de Barcos",
            # Ladino
            "Malandro Arcano", "Caçador de Tesouros", "Assassino", "Esgrimista", "Ladrão", 
            "Espião", "Vivisseccionista", "Bardo", "Dançarino das Sombras (Ladino)", 
            "Caçador de Demônios", "Trilha-Curta"
        ]

        # Regras de quem possui qual classe
        regras_exclusivas = {
            "Xamã": ["Gulthrak (Horda)"],
            "Aklat'tur": ["Gulthrak (Horda)"],
            "Dançarino das Sombras (Caster)": ["Har'oloth (Subterrâneo)"],
            "Dançarino das Sombras (Ladino)": ["Har'oloth (Subterrâneo)"],
            "Valsharess": ["Har'oloth (Subterrâneo)"],
            "Engenheiro de Artilharia": ["Badûran (Fortaleza)"],
            "Monge": ["Povo do Leste"],
            "Samurai": ["Povo do Leste"],
            "Arqueiro Arcano": ["Alüriel (Reino Élfico)"],
            "Trilha-Curta": ["Polkinea/Pequenilho"],
            "Construtor de Barcos": ["Björska (Nortenhos)"]
        }

        classes_filtradas = []
        for cls in lista_classes_total:
            donos = regras_exclusivas.get(cls)
            if donos:
                # É exclusiva: só mostra se a cultura atual for dona
                if cultura_sel in donos:
                    classes_filtradas.append(cls)
            else:
                # Não é exclusiva: mostra para todos
                classes_filtradas.append(cls)
        
        classes_filtradas.sort()
        classe_sel = st.selectbox("Classe", classes_filtradas)

        st.markdown("---")
        
        # --- 3. GERADORES (NOME E IMAGEM) ---
        col_gen1, col_gen2 = st.columns(2)
        
        with col_gen1:
            # Botão Gerar Nome
            if st.button("🎲 Gerar Nome"):
                if api_key:
                    try:
                        model = genai.GenerativeModel(modelo_escolhido)
                        p = f"""
                        Gere APENAS UM nome fantasia (sem explicações) para:
                        Gênero: {genero_npc}, Raça: {raca_sel}, Cultura: {cultura_sel}.
                        Convenções: Orcs=Gutural, Drow=Apóstrofos, Leste=Asiático, Björska=Nórdico.
                        """
                        st.session_state.temp_npc_nome = model.generate_content(p).text.strip().replace("*","").replace('"', '')
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro IA: {e}")
                else: st.warning("Sem API Key")
        
        with col_gen2:
            # Botão Gerar Imagem
            # Seletor de Modelo de Imagem
            provider_img = st.selectbox("Motor de Imagem", ["Flux (Pollinations)", "Nano Banana (Gemini 2.5)"])
            desc_vis = st.text_input("Aparência Extra (ex: cicatriz):")

            if st.button("📸 Retrato (200px)"):
                try:
                    gender_en = "Male" if genero_npc == "Masculino" else "Female"
                    
                    # Ajustes de tradução
                    race_en = raca_sel.split(" ")[0] 
                    if "Drow" in raca_sel: race_en = "Drow Dark Elf"
                    if "Pequenilho" in raca_sel: race_en = "Halfling"
                    if "Anão" in raca_sel: race_en = "Dwarf"
                    
                    prompt_img = f"D&D style portrait of a {gender_en} {race_en} {classe_sel}, {desc_vis}, detailed facial features, expressive eyes, strong fantasy mood, dramatic lighting, rich textures, high detail, hand-drawn look, subtle atmospheric background matching the creature’s origin — in the style of Greg Staples, hand drawn, fantasy, dynamic brushwork, d&d, packed with hidden detail, color, brushwork"
                    
                    if provider_img == "Flux (Pollinations)":
                        safe_prompt = urllib.parse.quote(prompt_img)
                        seed = random.randint(0, 999999)
                        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=200&height=200&nologo=true&model=flux&seed={seed}"
                        st.session_state.temp_npc_img = url
                        st.rerun()
                    
                    elif provider_img == "Nano Banana (Gemini 2.5)":
                        if not api_key:
                            st.warning("⚠️ Precisa da API Key configurada na barra lateral.")
                        else:
                            with st.spinner("Nano Banana está pintando..."):
                                model_img = genai.GenerativeModel("gemini-2-5-flash-image")
                                response = model_img.generate_content(prompt_img)
                                
                                # Tenta extrair a imagem da resposta (Inline Data)
                                if response.parts and response.parts[0].inline_data:
                                    img_data = response.parts[0].inline_data.data
                                    # img_data já é bytes, precisamos converter para b64 para exibir html ou salvar
                                    b64_img = base64.b64encode(img_data).decode('utf-8')
                                    mime_type = response.parts[0].inline_data.mime_type
                                    st.session_state.temp_npc_img = f"data:{mime_type};base64,{b64_img}"
                                    st.rerun()
                                else:
                                    st.error("O modelo não retornou uma imagem válida. Tente novamente ou verifique a API Key.")
                                    st.write(response.text) # Debug caso retorne texto de erro

                except Exception as e: 
                    st.error(f"Erro Imagem: {e}")

        # Campo Editável de Nome
        nome_final = st.text_input("Nome Final", value=st.session_state.temp_npc_nome)
        
        # --- EXIBIÇÃO DA IMAGEM COM BOTÃO DE REMOVER ---
        if st.session_state.temp_npc_img:
            st.markdown("---")
            col_img_show, col_img_btn = st.columns([1, 1])
            
            with col_img_show:
                # HTML para imagem 200x200 com borda dourada
                link_html = f'<a href="{st.session_state.temp_npc_img}" target="_blank"><img src="{st.session_state.temp_npc_img}" style="border-radius:8px; border: 2px solid #e6c200; width: 200px; height: 200px; object-fit: cover;"></a>'
                st.markdown(link_html, unsafe_allow_html=True)
                st.caption("Clique na imagem para baixar.")
            
            with col_img_btn:
                st.write("") # Espaçamento vertical para alinhar
                st.write("") 
                st.warning("Não gostou?")
                if st.button("❌ Remover Foto"):
                    st.session_state.temp_npc_img = "" # Limpa a variável
                    st.rerun() # Recarrega a tela limpa

        st.markdown("---")
        
        # --- 4. HISTÓRIA (LORE) ---
        st.markdown("##### História & Segredos")
        if st.button("✨ Escrever Lore Automática"):
            if api_key:
                try:
                    model = genai.GenerativeModel(modelo_escolhido)
                    p_lore = f"""
                    Crie um background curto (3 linhas) e um SEGREDO para este NPC.
                    Dados: {nome_final}, {genero_npc}, {raca_sel}, {classe_sel}, {cultura_sel}.
                    Tom: Sombrio/Grimdark.
                    """
                    st.session_state.temp_npc_lore = model.generate_content(p_lore).text
                    st.rerun()
                except Exception as e: 
                    st.error(f"Erro IA: {e}")
        
        # Campo Editável de Lore
        lore_final = st.text_area("Editar Lore/Segredo", value=st.session_state.temp_npc_lore, height=100)

        # --- 5. BOTÃO SALVAR ---
        st.markdown("---")
        if st.button("💾 Salvar Ficha no Banco", type="primary"):
            novo_npc = {
                "nome": nome_final if nome_final else "Desconhecido", 
                "genero": genero_npc,
                "raca": raca_sel, 
                "classe": classe_sel, 
                "cultura": cultura_sel, 
                "segredo": lore_final,
                "img_url": st.session_state.temp_npc_img,
                "data_criacao": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            # Salva no Firebase
            salvar_npc(novo_npc)
            
            # Atualiza Session State localmente
            st.session_state.npcs.append(novo_npc)
            
            # Limpa os campos temporários para o próximo NPC
            st.session_state.temp_npc_nome = ""
            st.session_state.temp_npc_img = ""
            st.session_state.temp_npc_lore = ""
            
            st.success(f"{nome_final} cadastrado com sucesso!")
            st.rerun()

    # --- COLUNA DA DIREITA: LISTA DE NPCs ---
    with c_lista:
        st.subheader(f"📜 Catálogo ({len(st.session_state.npcs)})")
        
        # Mostra lista invertida (mais recentes no topo)
        lista_invertida = list(reversed(st.session_state.npcs))
        
        for i, npc in enumerate(lista_invertida):
            # Índice original para deleção correta
            real_index = len(st.session_state.npcs) - 1 - i
            
            img_url = npc.get("img_url", "")
            
            # HTML do Avatar Pequeno na lista
            if img_url:
                img_html = f'<a href="{img_url}" target="_blank"><img src="{img_url}" class="npc-avatar" style="width:80px; height:80px;"></a>'
            else:
                img_html = '<div class="npc-avatar" style="width:80px; height:80px; background:#333; display:flex; align-items:center; justify-content:center;">👤</div>'
            
            # Card Estilizado
            st.markdown(f"""
            <div class="npc-card" style="padding: 15px; gap: 15px;">
                <div class="npc-img-container">{img_html}</div>
                <div class="npc-content">
                    <div class="npc-header" style="font-size: 1.2em;">
                        {npc.get('nome', 'Sem Nome')}
                    </div>
                    <div class="npc-sub" style="color:#e6c200; margin-bottom:5px;">
                        {npc.get('raca')} | {npc.get('classe')}
                    </div>
                    <div style="font-size: 0.8em; color: #aaa; margin-bottom: 8px;">
                        {npc.get('cultura')} • {npc.get('genero')}
                    </div>
                    <div class="npc-lore" style="font-size: 0.85em;">{npc.get('segredo', '')}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Botão de Deletar
            if st.button(f"🗑️ Apagar {npc.get('nome')}", key=f"del_{real_index}"):
                deletar_npc_index(real_index) 
                st.session_state.npcs.pop(real_index)
                st.rerun()
# ==============================================================================
# ABA 11: QUESTS (SEPARADA)
# ==============================================================================
with tab_quests:
    st.header("📜 Mural de Missões")
    col_q1, col_q2 = st.columns([1, 3])
    with col_q1:
        st.info("Gera ganchos de aventura baseados no Lore global.")
        if st.button("🎲 Gerar 5 Aventuras", type="primary"):
            if api_key:
                with st.spinner("Ouvindo boatos nas tavernas..."):
                    try:
                        l = {k:v for k,v in lore_data.items() if v.strip()}
                        p = f"""
                        Atue como Mestre de RPG. Crie 5 Ganchos de Aventura (Quests) baseados no lore abaixo.
                        Para cada quest:
                        - Título
                        - Sinopse
                        - Quem Contrata
                        - Recompensa
                        - Twist
                        LORE: {json.dumps(l, ensure_ascii=False)}
                        """
                        st.session_state.quest_result = genai.GenerativeModel(modelo_escolhido).generate_content(p).text
                    except: st.error("Erro IA")
            else: st.warning("API Key necessária")
            
    with col_q2:
        if "quest_result" in st.session_state:
            st.markdown(st.session_state.quest_result)

# ==============================================================================
# ABA 12: TEIA DE INTRIGAS (RELATIONSHIP GRAPH)
# ==============================================================================
with tab_teia:
    st.header("🕸️ Teia de Intrigas & Poder")
    st.caption("Visualização de grafos para análise de conexões políticas, alianças e rivalidades.")
    
    # Carrega dados
    npcs_existentes = st.session_state.npcs
    if not npcs_existentes:
        st.warning("Você precisa criar NPCs na aba '🎲 NPCs' primeiro.")
    else:
        # Cria lista de nomes para o selectbox
        lista_nomes = [n['nome'] for n in npcs_existentes]
        # Adiciona Facções (Hardcoded ou do Lore) para enriquecer o grafo
        lista_entidades = lista_nomes + CULTURAS + ["Rei/Imperador", "Deus/Entidade"]
        
        # --- 1. CONTROLE DE RELAÇÕES (ADICIONAR/REMOVER) ---
        with st.expander("🔗 Gerenciar Vínculos", expanded=False):
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
            
            with c1:
                origem = st.selectbox("Origem", lista_entidades, key="rel_origem")
            with c2:
                # Remove a origem da lista de destino para evitar auto-relação
                destinos_validos = [x for x in lista_entidades if x != origem]
                destino = st.selectbox("Destino", destinos_validos, key="rel_destino")
            with c3:
                tipo_rel = st.selectbox("Tipo de Relação", [
                    "🟢 Aliança / Amizade", 
                    "🔴 Ódio / Guerra", 
                    "🔵 Família / Sangue",
                    "🟣 Mestre / Servo",
                    "🟡 Comércio / Dívida"
                ])
            with c4:
                st.write("") # Espaço
                st.write("")
                if st.button("➕ Vincular"):
                    # Define cor baseada na escolha
                    cor_map = {
                        "🟢": "#00ff00", # Verde Matrix
                        "🔴": "#ff0000", # Vermelho Sangue
                        "🔵": "#00ccff", # Azul Cyan
                        "🟣": "#9900ff", # Roxo
                        "🟡": "#ffcc00"  # Ouro
                    }
                    cor_escolhida = cor_map.get(tipo_rel[0], "white")
                    texto_rel = tipo_rel.split(" ", 1)[1]
                    
                    adicionar_relacao(origem, destino, texto_rel, cor_escolhida)
                    st.toast(f"Vínculo {origem} -> {destino} criado!", icon="🔗")
                    st.rerun()

            # Lista para remover
            relacoes_atuais = carregar_relacoes()
            if relacoes_atuais:
                st.markdown("##### Vínculos Ativos")
                for i, rel in enumerate(relacoes_atuais):
                    cols = st.columns([4, 1])
                    with cols[0]:
                        st.caption(f"{rel['source']} ➡️ {rel['target']} ({rel['type']})")
                    with cols[1]:
                        if st.button("❌", key=f"del_rel_{i}"):
                            deletar_relacao(i)
                            st.rerun()

        # --- 2. VISUALIZAÇÃO DO GRAFO ---
        st.divider()
        
        # Construindo NÓS (Nodes)
        nodes = []
        ids_adicionados = set()
        
        # Adiciona nós baseados nas relações existentes (para não encher de npc solto)
        # Mas se quiser mostrar todos, use a lista de npcs
        
        # A) Adiciona NPCs com FOTOS
        for npc in npcs_existentes:
            # Só adiciona se o NPC tiver alguma relação ou se quisermos mostrar todos
            # Vamos mostrar todos os NPCs criados
            img = npc.get('img_url', "")
            # Se não tiver imagem, usa um placeholder ou nada
            if not img: img = "https://cdn-icons-png.flaticon.com/512/847/847969.png" # Icone genérico
            
            nodes.append(Node(
                id=npc['nome'], 
                label=npc['nome'], 
                size=25, 
                shape="circularImage", 
                image=img,
                borderWidth=3,
                color="#e6c200", # Borda Dourada
                title=f"{npc['raca']} | {npc['classe']}" # Tooltip
            ))
            ids_adicionados.add(npc['nome'])

        # B) Adiciona Nós que estão nas relações mas não são NPCs (ex: Facções, Deuses)
        for rel in relacoes_atuais:
            for entidade in [rel['source'], rel['target']]:
                if entidade not in ids_adicionados:
                    nodes.append(Node(
                        id=entidade,
                        label=entidade,
                        size=20,
                        shape="dot", # Bolinha normal para facções
                        color="#555555"
                    ))
                    ids_adicionados.add(entidade)

        # Construindo ARESTAS (Edges)
        edges = []
        for rel in relacoes_atuais:
            edges.append(Edge(
                source=rel['source'], 
                target=rel['target'], 
                label=rel['type'],
                color=rel['color'],
                width=2,
                arrows="to" # Seta direcional
            ))

        # Configuração Visual (Physics = True faz eles se mexerem)
        config = Config(
            width=1200, 
            height=600, 
            directed=True, 
            physics=True, 
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#e6c200",
            collapsible=False
        )

        # Renderiza
        if nodes:
            return_value = agraph(nodes=nodes, edges=edges, config=config)
        else:
            st.info("Adicione NPCs e crie vínculos para ver a teia.")

# ==============================================================================
# ABA 13: EPICBRAIN
# ==============================================================================
with tab_epicbrain:
    render_epicbrain_panel()

# ==============================================================================
# ABA 14: EPIC SERVER ANALYZER
# ==============================================================================
with tab_epicserver:
    render_epicserver_panel()

