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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import pytz
import urllib.parse

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL (CSS)
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
        
        /* --- CAIXAS DE TEXTO E INPUTS --- */
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
            border-radius: 8px; /* Quadrado arredondado para retrato */
            object-fit: cover;
            border: 2px solid #e6c200;
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
            border-left: 3px solid #555;
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
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()

# ==============================================================================
# 2. CONSTANTES E DADOS DE RPG
# ==============================================================================

# Categorias de Lore (Texto)
CATEGORIAS = [
    "Absencia - Caos", "Radiancia - Ordem", "Warp", "Os 4 Cavaleiros",
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    "Timeline - Cataclisma", "Timeline - Badlands", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

# Dados para o Gerador de NPC
CAMINHOS_RPG = {
    "Sabio": [
        "Necromante", "Clérigo", "Druida", "Magus", "Dançarino das Sombras Caster", 
        "Shaman / Xamã", "Granadeiro", "Lâmina Arcana", "Arqueiro Arcano", "Engenheiro de Artilharia"
    ],
    "Guerreiro": [
        "Arqueiro", "Caçador", "Combatente", "Defensor", "Paladino", 
        "Aklat'tur", "Bárbaro", "Monge", "Samurai", "Mutante"
    ],
    "Ladino": [
        "Malandro Arcano", "Caçador de Tesouros", "Assassino", "Esgrimista", 
        "Ladrao", "Espiao", "Vivisseccionista", "Bardo", "Dançarino das Sombras", "Caçador de demônios"
    ]
}

CULTURAS = [
    "Aiglana", "Har'oloth", "Povos do Leste", "Björska", 
    "Alüriel", "Badûran", "Gulthrak", "Polkinea"
]

RACAS = ["Anão", "Drow", "Elfo", "Orc", "Humano", "Polski"]

RELIGIOES = [
    "Veneratio", "Eluith'orth", "Kai", "Halleuad", 
    "Lórё", "Bokk Bharaz", "Ushkr'ar", "Céticos"
]

# ==============================================================================
# 3. INICIALIZAÇÃO DE ESTADO (SESSION STATE)
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
if "arvore_dot" not in st.session_state:
    st.session_state.arvore_dot = ""
if "timeline_dados" not in st.session_state:
    st.session_state.timeline_dados = []
if "dashboard_dados" not in st.session_state:
    st.session_state.dashboard_dados = []
if "grafo_dot" not in st.session_state:
    st.session_state.grafo_dot = ""
if "mapa_pins" not in st.session_state:
    st.session_state.mapa_pins = []
if "npcs" not in st.session_state:
    st.session_state.npcs = []
    
# Variáveis temporárias para criação de NPC (para não perder dados ao recarregar)
if "temp_npc_nome" not in st.session_state:
    st.session_state.temp_npc_nome = ""
if "temp_npc_img" not in st.session_state:
    st.session_state.temp_npc_img = ""
if "temp_npc_lore" not in st.session_state:
    st.session_state.temp_npc_lore = ""

# ==============================================================================
# 4. CONEXÃO COM O BANCO DE DADOS (FIREBASE)
# ==============================================================================
if not firebase_admin._apps:
    try:
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"❌ Erro Crítico nos Segredos (Secrets): {e}")
        st.stop()

db = firestore.client()

# ==============================================================================
# 5. FUNÇÕES AUXILIARES (LÓGICA DE NEGÓCIO)
# ==============================================================================

def enviar_alerta_email(categoria_alterada):
    """Envia e-mail de notificação via Gmail (Simples)."""
    if "email" not in st.secrets:
        return False
        
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        usuario = st.secrets["email"]["usuario"]
        senha = st.secrets["email"]["senha"]
        destinatario = st.secrets["email"]["destinatario"]

        msg = MIMEMultipart()
        msg['From'] = usuario
        msg['To'] = destinatario
        msg['Subject'] = f"🔔 World Architect: Alteração em {categoria_alterada}"
        
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

