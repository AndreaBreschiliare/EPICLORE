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

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="World Architect Pro", layout="wide", page_icon="🏰")
st.title("🏰 World Architect: Lore & Co-Autor")

# --- INICIALIZAÇÃO SEGURA DE ESTADO ---
if "sugestoes_ia" not in st.session_state: st.session_state.sugestoes_ia = {}
if "erros_ia" not in st.session_state: st.session_state.erros_ia = {}
if "resumo_erros" not in st.session_state: st.session_state.resumo_erros = ""
if "messages" not in st.session_state: st.session_state.messages = []
if "glossario" not in st.session_state: st.session_state.glossario = {}

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

# --- 4. INICIALIZAÇÃO DE ESTADO ---
caches_salvos = carregar_cache_analises()

if "sugestoes_ia" not in st.session_state: st.session_state.sugestoes_ia = caches_salvos.get("sugestoes", {})
if "erros_ia" not in st.session_state: st.session_state.erros_ia = caches_salvos.get("erros", {})
if "resumo_erros" not in st.session_state: st.session_state.resumo_erros = caches_salvos.get("resumo_erros", "")
if "auditoria_dados" not in st.session_state: st.session_state.auditoria_dados = caches_salvos.get("auditoria", [])
if "messages" not in st.session_state: st.session_state.messages = caches_salvos.get("chat_history", [])
# NOVO: Recupera Glossário
if "glossario" not in st.session_state: st.session_state.glossario = caches_salvos.get("glossario", {})

# --- 5. INTERFACE ---
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
tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_glossario, tab_mapa = st.tabs([
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", "📚 Glossário", "🗺️ Mapa"
])

# === ABA 1: EDITOR ===
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
    c1.header("Oráculo da Lore")
    if c2.button("🗑️ Limpar"):
        st.session_state.messages = []
        salvar_cache_analise("chat_history", [])
        st.rerun()

    if not api_key: st.warning("Insira a API Key.")
    else:
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
                    salvar_cache_analise("chat_history", st.session_state.messages)
                except Exception as e: st.error(str(e))

# === ABA 3: AUDITORIA ===
with tab_aval:
    st.header("⚖️ Auditoria Implacável")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.auditoria_dados: st.success("📂 Carregado da memória.")
        if st.button("🔄 Recalcular Auditoria"):
            with st.spinner("Auditando..."):
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
    st.header("💡 Co-Autor Criativo")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.sugestoes_ia: st.success("📂 Carregado da memória.")
        if st.button("🔄 Gerar Novas Ideias"):
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
    st.header("⚡ Detector de Incoerências")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.erros_ia: st.success("📂 Carregado da memória.")
        if st.button("🔄 Rastrear Contradições"):
            with st.spinner("Inquisidor trabalhando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    prompt_erros = f"""
                    Auditor Lógico. Cruze dados. Ache contradições.
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

# === ABA 6: GLOSSÁRIO AUTOMÁTICO (NOVA) ===
with tab_glossario:
    st.header("📚 Glossário Vivo")
    st.markdown("A IA lê todo o seu Lore e cria um dicionário de Termos, Nomes e Lugares.")

    # Botão de Geração
    if not api_key: st.warning("Insira a API Key.")
    else:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            if st.button("🔄 Gerar/Atualizar Glossário"):
                with st.spinner("Lendo todos os textos e compilando definições..."):
                    try:
                        lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                        prompt_glossario = f"""
                        Atue como um Bibliotecário Mágico.
                        TAREFA: Leia todo o texto abaixo e extraia uma lista de TERMOS IMPORTANTES (Nomes Próprios, Cidades, Magias, Raças, Eventos).
                        Para cada termo, escreva uma definição curta (1 frase).
                        
                        LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                        
                        FORMATO JSON OBRIGATÓRIO:
                        {{
                            "Aetherius": "O plano divino de onde emana a magia.",
                            "Elfos": "Raça imortal que vive nas florestas do norte.",
                            "Guerra das Cinzas": "Conflito que devastou o reino há 500 anos."
                        }}
                        """
                        model = genai.GenerativeModel(modelo_escolhido)
                        res = model.generate_content(prompt_glossario)
                        dados = extrair_json(res.text)
                        if dados:
                            st.session_state.glossario = dados
                            salvar_cache_analise("glossario", dados)
                            st.success(f"Glossário criado com {len(dados)} termos!")
                            st.rerun()
                        else: st.error("Erro ao gerar JSON.")
                    except Exception as e: st.error(f"Erro: {e}")
        
        with col_info:
            if st.session_state.glossario:
                st.info(f"📖 Termos catalogados: {len(st.session_state.glossario)}")

    st.divider()

    # --- O LEITOR INTELIGENTE ---
    c_leitor, c_termos = st.columns([2, 1])
    
    with c_leitor:
        st.subheader("📖 Leitor Contextual")
        # Dropdown para escolher o texto
        texto_escolhido = st.selectbox("Escolha um texto para ler:", CATEGORIAS)
        conteudo_texto = lore_data.get(texto_escolhido, "")
        
        if conteudo_texto:
            st.text_area("Leitura:", value=conteudo_texto, height=600, disabled=True)
        else:
            st.caption("Este texto está vazio.")

    with c_termos:
        st.subheader("🔍 Termos Neste Texto")
        if not st.session_state.glossario:
            st.warning("Gere o glossário primeiro!")
        elif not conteud_texto:
            st.write("...")
        else:
            # Lógica de busca: Verifica quais chaves do glossário aparecem no texto
            termos_encontrados = []
            for termo, definicao in st.session_state.glossario.items():
                if termo in conteudo_texto:
                    termos_encontrados.append((termo, definicao))
            
            if termos_encontrados:
                for t, d in termos_encontrados:
                    with st.expander(f"🔹 {t}", expanded=True):
                        st.write(d)
            else:
                st.info("Nenhum termo do glossário encontrado neste texto específico.")

    st.divider()
    # Lista completa no final (opcional)
    with st.expander("Ver Dicionário Completo (Todos os Termos)"):
        st.json(st.session_state.glossario)

# === ABA 7: MAPA ===
with tab_mapa:
    st.header("🗺️ Cartografia Oficial")
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
