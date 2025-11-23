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

# ==============================================================================
# 1. CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="World Architect Pro", 
    layout="wide", 
    page_icon="🏰",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# 2. ESTILO VISUAL (CSS - GRIMÓRIO DARK)
# ==============================================================================
def aplicar_estilo_visual():
    st.markdown("""
    <style>
        /* Fontes */
        @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700&family=Lato:wght@300;400;700&display=swap');
        
        /* Geral */
        .stApp {
            background-color: #0e1117;
            background-image: radial-gradient(circle at 50% 0, #1c2331, #0e1117);
            color: #d4d4d4;
            font-family: 'Lato', sans-serif;
        }
        
        /* Títulos */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Cinzel', serif;
            color: #e6c200 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-weight: 700;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #11141a;
            border-right: 1px solid #30363d;
        }
        
        /* Inputs */
        .stTextArea textarea, .stTextInput input, .stSelectbox div[data-baseweb="select"] {
            background-color: #161b22 !important;
            color: #e6e6e6 !important;
            border: 1px solid #30363d !important;
            border-radius: 8px;
        }
        .stTextArea textarea:focus, .stTextInput input:focus {
            border-color: #e6c200 !important;
            box-shadow: 0 0 8px rgba(230, 194, 0, 0.3);
        }
        
        /* Botões */
        .stButton > button {
            background: linear-gradient(180deg, #2e2e2e 0%, #1a1a1a 100%);
            color: #e6c200 !important;
            border: 1px solid #e6c200 !important;
            font-family: 'Cinzel', serif;
            font-weight: bold;
            border-radius: 6px;
            width: 100%;
            transition: all 0.3s ease;
        }
        .stButton > button:hover {
            background: linear-gradient(180deg, #e6c200 0%, #b39700 100%);
            color: #0e1117 !important;
            border-color: #fff !important;
            box-shadow: 0 0 15px rgba(230, 194, 0, 0.6);
        }
        
        /* Cards NPC */
        .npc-card {
            background-color: #1f2937;
            border: 1px solid #e6c200;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
            display: flex;
            gap: 15px;
            align-items: flex-start;
            transition: transform 0.2s;
        }
        .npc-card:hover { transform: translateY(-2px); }
        .npc-avatar {
            width: 100px; height: 100px; border-radius: 8px;
            object-fit: cover; border: 2px solid #e6c200;
        }
        .npc-content { flex-grow: 1; }
        .npc-header {
            font-family: 'Cinzel', serif; font-size: 1.3em; color: #e6c200;
            border-bottom: 1px solid #444; margin-bottom: 5px;
            display: flex; justify-content: space-between;
        }
        .npc-sub { font-size: 0.8em; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
        .npc-body { font-size: 0.95em; color: #ddd; line-height: 1.5; }
        .npc-label { color: #e6c200; font-weight: bold; margin-right: 5px; }
        .npc-lore { margin-top: 8px; font-style: italic; color: #bbb; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 5px; }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid #30363d; }
        .stTabs [data-baseweb="tab"] { background-color: transparent; color: #8b949e; font-family: 'Cinzel', serif; }
        .stTabs [aria-selected="true"] { background-color: #161b22; color: #e6c200; border: 1px solid #e6c200; border-bottom: none; }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()

# ==============================================================================
# 3. DADOS E REGRAS DE NEGÓCIO (LÓGICA RPG)
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

# --- LOGICA DE RAÇA VS CULTURA ---
# Culturas Cosmopolitas (Aceitam todas as raças)
CULTURAS_IMPERIAIS = ["Aiglana", "Povos do Leste"]

# Culturas Raciais (Travam a raça)
MAPA_CULTURA_RACA = {
    "Har'oloth": ["Drow"],
    "Björska": ["Humano", "Outro"], 
    "Alüriel": ["Elfo"],
    "Badûran": ["Anão"],
    "Gulthrak": ["Orc"],
    "Polkinea": ["Polski", "Pequilho"]
}

TODAS_RACAS = ["Humano", "Elfo", "Anão", "Orc", "Drow", "Polski", "Pequilho", "Outro"]

# --- LOGICA DE CLASSES ---
# Classes Base (Disponíveis para todos)
CLASSES_BASE = {
    "Sabio": ["Necromante", "Clérigo", "Druida", "Magus", "Granadeiro", "Lâmina Arcana"],
    "Guerreiro": ["Arqueiro", "Caçador", "Combatente", "Defensor", "Paladino", "Bárbaro", "Mutante"],
    "Ladino": ["Malandro Arcano", "Caçador de Tesouros", "Assassino", "Esgrimista", "Ladrao", "Espiao", "Vivisseccionista", "Bardo"]
}

# Classes Exclusivas (Adicionadas apenas à cultura correta)
CLASSES_EXCLUSIVAS = {
    "Gulthrak": {"Sabio": ["Shaman / Xamã"], "Guerreiro": ["Aklat'tur"]},
    "Har'oloth": {"Sabio": ["Dançarino das Sombras Caster"], "Ladino": ["Dançarino das Sombras", "Valsharess"]},
    "Badûran": {"Sabio": ["Engenheiro de Artilharia"], "Guerreiro": ["Engenheiro de Artilharia"]},
    "Alüriel": {"Sabio": ["Arqueiro Arcano"], "Guerreiro": ["Arqueiro Arcano"]},
    "Povos do Leste": {"Guerreiro": ["Monge", "Samurai"]},
    "Polkinea": {"Ladino": ["Trilha-Curta (Domestic Worker)"]},
    "Björska": {"Guerreiro": ["Boat Makers (Wood Worker)"]}
}
# Nota: Aigla (Império Aiglano) tem acesso a tudo que não seja exclusivo dos outros.

RELIGIOES = ["Veneratio", "Eluith'orth", "Kai", "Halleuad", "Lórё", "Bokk Bharaz", "Ushkr'ar", "Céticos"]

# ==============================================================================
# 4. INICIALIZAÇÃO DE ESTADO
# ==============================================================================
if "sugestoes_ia" not in st.session_state: st.session_state.sugestoes_ia = {}
if "erros_ia" not in st.session_state: st.session_state.erros_ia = {}
if "resumo_erros" not in st.session_state: st.session_state.resumo_erros = ""
if "auditoria_dados" not in st.session_state: st.session_state.auditoria_dados = []
if "messages" not in st.session_state: st.session_state.messages = []
if "glossario" not in st.session_state: st.session_state.glossario = {}
if "timeline_dados" not in st.session_state: st.session_state.timeline_dados = []
if "dashboard_dados" not in st.session_state: st.session_state.dashboard_dados = []
if "mapa_pins" not in st.session_state: st.session_state.mapa_pins = []
if "npcs" not in st.session_state: st.session_state.npcs = []
    
# Variáveis temporárias NPC
if "temp_npc_nome" not in st.session_state: st.session_state.temp_npc_nome = ""
if "temp_npc_img" not in st.session_state: st.session_state.temp_npc_img = ""
if "temp_npc_lore" not in st.session_state: st.session_state.temp_npc_lore = ""

# ==============================================================================
# 5. CONEXÃO FIREBASE
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
# 6. FUNÇÕES AUXILIARES
# ==============================================================================
def enviar_alerta_email(categoria_alterada):
    if "email" not in st.secrets: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = st.secrets["email"]["destinatario"]
        msg['Subject'] = f"🔔 Alteração: {categoria_alterada}"
        fuso = pytz.timezone('America/Sao_Paulo')
        msg.attach(MIMEText(f"Alterado às {datetime.now(fuso).strftime('%H:%M')}.", 'plain'))
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.send_message(msg)
        server.quit()
        return True
    except: return False

def carregar_lore():
    doc = db.collection("mundos").document("lore_oficial").get()
    if doc.exists: return doc.to_dict()
    return {cat: "" for cat in CATEGORIAS}

def salvar_categoria(categoria, texto):
    db.collection("mundos").document("lore_oficial").set({categoria: texto}, merge=True)
    enviar_alerta_email(categoria)

# --- NPC ---
def carregar_npcs():
    doc = db.collection("mundos").document("npc_database").get()
    if doc.exists: return doc.to_dict().get("lista", [])
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

# --- MAPAS E CACHE ---
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

def carregar_cache_analises():
    doc = db.collection("mundos").document("cache_analises").get()
    if doc.exists:
        return doc.to_dict()
    return {}

def salvar_cache_analise(tipo, dados):
    doc_ref = db.collection("mundos").document("cache_analises")
    doc_ref.set({tipo: dados}, merge=True)

# --- UTILS ---
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

def comprimir_imagem(arquivo_upload):
    image = Image.open(arquivo_upload)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    max_width = 1600
    if image.width > max_width:
        ratio = max_width / float(image.width)
        new_height = int((float(image.height) * float(ratio)))
        image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

# ==============================================================================
# 7. LOAD INICIAL DE DADOS
# ==============================================================================
caches_salvos = carregar_cache_analises()

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
if not st.session_state.timeline_dados: 
    st.session_state.timeline_dados = caches_salvos.get("timeline_dados", [])
if not st.session_state.dashboard_dados: 
    st.session_state.dashboard_dados = caches_salvos.get("dashboard_dados", [])
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
# 8. BARRA LATERAL
# ==============================================================================
with st.sidebar:
    st.title("🏰 World Architect")
    st.header("⚙️ Configuração")
    api_key = st.text_input("API Key (Gemini)", type="password")
    
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
    st.subheader("🔍 Busca Global")
    termo_busca = st.text_input("Procurar no Lore:", placeholder="Ex: Elfos")
    if termo_busca:
        resultados = []
        for cat, texto in lore_data.items():
            if termo_busca.lower() in texto.lower():
                resultados.append(cat)
        if resultados:
            st.success(f"Encontrado em {len(resultados)} seções:")
            for r in resultados: st.caption(f"• {r}")
        else: st.warning("Não encontrado.")

# ==============================================================================
# 9. ABAS
# ==============================================================================
abas = [
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", 
    "📚 Glossário", "📉 Timeline", "📊 Dashboards", "🗺️ Mapa", "🎲 NPCs", "📜 Quests"
]

tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_timeline, tab_dashboard, tab_mapa, tab_npc, tab_quests = st.tabs(abas)

# === ABA 1: EDITOR ===
with tab_editor:
    c1, c2 = st.columns([3,1])
    with c1: st.info("Salvamento na nuvem + Notificação por E-mail.")
    with c2: filtro = st.selectbox("Filtro Visual:", ["Ver Tudo", "Geral", "Timeline", "Povos"])
    
    for cat in CATEGORIAS:
        visivel = True
        if filtro == "Geral" and ("Timeline" in cat or "Povo" in cat): visivel = False
        elif filtro == "Timeline" and "Timeline" not in cat: visivel = False
        elif filtro == "Povos" and "Povo" not in cat: visivel = False
        
        if visivel:
            st.markdown(f"### {cat}")
            val = lore_data.get(cat, "")
            novo = st.text_area(cat, val, height=500, label_visibility="collapsed", key=f"t_{cat}")
            if st.button(f"💾 Salvar {cat}", key=f"b_{cat}"):
                salvar_categoria(cat, novo)
                st.toast("Salvo! E-mail enviado.", icon="📧")
            st.divider()

# === ABA 2: CHAT ===
with tab_chat:
    c1, c2 = st.columns([4,1])
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
                except Exception as e: st.error(f"Erro na IA: {e}")

# === ABA 3: AUDITORIA ===
with tab_aval:
    st.header("⚖️ Auditoria")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.auditoria_dados: st.success("Cache carregado.")
        if st.button("🔄 Recalcular"):
            with st.spinner("..."):
                try:
                    res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Crítico Cínico. Analise: {json.dumps({k:v for k,v in lore_data.items() if v.strip()}, ensure_ascii=False)}. JSON: [{{ "titulo": "...", "nota": 8, "analise": "...", "melhorias": "..." }}]""").text
                    d = extrair_json(res)
                    if d: st.session_state.auditoria_dados = d; salvar_cache_analise("auditoria", d); st.rerun()
                except Exception as e: st.error(str(e))
        for i in st.session_state.auditoria_dados:
            with st.expander(f"{i['titulo']} - Nota {i['nota']}"): st.progress(i['nota']/10); st.info(i['analise']); st.warning(i['melhorias'])

