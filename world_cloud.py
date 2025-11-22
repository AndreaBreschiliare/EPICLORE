import streamlit as st
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import google.generativeai as genai
import json
import re

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="World Architect Pro", layout="wide", page_icon="🏰")
st.title("🏰 World Architect: Lore & Auditoria")

# --- 1. CONEXÃO COM O BANCO DE DADOS (FIREBASE) ---
if not firebase_admin._apps:
    key_dict = json.loads(st.secrets["textkey"])
    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

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

# Função para extrair JSON limpo da resposta da IA (caso ela fale antes ou depois)
def extrair_json(texto):
    try:
        # Tenta encontrar o bloco json entre ```json e ```
        match = re.search(r"```json\n(.*?)\n```", texto, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # Se não achar, tenta achar o primeiro { e o último }
        match = re.search(r"\{.*\}", texto, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return None
    except:
        return None

# --- 3. LISTA DE CATEGORIAS ---
CATEGORIAS = [
    "Facções", "Epic! Aetherius", "Resumo Primeira Era", "Resumo Segunda Era", 
    "Cosmogenese - Resumo", "Origem por Povos (Geral)",
    "Timeline - Cataclisma", "Timeline - Elfos", "Timeline - Drows", 
    "Timeline - Anões", "Timeline - Orcs", "Timeline - Humanos", "Timeline - Pequilhos",
    "Povo - Aiglana", "Povo - Haroloth", "Povo - Leste", "Povo - Bjorska", 
    "Povo - Aluriel", "Povo - Baduran", "Povo - Gulthrak", "Povo - Polkinea"
]

CRITERIOS_AUDITORIA = [
    "1. Coerência Interna",
    "2. Profundidade Histórica",
    "3. Cultura e Antropologia",
    "4. Sistema Político",
    "5. Economia e Recursos",
    "6. Magia e Tecnologia",
    "7. Religião e Metafísica",
    "8. Ecologia e Geografia",
    "9. Conflitos Atuais",
    "10. Singularidade"
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
        st.sidebar.error(f"Erro: {e}")

try:
    lore_data = carregar_lore()
except Exception as e:
    st.error(f"Erro banco: {e}")
    st.stop()

# --- ABAS ---
tab_editor, tab_chat, tab_aval = st.tabs(["✍️ Editor", "🧠 Chat", "⚖️ Auditoria de Lore"])

# === ABA 1: EDITOR ===
with tab_editor:
    st.info("As alterações são salvas automaticamente na nuvem.")
    def criar_secao(titulo, filtro):
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
                    novo_val = st.text_area(cat, value=val_atual, height=150, key=f"txt_{cat}")
                    if st.button(f"💾 Salvar {cat}", key=f"btn_{cat}"):
                        salvar_categoria(cat, novo_val)
                        st.success("Salvo!")
                        st.rerun()
                idx += 1
        st.divider()

    criar_secao("📜 Documentos Gerais", "Geral")
    criar_secao("⏳ Timeline", "Timeline")
    criar_secao("🏰 Povos", "Povo")

# === ABA 2: CHAT ===
with tab_chat:
    st.header("Oráculo da Lore")
    if not api_key:
        st.warning("Insira a API Key.")
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

# === ABA 3: AUDITORIA (NOVA) ===
with tab_aval:
    st.header("⚖️ Auditoria de Worldbuilding")
    st.markdown("A IA vai ler todo o seu mundo e avaliar os 10 pilares fundamentais de uma Lore Medieval.")
    
    if not api_key:
        st.warning("Você precisa da API Key para rodar a auditoria.")
    else:
        if st.button("🔍 Rodar Auditoria Completa (Pode levar 1 minuto)", type="primary"):
            with st.spinner("O Auditor está lendo seus pergaminhos e julgando suas escolhas..."):
                try:
                    # 1. Prepara o Lore
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    lore_txt = json.dumps(lore_ativo, ensure_ascii=False)
                    
                    # 2. O Prompt Gigante de Avaliação
                    prompt_auditoria = f"""
                    Atue como um Crítico Literário Sênior especialista em Fantasia Medieval (estilo Tolkien/George Martin).
                    Analise o seguinte LORE MUNDIAL:
                    ---
                    {lore_txt}
                    ---

                    Sua tarefa é avaliar o mundo com base em 10 critérios.
                    Para cada critério, dê uma nota (0 a 10), um resumo da análise e sugestões de melhoria.
                    
                    OS 10 CRITÉRIOS SÃO:
                    1. Coerência Interna (Regras, Magia, Contradições)
                    2. Profundidade Histórica (Eras, Ruínas, Passado)
                    3. Cultura e Antropologia (Idiomas, Rituais, Vestimentas)
                    4. Sistema Político (Alianças, Guerras, Tensões)
                    5. Economia e Recursos (Comércio, Moeda, Sustento)
                    6. Magia/Tecnologia (Limites, Custos, Origem)
                    7. Religião e Metafísica (Deuses, Mitos, Vida após morte)
                    8. Ecologia e Geografia (Biomas, Clima, Mapas)
                    9. Conflitos Atuais (Tensões imediatas, ameaças)
                    10. Singularidade (O que torna este mundo único?)

                    FORMATO DE RESPOSTA OBRIGATÓRIO:
                    Retorne APENAS um JSON válido com esta estrutura exata para cada um dos 10 itens:
                    [
                        {{
                            "titulo": "1. Coerência Interna",
                            "nota": 8,
                            "analise": "O texto explica bem...",
                            "melhorias": "Faltou explicar..."
                        }},
                        ... repita para os 10 itens ...
                    ]
                    """
                    
                    # 3. Chama a IA
                    model = genai.GenerativeModel(modelo_escolhido)
                    # Força resposta JSON se o modelo suportar (Flash suporta melhor)
                    res = model.generate_content(prompt_auditoria)
                    
                    # 4. Processa o JSON
                    dados_auditoria = extrair_json(res.text)
                    
                    if dados_auditoria:
                        st.success("Auditoria Concluída!")
                        
                        # Loop para criar os cards
                        for item in dados_auditoria:
                            with st.expander(f"{item['titulo']} (Nota: {item['nota']}/10)"):
                                # Barra de Progresso colorida
                                cor_barra = "red"
                                if item['nota'] >= 7: cor_barra = "green"
                                elif item['nota'] >= 5: cor_barra = "yellow"
                                
                                st.progress(item['nota'] / 10)
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**🕵️ Análise:**")
                                    st.info(item['analise'])
                                with c2:
                                    st.markdown("**💡 Sugestões:**")
                                    st.warning(item['melhorias'])
                    else:
                        st.error("A IA retornou um texto, mas não consegui formatar em caixas. Veja o texto bruto abaixo:")
                        st.write(res.text)

                except Exception as e:
                    st.error(f"Erro na auditoria: {e}")
