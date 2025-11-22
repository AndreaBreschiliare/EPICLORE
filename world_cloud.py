import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai
import json
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="World Architect Pro", layout="wide", page_icon="🏰")
st.title("🏰 World Architect: Lore & Co-Autor")

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

# --- 2. FUNÇÕES DE SUPORTE ---
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

def extrair_json(texto):
    try:
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match: return json.loads(match.group(1))
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match: return json.loads(match.group(0))
        return None
    except:
        return None

# --- 3. LISTA DE CATEGORIAS ---
CATEGORIAS = [
    # --- NOVAS ---
    "Absencia - Caos", "Radiancia - Ordem", "Warp", "Os 4 Cavaleiros",
    # --- GERAIS ---
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    # --- TIMELINE ---
    "Timeline - Cataclisma", "Timeline - Badlands", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    # --- POVOS ---
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

# --- 4. INTERFACE ---
st.sidebar.header("Configuração IA")
api_key = st.sidebar.text_input("Sua Google API Key (Gemini)", type="password")

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
            modelo_escolhido = st.sidebar.selectbox("Modelo IA:", lista_modelos, index=0)
    except Exception as e:
        st.sidebar.error(f"Erro IA: {e}")

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro Banco: {e}")
    st.stop()

# --- ABAS ---
tab_editor, tab_chat, tab_aval, tab_sugestao = st.tabs(["✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões"])

# === ABA 1: EDITOR (Visual: Meia Página | Capacidade: Infinita) ===
with tab_editor:
    st.info("As alterações são salvas automaticamente na nuvem.")
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
                    
                    # AJUSTE FINO: 500px de altura visual.
                    # Pode colar 300 páginas aqui que ele cria barra de rolagem.
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
    st.header("Oráculo da Lore")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if "messages" not in st.session_state: st.session_state.messages = []
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if prompt := st.chat_input("Pergunte ao Lore..."):
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
                except Exception as e: st.error(str(e))

# === ABA 3: AUDITORIA ===
with tab_aval:
    st.header("⚖️ Auditoria de Worldbuilding")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.button("🔍 Rodar Auditoria"):
            with st.spinner("Auditando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_auditoria = f"""
                    Atue como Crítico Literário. Analise este LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    Avalie os 10 pilares (Coerência, História, Cultura, Política, Economia, Magia, Religião, Geografia, Conflitos, Singularidade).
                    RETORNE JSON: [{{ "titulo": "...", "nota": 8, "analise": "...", "melhorias": "..." }}]
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_auditoria)
                    dados = extrair_json(res.text)
                    if dados:
                        for item in dados:
                            with st.expander(f"{item['titulo']} - Nota {item['nota']}"):
                                st.progress(item['nota']/10)
                                st.info(item['analise'])
                                st.warning(item['melhorias'])
                    else: st.write(res.text)
                except Exception as e: st.error(str(e))

# === ABA 4: SUGESTÕES ===
with tab_sugestao:
    st.header("💡 Co-Autor Criativo")
    if not api_key:
        st.warning("Insira a API Key para gerar sugestões.")
    else:
        if "sugestoes_ia" not in st.session_state:
            st.session_state.sugestoes_ia = {}
            
        if st.button("✨ Gerar Sugestões", type="primary"):
            with st.spinner("Sonhando com seu mundo..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items()}
                    prompt_sugestao = f"""
                    Atue como um Co-Autor de Fantasia Criativa.
                    SUA TAREFA: Para CADA categoria listada abaixo, escreva uma SUGESTÃO curta.
                    LORE ATUAL: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    FORMATO JSON PURO: {{ "Categoria": "Sugestão...", ... }}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_sugestao)
                    sugestoes_novas = extrair_json(res.text)
                    if sugestoes_novas:
                        st.session_state.sugestoes_ia = sugestoes_novas
                        st.success("Sugestões geradas!")
                    else: st.error("Erro no JSON.")
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
                    sugestao = st.session_state.sugestoes_ia.get(cat, "Clique no botão acima para gerar.")
                    st.text_area(f"💡 Ideia para: {cat}", value=sugestao, height=250, key=f"sug_{cat}", disabled=False)
                    if sugestao != "Clique no botão acima para gerar.":
                        st.caption("Gostou? Copie e cole na aba 'Editor'.")
                idx += 1
        st.divider()

    if st.session_state.sugestoes_ia:
        criar_secao_sugestao("Sugestões: Gerais", "Geral")
        criar_secao_sugestao("Sugestões: Timeline", "Timeline")
        criar_secao_sugestao("Sugestões: Povos", "Povo")