# === ABA 4: SUGESTÕES ===
with tab_sugestao:
    st.header("💡 Ideias")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.sugestoes_ia: st.success("Cache carregado.")
        if st.button("🔄 Gerar"):
            with st.spinner("..."):
                try:
                    res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Co-Autor. Bullet Points 3-5. JSON: {{ "Categoria": "• ...", ... }}. LORE: {json.dumps({k:v for k,v in lore_data.items()}, ensure_ascii=False)}""").text
                    d = extrair_json(res)
                    if d: st.session_state.sugestoes_ia = d; salvar_cache_analise("sugestoes", d); st.rerun()
                except Exception as e: st.error(str(e))
    if st.session_state.sugestoes_ia:
        for c in CATEGORIAS: st.text_area(f"💡 {c}", st.session_state.sugestoes_ia.get(c, ""), height=200, disabled=True)

# === ABA 5: INCOERÊNCIAS ===
with tab_erros:
    st.header("⚡ Inquisidor")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.erros_ia: st.success("Cache carregado.")
        if st.button("🔄 Rastrear"):
            with st.spinner("..."):
                try:
                    res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Auditor Lógico. Ache erros. Bullet Points. JSON: {{ "resumo_geral": "...", "detalhes": {{ "Categoria": "• 🔴 ...", ... }} }}. LORE: {json.dumps({k:v for k,v in lore_data.items() if v.strip()}, ensure_ascii=False)}""").text
                    d = extrair_json(res)
                    if d: st.session_state.resumo_erros = d.get("resumo_geral",""); st.session_state.erros_ia = d.get("detalhes",{}); salvar_cache_analise("erros", st.session_state.erros_ia); salvar_cache_analise("resumo_erros", st.session_state.resumo_erros); st.rerun()
                except Exception as e: st.error(str(e))
    if st.session_state.resumo_erros: st.info(st.session_state.resumo_erros)
    for c, err in st.session_state.erros_ia.items(): st.error(f"🚨 {c}:\n{err}")

