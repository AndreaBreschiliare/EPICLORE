import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai
import json

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="World Architect Cloud", layout="wide", page_icon="☁️")
st.title("☁️ World Architect: Lore Colaborativo")

# --- 1. CONEXÃO COM O BANCO DE DADOS (FIREBASE) ---
# Verifica se já não inicializou para não dar erro de duplicidade
if not firebase_admin._apps:
    # Tenta pegar as credenciais dos "Segredos" do Streamlit Cloud
    key_dict = json.loads(st.secrets["textkey"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- 2. FUNÇÕES DE LEITURA/ESCRITA NA NUVEM ---
def carregar_lore():
    # Busca o documento "lore_oficial" na coleção "mundos"
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        # Se não existir, cria vazio
        dados_iniciais = {cat: "" for cat in CATEGORIAS}
        doc_ref.set(dados_iniciais)
        return dados_iniciais

def salvar_categoria(categoria, texto):
    # Atualiza apenas o campo específico no banco (merge=True)
    doc_ref = db.collection("mundos").document("lore_oficial")
    doc_ref.set({categoria: texto}, merge=True)

# --- 3. LISTA DE CATEGORIAS ---
CATEGORIAS = [
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    "Timeline - Cataclisma", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

# --- 4. INTERFACE ---
# Barra Lateral para API do Gemini (Cada usuário põe a sua ou você deixa uma fixa nos segredos)
api_key = st.sidebar.text_input("Sua Google API Key (Gemini)", type="password")
if api_key:
    genai.configure(api_key=api_key)

# Carrega dados da Nuvem
try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro ao conectar no banco: {e}")
    st.stop()

tab_editor, tab_chat = st.tabs(["✍️ Editor Compartilhado", "🧠 Chat com a Lore"])

# === EDITOR ===
with tab_editor:
    st.warning("⚠️ Atenção: As alterações aqui são salvas na nuvem para TODOS os usuários instantaneamente.")
    
    # Lógica de exibição agrupada
    def criar_secao(titulo, filtro):
        st.markdown(f"### {titulo}")
        cols = st.columns(2)
        idx = 0
        for cat in CATEGORIAS:
            if filtro in cat or (filtro == "Geral" and "Timeline" not in cat and "Povo" not in cat):
                # Filtro meio 'gambiarra' para simplificar, mas funciona
                mostrar = False
                if filtro == "Geral" and ("Timeline" not in cat and "Povo" not in cat): mostrar = True
                elif filtro != "Geral" and filtro in cat: mostrar = True
                
                if mostrar:
                    with cols[idx % 2]:
                        val_atual = lore_data.get(cat, "")
                        # Key única para o widget
                        novo_val = st.text_area(cat, value=val_atual, height=150, key=f"txt_{cat}")
                        
                        # Botão de Salvar Individual (Melhor para nuvem para economizar escritas)
                        if st.button(f"💾 Salvar {cat}", key=f"btn_{cat}"):
                            salvar_categoria(cat, novo_val)
                            st.success("Salvo na nuvem!")
                            st.rerun()
                    idx += 1
        st.divider()

    criar_secao("📜 Documentos Gerais", "Geral")
    criar_secao("⏳ Timeline", "Timeline")
    criar_secao("🏰 Povos", "Povo")

# === CHAT ===
with tab_chat:
    st.header("Oráculo da Lore")
    if not api_key:
        st.warning("Insira a chave do Gemini na esquerda.")
    else:
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        if prompt := st.chat_input("Pergunte ao Lore..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Pega dados frescos do banco
            lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
            contexto = json.dumps(lore_ativo, ensure_ascii=False)
            
            sys_prompt = f"Você é o assistente do mundo. Lore:\n{contexto}\nUsuário: {prompt}"
            
            with st.chat_message("assistant"):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    res = model.generate_content(sys_prompt)
                    st.markdown(res.text)
                    st.session_state.messages.append({"role": "assistant", "content": res.text})
                except Exception as e:
                    st.error(str(e))