def carregar_lore():
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        dados_iniciais = {cat: "" for cat in CATEGORIAS}
        doc_ref.set(dados_iniciais)
        return dados_iniciais

def salvar_categoria(categoria, texto):
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc_ref.set({categoria: texto}, merge=True)
    enviar_alerta_email(categoria)

def carregar_cache_analises():
    doc_ref = db.collection("mundos").document("cache_analises")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {}

def salvar_cache_analise(tipo, dados):
    doc_ref = db.collection("mundos").document("cache_analises")
    doc_ref.set({tipo: dados}, merge=True)

def extrair_json(texto):
    try:
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except:
        return None

def extrair_dot(texto):
    try:
        match = re.search(r"```(?:dot|graphviz)\n(.*?)\n```", texto, re.DOTALL)
        if match:
            return match.group(1)
        if "digraph" in texto:
            inicio = texto.find("digraph")
            fim = texto.rfind("}") + 1
            return texto[inicio:fim]
        return None
    except:
        return None

# --- FUNÇÕES NPC ---
def carregar_npcs():
    doc = db.collection("mundos").document("npc_database").get()
    if doc.exists:
        return doc.to_dict().get("lista", [])
    return []

def salvar_npc(novo_npc):
    npcs = carregar_npcs()
    npcs.append(novo_npc)
    db.collection("mundos").document("npc_database").set({"lista": npcs})

def deletar_npc_index(index):
    npcs = carregar_npcs()
    if 0 <= index < len(npcs):
        npcs.pop(index)
        db.collection("mundos").document("npc_database").set({"lista": npcs})

# --- FUNÇÕES MAPA E IMAGEM ---
def salvar_mapa_b64(b64_string):
    db.collection("mundos").document("mapa_oficial").set({"imagem_b64": b64_string})

def carregar_mapa():
    doc = db.collection("mundos").document("mapa_oficial").get()
    if doc.exists:
        return doc.to_dict().get("imagem_b64", None)
    return None

def carregar_pins():
    doc = db.collection("mundos").document("mapa_pins").get()
    if doc.exists:
        return doc.to_dict().get("lista", [])
    return []

def salvar_pins(lista_pins):
    db.collection("mundos").document("mapa_pins").set({"lista": lista_pins})

def comprimir_imagem(arquivo_upload):
    image = Image.open(arquivo_upload)
    
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    
    # Redimensiona se for muito grande (max 1600px)
    max_width = 1600
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int((float(image.height) * float(ratio)))
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
    
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# ==============================================================================
# 6. CARREGAMENTO INICIAL (CACHE E BANCO)
# ==============================================================================
caches_salvos = carregar_cache_analises()

# Popula session_state com dados do banco se estiverem vazios
if not st.session_state.sugestoes_ia: 
    st.session_state.sugestoes_ia = caches_salvos.get("sugestoes", {})
if not st.session_state.erros_ia: 
    st.session_state.erros_ia = caches_salvos.get("erros", {})
if not st.session_state.resumo_erros: 
    st.session_state.resumo_erros = caches_salvos.get("resumo_erros", "")
if not st.session_state.auditoria_dados: 
    st.session_state.auditoria_dados = caches_salvos.get("auditoria", [])
if not st.session_state.messages: 
    st.session_state.messages = caches_salvos.get("chat_history", [])
if not st.session_state.glossario: 
    st.session_state.glossario = caches_salvos.get("glossario", {})
if not st.session_state.arvore_dot: 
    st.session_state.arvore_dot = caches_salvos.get("arvore_dot", "")
if not st.session_state.timeline_dados: 
    st.session_state.timeline_dados = caches_salvos.get("timeline_dados", [])
if not st.session_state.dashboard_dados: 
    st.session_state.dashboard_dados = caches_salvos.get("dashboard_dados", [])
if not st.session_state.grafo_dot: 
    st.session_state.grafo_dot = caches_salvos.get("grafo_dot", "")