# === ABA 6: GLOSSÁRIO ===
with tab_glossario:
    st.header("📚 Glossário")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.button("🔄 Atualizar"):
            with st.spinner("..."):
                try:
                    res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Bibliotecário. Termos e definições. JSON: {{ "Termo": "Def...", ... }}. LORE: {json.dumps({k:v for k,v in lore_data.items() if v.strip()}, ensure_ascii=False)}""").text
                    d = extrair_json(res)
                    if d: st.session_state.glossario = d; salvar_cache_analise("glossario", d); st.rerun()
                except Exception as e: st.error(str(e))
    c1, c2 = st.columns([2, 1])
    with c1:
        txt_escolhido = st.selectbox("Ler:", CATEGORIAS)
        conteudo = lore_data.get(txt_escolhido, "")
        st.text_area("Leitura:", value=conteudo, height=600, disabled=True)
    with c2:
        st.subheader("🔍 Termos")
        if st.session_state.glossario and conteudo:
            encontrados = [(t, d) for t, d in st.session_state.glossario.items() if t in conteudo]
            if encontrados:
                for t, d in encontrados:
                    with st.expander(f"🔹 {t}"): st.write(d)
            else: st.info("Nenhum termo encontrado.")

# === ABA 7: TIMELINE ===
with tab_timeline:
    st.header("📉 Timeline")
    if not api_key: st.warning("API Key necessária.")
    else:
        if st.session_state.timeline_dados: st.success("Cache carregado.")
        if st.button("🔄 Gerar"):
            with st.spinner("..."):
                try:
                    res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Analise Timelines. JSON: [{{ "ano_numerico": 100, "data_exibicao": "Ano 100", "evento": "...", "grupo": "..." }}]. LORE: {json.dumps({k:v for k,v in lore_data.items() if "Timeline" in k}, ensure_ascii=False)}""").text
                    d = extrair_json(res)
                    if d: st.session_state.timeline_dados = d; salvar_cache_analise("timeline_dados", d); st.rerun()
                except Exception as e: st.error(str(e))
    if st.session_state.timeline_dados:
        try:
            df = pd.DataFrame(st.session_state.timeline_dados)
            if not df.empty:
                fig = px.scatter(df, x="ano_numerico", y="grupo", hover_name="data_exibicao", hover_data={"ano_numerico": False, "grupo": False, "evento": True}, color="grupo", height=600)
                fig.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22")
                st.plotly_chart(fig, use_container_width=True)
        except: pass

