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
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# ==============================================================================
st.set_page_config(page_title="World Architect Pro", layout="wide", page_icon="🏰")

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
        
        /* --- TIPOGRAFIA DOURADA --- */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Cinzel', serif;
            color: #e6c200 !important;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
            font-weight: 700;
        }
        
        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: #11141a;
            border-right: 1px solid #30363d;
        }
        
        /* --- INPUTS E TEXTAREAS --- */
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
        
        /* --- BOTÕES ESTILIZADOS --- */
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
        
        /* --- CARDS DE NPC --- */
        .npc-card {
            background: #1f2937;
            border: 1px solid #e6c200;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
        .npc-header {
            font-family: 'Cinzel', serif;
            font-size: 1.4em;
            color: #e6c200;
            border-bottom: 1px solid #444;
            padding-bottom: 8px;
            margin-bottom: 12px;
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
        }
        .npc-body {
            font-size: 1em;
            color: #ddd;
            line-height: 1.6;
        }
        .npc-label {
            color: #e6c200;
            font-weight: bold;
            font-size: 0.9em;
            margin-right: 5px;
        }
        
        /* --- TOAST --- */
        div[data-testid="stToast"] {
            background-color: #161b22;
            border: 1px solid #e6c200;
            color: #e6c200;
            font-family: 'Cinzel', serif;
        }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_visual()

# ==============================================================================
# 2. INICIALIZAÇÃO DE ESTADO (CACHE LOCAL)
# ==============================================================================
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
if "mapa_pins" not in st.session_state: st.session_state.mapa_pins = []
if "npcs" not in st.session_state: st.session_state.npcs = []

# ==============================================================================
# 3. CONEXÃO COM O FIREBASE
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
# 4. LISTA DE CATEGORIAS (LORE)
# ==============================================================================
CATEGORIAS = [
    # Novas
    "Absencia - Caos", "Radiancia - Ordem", "Warp", "Os 4 Cavaleiros",
    # Gerais
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    # Timeline
    "Timeline - Cataclisma", "Timeline - Badlands", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    # Povos
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

# ==============================================================================
# 5. FUNÇÕES AUXILIARES (BANCO, IA, IMAGEM, EMAIL)
# ==============================================================================

def enviar_alerta_email(categoria_alterada):
    """Envia e-mail silencioso via Gmail."""
    if "email" not in st.secrets: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = st.secrets["email"]["usuario"]
        msg['To'] = st.secrets["email"]["destinatario"]
        msg['Subject'] = f"🔔 World Architect: Alteração em {categoria_alterada}"
        
        fuso = pytz.timezone('America/Sao_Paulo')
        hora = datetime.now(fuso).strftime("%H:%M")
        texto = f"A seção '{categoria_alterada}' foi modificada e salva no banco às {hora}."
        msg.attach(MIMEText(texto, 'plain'))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(st.secrets["email"]["usuario"], st.secrets["email"]["senha"])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Erro email: {e}")
        return False

def carregar_lore():
    doc = db.collection("mundos").document("lore_oficial").get()
    if doc.exists: return doc.to_dict()
    return {cat: "" for cat in CATEGORIAS}

def salvar_categoria(categoria, texto):
    db.collection("mundos").document("lore_oficial").set({categoria: texto}, merge=True)
    enviar_alerta_email(categoria)

# --- FUNÇÕES DE NPC ---
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

# --- FUNÇÕES DE MAPA E CACHE ---
def salvar_mapa_b64(b64): db.collection("mundos").document("mapa_oficial").set({"imagem_b64": b64})
def carregar_mapa():
    d = db.collection("mundos").document("mapa_oficial").get()
    return d.to_dict().get("imagem_b64") if d.exists else None

def carregar_pins():
    d = db.collection("mundos").document("mapa_pins").get()
    return d.to_dict().get("lista", []) if d.exists else []
def salvar_pins(l): db.collection("mundos").document("mapa_pins").set({"lista": l})

def carregar_cache_analises():
    doc = db.collection("mundos").document("cache_analises").get()
    if doc.exists: return doc.to_dict()
    return {}

def salvar_cache_analise(tipo, dados):
    db.collection("mundos").document("cache_analises").set({tipo: dados}, merge=True)

def extrair_json(texto):
    try:
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except: return None

def extrair_dot(texto):
    try:
        match = re.search(r"```(?:dot|graphviz)\n(.*?)\n```", texto, re.DOTALL)
        if match: return match.group(1)
        if "digraph" in texto:
            start = texto.find("digraph")
            end = texto.rfind("}") + 1
            return texto[start:end]
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
# 6. RECUPERAÇÃO DE DADOS (LOAD)
# ==============================================================================
cache = carregar_cache_analises()

# Carrega cache nas variáveis de sessão se estiverem vazias
if not st.session_state.sugestoes_ia: st.session_state.sugestoes_ia = cache.get("sugestoes", {})
if not st.session_state.erros_ia: st.session_state.erros_ia = cache.get("erros", {})
if not st.session_state.resumo_erros: st.session_state.resumo_erros = cache.get("resumo_erros", "")
if not st.session_state.auditoria_dados: st.session_state.auditoria_dados = cache.get("auditoria", [])
if not st.session_state.messages: st.session_state.messages = cache.get("chat_history", [])
if not st.session_state.glossario: st.session_state.glossario = cache.get("glossario", {})
if not st.session_state.arvore_dot: st.session_state.arvore_dot = cache.get("arvore_dot", "")
if not st.session_state.timeline_dados: st.session_state.timeline_dados = cache.get("timeline_dados", [])
if not st.session_state.dashboard_dados: st.session_state.dashboard_dados = cache.get("dashboard_dados", [])
if not st.session_state.grafo_dot: st.session_state.grafo_dot = cache.get("grafo_dot", "")
if not st.session_state.mapa_pins: st.session_state.mapa_pins = carregar_pins()
if not st.session_state.npcs: st.session_state.npcs = carregar_npcs()

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro fatal ao carregar Lore: {e}")
    st.stop()

# ==============================================================================
# 7. BARRA LATERAL (SIDEBAR)
# ==============================================================================
with st.sidebar:
    st.title("🏰 World Architect")
    
    st.header("⚙️ Configuração")
    api_key = st.text_input("API Key (Gemini)", type="password")
    modelo_escolhido = "gemini-pro"
    
    if api_key:
        genai.configure(api_key=api_key)
        try:
            lista = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods and "exp" not in m.name]
            lista.sort(key=lambda x: "flash" not in x)
            modelo_escolhido = st.selectbox("Cérebro da IA:", lista, index=0)
        except: pass
        
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
# 8. ABAS PRINCIPAIS DO SISTEMA
# ==============================================================================
abas = [
    "✍️ Editor", "🎲 NPC & Quests", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", 
    "⚡ Incoerências", "📚 Glossário", "🌳 Genealogia", "🕸️ Conexões", 
    "📉 Timeline", "📊 Dashboards", "🗺️ Mapa"
]
tab_editor, tab_npc, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_genealogia, tab_conexoes, tab_timeline, tab_dashboard, tab_mapa = st.tabs(abas)

# --- ABA 1: EDITOR (COM E-MAIL) ---
with tab_editor:
    col_titulo, col_filtro = st.columns([3, 1])
    with col_titulo:
        st.info("💾 As escrituras são salvas na nuvem com backup automático.")
    with col_filtro:
        filtro_visualizacao = st.selectbox("Índice (Filtrar):", ["Ver Tudo", "Geral/Cosmologia", "Timeline", "Povos"])

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
                        st.toast(f"Alterações em '{cat}' salvas! Email enviado.", icon="📧")
                idx += 1
        st.divider()

    criar_secao_editor("📜 Documentos Gerais & Cosmologia", "Geral")
    criar_secao_editor("⏳ Timeline", "Timeline")
    criar_secao_editor("🏰 Povos", "Povo")

# --- ABA 2: NPC & QUESTS (FERRAMENTAS DO MESTRE) ---
with tab_npc:
    st.header("🎲 Mestre dos Jogos")
    subtabs = st.tabs(["👤 Banco de NPCs", "🖼️ Ateliê de Arte", "🏷️ Gerador de Nomes", "📜 Mural de Missões"])
    
    # 1. BANCO DE NPCs
    with subtabs[0]:
        c_add, c_view = st.columns([1, 2])
        with c_add:
            st.subheader("Criar Novo NPC")
            with st.form("form_npc"):
                nome = st.text_input("Nome")
                raca = st.selectbox("Raça/Povo", ["Humano", "Elfo", "Anão", "Orc", "Drow", "Pequilho", "Outro"])
                classe = st.text_input("Classe/Ocupação")
                idade = st.text_input("Idade")
                align = st.selectbox("Alinhamento", ["Leal Bom", "Neutro", "Caótico Mau", "Indefinido"])
                segredo = st.text_area("Segredo/Lore")
                
                if st.form_submit_button("💾 Salvar Ficha"):
                    novo = {"nome": nome, "raca": raca, "classe": classe, "idade": idade, "align": align, "segredo": segredo}
                    salvar_npc(novo)
                    st.session_state.npcs.append(novo)
                    st.success("NPC Salvo no Banco!")
                    st.rerun()
        
        with c_view:
            st.subheader(f"Catálogo de Personagens ({len(st.session_state.npcs)})")
            if not st.session_state.npcs:
                st.info("Nenhum NPC cadastrado ainda.")
            else:
                for i, npc in enumerate(st.session_state.npcs):
                    # Card Visual HTML
                    st.markdown(f"""
                    <div class="npc-card">
                        <div class="npc-header">
                            {npc['nome']} 
                            <span class="npc-sub">({npc['raca']})</span>
                        </div>
                        <div class="npc-body">
                            <span class="npc-label">Ocupação:</span> {npc['classe']} &nbsp;|&nbsp; 
                            <span class="npc-label">Idade:</span> {npc['idade']} &nbsp;|&nbsp; 
                            <span class="npc-label">Alinhamento:</span> {npc['align']}<br>
                            <hr style="border-color: #444; margin: 8px 0;">
                            <i>"{npc['segredo']}"</i>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"🗑️ Deletar {npc['nome']}", key=f"del_npc_{i}"):
                        deletar_npc_index(i)
                        st.session_state.npcs.pop(i)
                        st.rerun()

    # 2. GERADOR DE IMAGENS (POLLINATIONS)
    with subtabs[1]:
        st.subheader("🖼️ Ateliê de Arte (IA)")
        st.info("Descreva o personagem ou local. A IA cria um prompt profissional e gera a imagem na hora (Grátis).")
        
        if not api_key: st.warning("API Key necessária para criar o prompt.")
        else:
            desc_img = st.text_input("O que você quer ver?", placeholder="Ex: Um guerreiro orc com armadura dourada no deserto ao pôr do sol")
            if st.button("🎨 Pintar"):
                with st.spinner("A IA está imaginando e pintando..."):
                    try:
                        # 1. Gemini melhora o prompt
                        prompt_art = f"""
                        Act as a Prompt Engineer for Stable Diffusion.
                        Transform this description: "{desc_img}" into a highly detailed, epic fantasy art prompt in English.
                        Include details about lighting, style (e.g. Greg Rutkowski, oil painting), and mood.
                        Output ONLY the prompt text.
                        """
                        model = genai.GenerativeModel(modelo_escolhido)
                        prompt_ingles = model.generate_content(prompt_art).text
                        
                        st.caption(f"Prompt Gerado: {prompt_ingles}")
                        
                        # 2. Pollinations gera a imagem
                        encoded_prompt = urllib.parse.quote(prompt_ingles)
                        url_imagem = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&model=flux"
                        
                        st.image(url_imagem, caption=desc_img, use_container_width=True)
                        st.markdown(f"[⬇️ Baixar Imagem em Alta Resolução]({url_imagem})")
                    except Exception as e: st.error(f"Erro ao gerar imagem: {e}")

    # 3. GERADOR DE NOMES
    with subtabs[2]:
        st.subheader("🏷️ Gerador de Nomes Culturais")
        if not api_key: st.warning("API Key necessária.")
        else:
            povo_sel = st.selectbox("Escolha a Cultura de Origem:", CATEGORIAS)
            if st.button("Gerar Lista de Nomes"):
                with st.spinner("Consultando linguistas..."):
                    try:
                        lore_povo = lore_data.get(povo_sel, "")
                        prompt_nome = f"""
                        Atue como Linguista de Fantasia.
                        Baseado no texto abaixo sobre '{povo_sel}', crie 10 nomes (masculinos, femininos e neutros) que sigam a fonética e regras dessa cultura.
                        Explique brevemente o significado de cada um.
                        
                        LORE: {lore_povo[:4000]}...
                        """
                        res = genai.GenerativeModel(modelo_escolhido).generate_content(prompt_nome).text
                        st.markdown(res)
                    except Exception as e: st.error(str(e))

    # 4. GERADOR DE QUESTS
    with subtabs[3]:
        st.subheader("📜 Mural de Missões")
        st.markdown("Gera ganchos de aventura baseados nas tensões políticas atuais.")
        if not api_key: st.warning("API Key necessária.")
        else:
            if st.button("Gerar 5 Aventuras"):
                with st.spinner("Ouvindo fofocas nas tavernas..."):
                    try:
                        lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                        prompt_quest = f"""
                        Atue como Mestre de RPG Profissional.
                        Crie 5 Ganchos de Aventura (Quests) baseados nas tensões descritas no lore abaixo.
                        Para cada quest, defina:
                        - Título Épico
                        - Sinopse do Conflito
                        - Quem Contrata
                        - Recompensa
                        - Twist/Reviravolta
                        
                        LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
                        """
                        res = genai.GenerativeModel(modelo_escolhido).generate_content(prompt_quest).text
                        st.markdown(res)
                    except Exception as e: st.error(str(e))

# --- ABA 3: CHAT (CACHEADO) ---
with tab_chat:
    c1, c2 = st.columns([4, 1])
    c1.header("🔮 Oráculo da Lore")
    if c2.button("🗑️ Limpar Chat"):
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
            sys_prompt = f"""
            Você é o Guardião deste mundo.
            LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
            USUÁRIO: {prompt}
            """
            with st.chat_message("assistant"):
                try:
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(sys_prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                    salvar_cache_analise("chat_history", st.session_state.messages)
                except Exception as e: st.error(str(e))

# --- ABA 4: AUDITORIA (CRÍTICA) ---
with tab_aval:
    st.header("⚖️ O Julgamento Final")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.auditoria_dados: st.success("📂 Relatório recuperado dos arquivos.")
        if st.button("🔄 Convocar Novo Julgamento (Brutal)"):
            with st.spinner("O Crítico está destruindo seus conceitos..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_auditoria = f"""
                    VOCÊ É UM EDITOR LITERÁRIO SÊNIOR, CÍNICO E EXTREMAMENTE CRÍTICO (ESTILO GEORGE MARTIN EM UM DIA RUIM).
                    SUA MISSÃO: Analisar o worldbuilding abaixo e DESTRUIR qualquer incoerência, clichê ou preguiça criativa.
                    
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
                    else: st.write(res.text)
                except Exception as e: st.error(str(e))
        
        if st.session_state.auditoria_dados:
             for item in st.session_state.auditoria_dados:
                with st.expander(f"{item['titulo']} - Nota {item['nota']}"):
                    st.progress(item['nota']/10)
                    st.info(f"**Análise:** {item['analise']}")
                    st.warning(f"**Exigência:** {item['melhorias']}")

# --- ABA 5: SUGESTÕES (BULLET POINTS) ---
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
                    Atue como Co-Autor. Para CADA categoria abaixo, escreva 3 a 5 TÓPICOS (Bullet Points) de ideias novas.
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    JSON DE SAÍDA: {{ "Categoria": "• Ideia 1\\n• Ideia 2", ... }}
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

# --- ABA 6: INCOERÊNCIAS ---
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
                    VOCÊ É UM INVESTIGADOR FORENSE DE LÓGICA. Não seja "bonzinho".
                    TAREFA: Cruze TODOS os dados. Se A contradiz B, aponte. Use Bullet Points.
                    
                    FORMATO JSON: {{ "resumo_geral": "Veredito ácido...", "detalhes": {{ "Categoria": "• 🔴 ERRO: ...", ... }} }}
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

# --- ABA 7: GLOSSÁRIO ---
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

# --- ABA 8: GENEALOGIA ---
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
                    Atue como Genealogista. Crie um código GRAPHVIZ DOT.
                    REGRAS: digraph G {{ rankdir=LR; bgcolor="#0e1117"; node [fontcolor="white" color="white"]; edge [color="gray"]; ... }}
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

# --- ABA 9: CONEXÕES (DARK MODE) ---
with tab_conexoes:
    st.header("🕸️ Teia de Influência")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.grafo_dot: st.success("📂 Rede carregada.")
        if st.button("🔄 Mapear Teia Política (Refinado)"):
            with st.spinner("Desenhando a teia..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_grafo = f"""
                    Atue como um Designer de Informação.
                    TAREFA: Criar um Grafo de Conexões (Graphviz DOT) para MODO ESCURO.
                    
                    graph [bgcolor="#0e1117", layout=fdp, overlap=false, splines=curved, K=2.5];
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

# --- ABA 10: TIMELINE VISUAL ---
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
                    df, x="ano_numerico", y="grupo", 
                    hover_name="data_exibicao", 
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

# --- ABA 11: DASHBOARDS ---
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
        fig_bar = px.bar(df_dash, x="Entidade", y=["Militar", "Magia", "Economia", "Influencia"], barmode="group", title="Atributos", color_discrete_sequence=["#e63946", "#a8dadc", "#e6c200", "#457b9d"])
        fig_bar.update_layout(font_family="Lato", font_color="#d4d4d4", paper_bgcolor="#0e1117", plot_bgcolor="#161b22", legend_title_text='Atributo')
        st.plotly_chart(fig_bar, use_container_width=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🌍 Influência")
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

# --- ABA 12: MAPA ---
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
                fig = px.scatter(df_pins, x="x", y="y", hover_name="nome", hover_data={"x":False, "y":False, "desc":True}, title="Mapa Interativo")
                fig.add_layout_image(dict(source=img_pil, xref="x", yref="y", x=0, y=0, sizex=img_pil.width, sizey=img_pil.height, sizing="stretch", opacity=1, layer="below"))
                fig.update_xaxes(visible=False, range=[0, img_pil.width])
                fig.update_yaxes(visible=False, range=[img_pil.height, 0])
                fig.update_layout(width=img_pil.width, height=img_pil.height, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", hoverlabel=dict(bgcolor="#161b22", font_size=14))
                fig.update_traces(marker=dict(size=15, color='#e6c200', symbol='circle', line=dict(width=2, color='black')))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.image(img_pil, caption="Sem pins.", use_container_width=True)
        else:
            st.info("Clique na imagem para marcar um local.")
            coords = streamlit_image_coordinates(img_pil, key="click_map")
            if coords:
                with st.form("form_pin"):
                    nome_pin = st.text_input("Nome do Local")
                    desc_pin = st.text_area("Descrição")
                    vinculo = st.selectbox("Vincular a Texto Existente:", ["Nenhum"] + CATEGORIAS)
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