if not st.session_state.mapa_pins:
    st.session_state.mapa_pins = carregar_pins()
if not st.session_state.npcs:
    st.session_state.npcs = carregar_npcs()

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro ao carregar Lore do Banco: {e}")
    st.stop()

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
        except Exception as e:
            st.error(f"Erro ao listar modelos: {e}")

    st.divider()
    
    # Busca Global
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
            st.warning("Termo não encontrado.")

# ==============================================================================
# 8. ESTRUTURA DE ABAS
# ==============================================================================
abas = [
    "✍️ Editor", 
    "🧠 Chat", 
    "⚖️ Auditoria", 
    "💡 Sugestões", 
    "⚡ Incoerências", 
    "📚 Glossário", 
    "🌳 Genealogia", 
    "🕸️ Conexões", 
    "📉 Timeline", 
    "📊 Dashboards", 
    "🗺️ Mapa",
    "🎲 NPC & Quests" # Aba movida para o final
]

tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_genealogia, tab_conexoes, tab_timeline, tab_dashboard, tab_mapa, tab_npc = st.tabs(abas)

# ==============================================================================
# ABA 1: EDITOR (COM EMAIL E ÍNDICE)
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
        # Lógica de filtro
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
                    # Altura de 500px
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
# ABA 2: CHAT (CACHEADO)
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
# ABA 3: AUDITORIA (CRÍTICA E CÍNICA)
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
                    SUA MISSÃO: Analisar o worldbuilding abaixo e DESTRUIR qualquer incoerência, clichê ou preguiça criativa.
                    Não seja educado. Seja realista.
                    
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    
                    AVALIE ESTES 10 PILARES (Nota 0-10):
                    1. Coerência Interna
                    2. Profundidade Histórica
                    3. Cultura e Antropologia
                    4. Sistema Político
                    5. Economia e Recursos
                    6. Magia/Tecnologia
                    7. Religião e Metafísica
                    8. Ecologia e Geografia
                    9. Conflitos Atuais
                    10. Singularidade
                    
                    FORMATO JSON OBRIGATÓRIO:
                    [
                        {{
                            "titulo": "1. Coerência Interna",
                            "nota": 4,
                            "analise": "Texto crítico e ácido explicando por que está ruim ou bom.",
                            "melhorias": "Sugestão prática para consertar."
                        }},
                        ... repita para os 10 itens ...
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
                        st.error("A IA não retornou um JSON válido.")
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
# ABA 4: SUGESTÕES (BULLET POINTS)
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
                    TAREFA: Para CADA categoria listada abaixo, escreva 3 a 5 TÓPICOS (Bullet Points) de ideias novas, plot twists ou segredos.
                    Seja breve e direto.
                    
                    LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    
                    FORMATO JSON DE SAÍDA: 
                    {{ 
                        "Nome da Categoria": "• Ideia 1\\n• Ideia 2\\n• Ideia 3", 
                        ... 
                    }}
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
        st.markdown("Cruzamento de dados N x N para encontrar falhas cronológicas e lógicas.")

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
                    Não seja "bonzinho". Seu trabalho é achar falhas.
                    
                    TAREFA: 
                    1. Cruze TODOS os dados.
                    2. Se A contradiz B, aponte.
                    3. Use Bullet Points.
                    
                    FORMATO JSON: 
                    {{ 
                        "resumo_geral": "Veredito ácido sobre a consistência geral...", 
                        "detalhes": {{ 
                            "Nome da Categoria": "• 🔴 ERRO CRÍTICO: ...\\n• 🟡 ALERTA: ...", 
                            ... 
                        }} 
                    }}
                    
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
                        st.success("✅ Aprovado pelo Inquisidor")
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
                        Atue como Bibliotecário. Extraia termos importantes (Nomes, Cidades, Magias).
                        Definição curta (1 frase).
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
    
    # Leitor Contextual
    c_leitor, c_termos = st.columns([2, 1])
    with c_leitor:
        txt_escolhido = st.selectbox("Ler Pergaminho:", CATEGORIAS)
        conteudo = lore_data.get(txt_escolhido, "")
        st.text_area("Leitura:", value=conteudo, height=600, disabled=True)
    
    with c_termos:
        st.subheader("🔍 Notas de Rodapé")
        if not st.session_state.glossario:
            st.warning("Gere o glossário primeiro!")
        elif not conteudo:
            st.write("...")
        else:
            encontrados = [(t, d) for t, d in st.session_state.glossario.items() if t in conteudo]
            if encontrados:
                for t, d in encontrados:
                    with st.expander(f"🔹 {t}"):
                        st.write(d)
            else:
                st.info("Nenhum termo mágico encontrado neste texto.")

# ==============================================================================
# ABA 7: GENEALOGIA
# ==============================================================================
with tab_genealogia:
    st.header("🌳 Linhagens e Alianças")
    
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.arvore_dot:
            st.success("📂 Diagrama recuperado.")
            
        if st.button("🔄 Desenhar Árvore"):
            with st.spinner("Traçando linhagens..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_genealogia = f"""
                    Atue como Genealogista.
                    Crie um código GRAPHVIZ DOT válido.
                    REGRAS:
                    - digraph G {{ rankdir=LR; bgcolor="#0e1117"; ... }}
                    - node [fontcolor="white" color="white" style=filled fillcolor="#333"];
                    - edge [color="gray"];
                    - Agrupe famílias em 'subgraph cluster_Nome {{ ... }}'
                    
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

# ==============================================================================
# ABA 8: CONEXÕES (DARK MODE FIX)
# ==============================================================================
with tab_conexoes:
    st.header("🕸️ Teia de Influência")
    
    if not api_key:
        st.warning("Insira a API Key.")
    else:
        if st.session_state.grafo_dot:
            st.success("📂 Rede carregada.")
            
        if st.button("🔄 Mapear Teia Política (Refinado)"):
            with st.spinner("Desenhando a teia..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    
                    prompt_grafo = f"""
                    Atue como um Designer de Informação.
                    TAREFA: Criar um Grafo de Conexões (DOT) para MODO ESCURO.
                    
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

# ==============================================================================
# ABA 9: TIMELINE VISUAL
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
# ABA 10: DASHBOARDS
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
                    Atue como um Estrategista Militar.
                    Leia o lore e identifique 6-10 facções. Dê notas 0-100: Militar, Magia, Economia, Influencia.
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
        fig_bar = px.bar(
            df_dash, x="Entidade", y=["Militar", "Magia", "Economia", "Influencia"], 
            barmode="group", title="Atributos",
            color_discrete_sequence=["#e63946", "#a8dadc", "#e6c200", "#457b9d"]
        )
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
# ABA 11: MAPA INTERATIVO
# ==============================================================================
with tab_mapa:
    st.header("🗺️ Cartografia Oficial")
    modo_mapa = st.radio("Modo:", ["👁️ Explorar (Zoom/Hover)", "📍 Editar (Adicionar Pins)"], horizontal=True)
    
    mapa_b64 = carregar_mapa()
    
    if mapa_b64:
        img_bytes = base64.b64decode(mapa_b64)
        img_pil = Image.open(io.BytesIO(img_bytes))
        
        if modo_mapa == "👁️ Explorar (Zoom/Hover)":
            if st.session_state.mapa_pins:
                df_pins = pd.DataFrame(st.session_state.mapa_pins)
                fig = px.scatter(
                    df_pins, x="x", y="y", hover_name="nome", 
                    hover_data={"x":False, "y":False, "desc":True}, 
                    title="Mapa Interativo"
                )
                fig.add_layout_image(dict(source=img_pil, xref="x", yref="y", x=0, y=0, sizex=img_pil.width, sizey=img_pil.height, sizing="stretch", opacity=1, layer="below"))
                fig.update_xaxes(visible=False, range=[0, img_pil.width])
                fig.update_yaxes(visible=False, range=[img_pil.height, 0])
                fig.update_layout(width=img_pil.width, height=img_pil.height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.image(img_pil, caption="Sem pins.", use_container_width=True)
        else:
            st.info("Clique na imagem para marcar um local.")
            coords = streamlit_image_coordinates(img_pil, key="click_map")
            if coords:
                with st.form("pin"):
                    nome_pin = st.text_input("Nome do Local")
                    desc_pin = st.text_area("Descrição")
                    vinculo = st.selectbox("Vincular a Texto:", ["Nenhum"] + CATEGORIAS)
                    if st.form_submit_button("💾 Salvar Pin"):
                        if vinculo != "Nenhum":
                            txt = lore_data.get(vinculo, "")[:200] + "..."
                            if not desc_pin: desc_pin = txt
                        pins = st.session_state.mapa_pins
                        pins.append({"x": coords['x'], "y": coords['y'], "nome": nome_pin, "desc": desc_pin})
                        salvar_pins(pins)
                        st.session_state.mapa_pins = pins
                        st.success("Pin salvo!")
                        st.rerun()
    else:
        st.info("Sem mapa.")

    st.markdown("---")
    with st.expander("Carregar Novo Mapa"):
        arquivo_mapa = st.file_uploader("Upload", type=["jpg", "jpeg", "png", "webp"])
        if arquivo_mapa:
            if st.button("📤 Enviar"):
                try:
                    b64 = comprimir_imagem(arquivo_mapa)
                    salvar_mapa_b64(b64)
                    st.success("Salvo!")
                    st.rerun()
                except Exception as e: st.error(str(e))

# ==============================================================================
# ABA 12: NPC & QUESTS (FINAL)
# ==============================================================================
with tab_npc:
    st.header("🎲 Mestre dos Jogos")
    
    c_criar, c_lista = st.columns([1, 1.5])
    
    # --- COLUNA DA ESQUERDA: CRIAÇÃO ---
    with c_criar:
        st.subheader("🛠️ Forja de Personagens")
        
        st.markdown("##### 1. Definição")
        col_a, col_b = st.columns(2)
        
        with col_a:
            caminho_sel = st.selectbox("Caminho", list(CAMINHOS_RPG.keys()))
            raca_sel = st.selectbox("Raça", RACAS)
            religiao_sel = st.selectbox("Religião", RELIGIOES)
        
        with col_b:
            classe_sel = st.selectbox("Classe", CAMINHOS_RPG[caminho_sel])
            cultura_sel = st.selectbox("Cultura", CULTURAS)
            idade_inp = st.text_input("Idade")
            align_inp = st.selectbox("Alinhamento", ["Leal Bom", "Neutro", "Caótico Mau", "Indefinido"])

        st.divider()
        st.markdown("##### 2. Geradores")
        
        col_gen1, col_gen2 = st.columns(2)
        with col_gen1:
            if st.button("🎲 Gerar Nome"):
                if api_key:
                    try:
                        p = f"Gere UM nome fantasia para um {raca_sel} {classe_sel} da cultura {cultura_sel}. Só o nome."
                        st.session_state.temp_npc_nome = genai.GenerativeModel(modelo_escolhido).generate_content(p).text.strip()
                        st.success("Nome criado!")
                    except: st.error("Erro IA")
                else: st.warning("Sem API Key")
        
        with col_gen2:
            desc_vis = st.text_input("Aparência:", placeholder="Ex: Cicatriz no olho")
            if st.button("📸 Retrato"):
                if api_key:
                    try:
                        # Gera prompt em inglês
                        p_art = f"Portrait of {raca_sel} {classe_sel}, {cultura_sel} style, {desc_vis}. Fantasy RPG character art, detailed face. Output ONLY english prompt."
                        p_ing = genai.GenerativeModel(modelo_escolhido).generate_content(p_art).text
                        # Gera imagem no Pollinations (200x200)
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(p_ing)}?width=200&height=200&nologo=true&model=flux"
                        st.session_state.temp_npc_img = url
                        st.success("Foto criada!")
                    except: st.error("Erro IA")
        
        # Mostra resultados temporários
        nome_final = st.text_input("Nome Final", value=st.session_state.temp_npc_nome)
        if st.session_state.temp_npc_img:
            st.image(st.session_state.temp_npc_img, width=200)

        st.divider()
        st.markdown("##### 3. História")
        if st.button("✨ Escrever Lore Automática"):
            if api_key:
                try:
                    p_lore = f"""
                    Crie um background curto (3 linhas) e um SEGREDO para este NPC.
                    Dados: {raca_sel} {classe_sel}, {cultura_sel}, Seguidor de {religiao_sel}.
                    """
                    st.session_state.temp_npc_lore = genai.GenerativeModel(modelo_escolhido).generate_content(p_lore).text
                except: st.error("Erro IA")
        
        lore_final = st.text_area("Lore/Segredo", value=st.session_state.temp_npc_lore)

        # Botão Final
        if st.button("💾 Salvar Ficha no Banco"):
            novo = {
                "nome": nome_final, "raca": raca_sel, "classe": classe_sel, 
                "cultura": cultura_sel, "religiao": religiao_sel,
                "idade": idade_inp, "align": align_inp, "segredo": lore_final,
                "img_url": st.session_state.temp_npc_img
            }
            salvar_npc(novo)
            st.session_state.npcs.append(novo)
            # Limpa
            st.session_state.temp_npc_nome = ""
            st.session_state.temp_npc_img = ""
            st.session_state.temp_npc_lore = ""
            st.success("NPC Cadastrado!")
            st.rerun()

    # --- COLUNA DA DIREITA: LISTA ---
    with c_lista:
        st.subheader(f"📜 Catálogo ({len(st.session_state.npcs)})")
        
        if not st.session_state.npcs:
            st.info("Nenhum NPC cadastrado.")
        else:
            for i, npc in enumerate(st.session_state.npcs):
                img_html = f'<img src="{npc.get("img_url")}" class="npc-avatar">' if npc.get("img_url") else '<div class="npc-avatar" style="background:#333;display:flex;align-items:center;justify-content:center;font-size:2em">👤</div>'
                
                st.markdown(f"""
                <div class="npc-card">
                    <div class="npc-img-container">{img_html}</div>
                    <div class="npc-content">
                        <div class="npc-header">
                            {npc['nome']}
                            <span class="npc-sub">{npc['raca']} | {npc.get('classe','')}</span>
                        </div>
                        <div class="npc-sub" style="margin-bottom:8px; color:#e6c200">
                            {npc.get('cultura','')} • {npc.get('religiao','')}
                        </div>
                        <div class="npc-body">
                            <span class="npc-label">Idade:</span> {npc.get('idade','?')} | 
                            <span class="npc-label">Align:</span> {npc.get('align','?')}
                            <div class="npc-lore">{npc['segredo']}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🗑️ Deletar {npc['nome']}", key=f"del_npc_{i}"):
                    deletar_npc_index(i)
                    st.session_state.npcs.pop(i)
                    st.rerun()
        
        st.divider()
        with st.expander("📜 Gerador de Quests (Baseado no Lore)"):
            if st.button("Gerar 3 Aventuras"):
                if api_key:
                    with st.spinner("Criando..."):
                        try:
                            l = {k:v for k,v in lore_data.items() if v.strip()}
                            p = f"Mestre RPG. Crie 3 Ganchos de Aventura baseados no lore: {json.dumps(l, ensure_ascii=False)}"
                            r = genai.GenerativeModel(modelo_escolhido).generate_content(p).text
                            st.markdown(r)
                        except: st.error("Erro IA")
                else: st.warning("API Key necessaria")