# === ABA 8: DASHBOARDS ===
with tab_dashboard:
    st.header("📊 Sala de Guerra")
    if not api_key: st.warning("API Key necessária.")
    else:
        if st.session_state.dashboard_dados: st.success("Cache carregado.")
        if st.button("🔄 Calcular"):
            try:
                res = genai.GenerativeModel(modelo_escolhido).generate_content(f"""Estrategista. JSON: [{{ "Entidade": "...", "Militar": 90, ... }}]. LORE: {json.dumps({k:v for k,v in lore_data.items() if v.strip()}, ensure_ascii=False)}""").text
                d = extrair_json(res)
                if d: st.session_state.dashboard_dados = d; salvar_cache_analise("dashboard_dados", d); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
    if st.session_state.dashboard_dados:
        df = pd.DataFrame(st.session_state.dashboard_dados)
        fig = px.bar(df, x="Entidade", y=["Militar", "Magia", "Economia", "Influencia"], barmode="group")
        fig.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22")
        st.plotly_chart(fig, use_container_width=True)

# === ABA 9: MAPA ===
with tab_mapa:
    st.header("🗺️ Cartografia")
    modo = st.radio("Modo:", ["👁️ Explorar", "📍 Editar"], horizontal=True)
    mapa_b64 = carregar_mapa()
    if mapa_b64:
        img_bytes = base64.b64decode(mapa_b64)
        img_pil = Image.open(io.BytesIO(img_bytes))
        if modo == "👁️ Explorar":
            if st.session_state.mapa_pins:
                df_pins = pd.DataFrame(st.session_state.mapa_pins)
                fig = px.scatter(df_pins, x="x", y="y", hover_name="nome", hover_data={"x":False, "y":False, "desc":True}, title="Mapa Interativo")
                fig.add_layout_image(dict(source=img_pil, xref="x", yref="y", x=0, y=0, sizex=img_pil.width, sizey=img_pil.height, sizing="stretch", opacity=1, layer="below"))
                fig.update_xaxes(visible=False, range=[0, img_pil.width]); fig.update_yaxes(visible=False, range=[img_pil.height, 0])
                fig.update_layout(width=img_pil.width, height=img_pil.height, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor="#0e1117", plot_bgcolor="#0e1117")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.image(img_pil, caption="Sem pins.", use_container_width=True)
        else:
            st.info("Clique na imagem.")
            coords = streamlit_image_coordinates(img_pil, key="click")
            if coords:
                with st.form("pin"):
                    nome = st.text_input("Nome")
                    desc = st.text_area("Desc")
                    if st.form_submit_button("Salvar"):
                        pins = st.session_state.mapa_pins
                        pins.append({"x": coords['x'], "y": coords['y'], "nome": nome, "desc": desc})
                        salvar_pins(pins); st.session_state.mapa_pins = pins; st.rerun()
    else: st.info("Sem mapa.")
    st.markdown("---")
    upl = st.file_uploader("Novo Mapa", type=["jpg", "jpeg", "png", "webp"])
    if upl and st.button("📤 Enviar"):
        try:
            b64 = comprimir_imagem(upl)
            salvar_mapa_b64(b64)
            st.success("Salvo!"); st.rerun()
        except Exception as e: st.error(str(e))

# === ABA 10: NPCs (ATUALIZADO COM REGRAS RÍGIDAS) ===
with tab_npc:
    st.header("🎲 Banco de NPCs")
    c_criar, c_lista = st.columns([1, 1.5])
    
    with c_criar:
        st.subheader("🛠️ Criar NPC")
        
        # 1. CULTURA (Define a Raça)
        cultura = st.selectbox("Cultura de Origem:", list(CULTURAS) + CULTURAS_IMPERIAIS)
        
        # 2. RAÇA (Filtro por Cultura)
        racas_disp = []
        if cultura in CULTURAS_IMPERIAIS: racas_disp = TODAS_RACAS
        elif cultura in MAPA_CULTURA_RACA: racas_disp = MAPA_CULTURA_RACA[cultura]
        else: racas_disp = TODAS_RACAS
        raca = st.selectbox("Raça:", racas_disp)
        
        # 3. CLASSES (Filtro por Cultura e Caminho)
        caminho = st.selectbox("Caminho:", list(CAMINHOS_RPG.keys()))
        classes_disp = CAMINHOS_RPG[caminho].copy() # Começa com o básico
        
        if cultura in CLASSES_EXCLUSIVAS:
            extras = CLASSES_EXCLUSIVAS[cultura].get(caminho, [])
            classes_disp.extend(extras)
            
        classe = st.selectbox("Classe:", classes_disp)
        
        # 4. GÊNERO E OUTROS
        col_g1, col_g2 = st.columns(2)
        with col_g1: genero = st.selectbox("Gênero:", ["Masculino", "Feminino", "Outro"])
        with col_g2: religiao = st.selectbox("Religião:", RELIGIOES)
        
        idade = st.text_input("Idade")
        align = st.selectbox("Alinhamento", ["Leal Bom", "Neutro", "Caótico Mau", "Indefinido"])

        st.markdown("---")
        
        # GERADORES
        c_gen1, c_gen2 = st.columns(2)
        with c_gen1:
            if st.button("🎲 Nome"):
                if api_key:
                    try:
                        # Prompt ajustado: APENAS UM NOME
                        p = f"Gere APENAS UM nome fantasia ({genero}) para {raca} de {cultura}. Responda SOMENTE o nome."
                        st.session_state.temp_npc_nome = genai.GenerativeModel(modelo_escolhido).generate_content(p).text.strip()
                        st.rerun()
                    except Exception as e: st.error(f"Erro IA: {e}")
        
        with c_gen2:
            desc = st.text_input("Visual:", placeholder="Cicatriz, olhos...")
            if st.button("📸 Foto"):
                if api_key:
                    try:
                        p_art = f"Portrait of {genero} {raca} {classe}, {cultura}, {desc}. Fantasy RPG art. Output ONLY english prompt."
                        ing = genai.GenerativeModel(modelo_escolhido).generate_content(p_art).text
                        url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(ing)}?width=200&height=200&nologo=true&model=flux"
                        st.session_state.temp_npc_img = url
                        st.rerun()
                    except Exception as e: st.error(f"Erro IA: {e}")

        nome = st.text_input("Nome Final", value=st.session_state.temp_npc_nome)
        if st.session_state.temp_npc_img:
            st.markdown(f'<a href="{st.session_state.temp_npc_img}" target="_blank"><img src="{st.session_state.temp_npc_img}" style="border:2px solid #e6c200;border-radius:8px"></a>', unsafe_allow_html=True)

        if st.button("✨ Gerar Lore"):
            if api_key:
                try:
                    p_lore = f"Lore curta e segredo para {nome}, {genero} {raca} {classe} de {cultura}, {religiao}."
                    st.session_state.temp_npc_lore = genai.GenerativeModel(modelo_escolhido).generate_content(p_lore).text
                    st.rerun()
                except Exception as e: st.error(f"Erro IA: {e}")
        
        lore_final = st.text_area("Lore", value=st.session_state.temp_npc_lore)
        
        if st.button("💾 Salvar NPC"):
            novo = {"nome": nome, "raca": raca, "classe": classe, "cultura": cultura, "religiao": religiao, "genero": genero, "idade": idade, "align": align, "segredo": lore_final, "img_url": st.session_state.temp_npc_img}
            salvar_npc(novo); st.session_state.npcs.append(novo); st.success("Salvo!"); st.rerun()

    with c_lista:
        st.subheader(f"📜 Catálogo ({len(st.session_state.npcs)})")
        for i, n in enumerate(st.session_state.npcs):
            img = f'<a href="{n.get("img_url")}" target="_blank"><img src="{n.get("img_url")}" class="npc-avatar"></a>' if n.get("img_url") else '<div class="npc-avatar" style="background:#333;display:flex;align-items:center;justify-content:center;font-size:2em">👤</div>'
            st.markdown(f"""<div class="npc-card"><div class="npc-img-container">{img}</div><div class="npc-content"><div class="npc-header">{n['nome']} <span class="npc-sub">{n['raca']} | {n.get('classe','')}</span></div><div class="npc-sub" style="color:#e6c200">{n.get('cultura','')} • {n.get('religiao','')}</div><div class="npc-body">Idade: {n.get('idade','?')} | Align: {n.get('align','?')}</div><div class="npc-lore">{n['segredo']}</div></div></div>""", unsafe_allow_html=True)
            if st.button(f"🗑️ {n['nome']}", key=f"del_{i}"): deletar_npc_index(i); st.session_state.npcs.pop(i); st.rerun()

# === ABA 11: QUESTS ===
with tab_quests:
    st.header("📜 Mural de Missões")
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("🎲 Gerar 5 Aventuras", type="primary"):
            if api_key:
                with st.spinner("Ouvindo boatos..."):
                    try:
                        l = {k:v for k,v in lore_data.items() if v.strip()}
                        p = f"Mestre RPG. Crie 5 Ganchos de Aventura baseados no lore: {json.dumps(l, ensure_ascii=False)}"
                        st.session_state.quest_result = genai.GenerativeModel(modelo_escolhido).generate_content(p).text
                    except: st.error("Erro IA")
            else: st.warning("API Key necessária")
    with c2:
        if "quest_result" in st.session_state: st.markdown(st.session_state.quest_result)
