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

# --- NOVO: CARREGAR CACHES ---
def carregar_cache_analises():
    # Tenta carregar as análises salvas para não gastar IA a toa
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

# --- NOVO: SALVAR CACHES ---
def salvar_cache_analise(tipo, dados):
    # Tipos: 'auditoria', 'sugestoes', 'erros', 'resumo_erros'
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

# --- 4. INICIALIZAÇÃO DE ESTADO COM CACHE ---
# Carrega os dados do banco na inicialização
caches_salvos = carregar_cache_analises()

if "sugestoes_ia" not in st.session_state: 
    st.session_state.sugestoes_ia = caches_salvos.get("sugestoes", {})

if "erros_ia" not in st.session_state: 
    st.session_state.erros_ia = caches_salvos.get("erros", {})

if "resumo_erros" not in st.session_state: 
    st.session_state.resumo_erros = caches_salvos.get("resumo_erros", "")

if "auditoria_dados" not in st.session_state:
    st.session_state.auditoria_dados = caches_salvos.get("auditoria", [])

if "messages" not in st.session_state: 
    st.session_state.messages = []

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
tab_editor, tab_chat, tab_aval, tab_sugestao, tab_erros, tab_mapa = st.tabs([
    "✍️ Editor", "🧠 Chat", "⚖️ Auditoria", "💡 Sugestões", "⚡ Incoerências", "🗺️ Mapa"
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
    st.header("Oráculo da Lore")
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
                except Exception as e: st.error(str(e))

# === ABA 3: AUDITORIA (CRÍTICA E PERSISTENTE) ===
with tab_aval:
    st.header("⚖️ Auditoria Implacável")
    with st.expander("📘 Metodologia (10 Pilares)", expanded=False):
        st.markdown("Critérios: Coerência, História, Cultura, Política, Economia, Magia, Religião, Geografia, Conflitos, Singularidade.")

    if not api_key: st.warning("Insira a API Key.")
    else:
        # Se já tiver dados no cache, avisa
        if st.session_state.auditoria_dados:
            st.info("Visualizando Auditoria do Cache (Salva no Banco). Clique abaixo para recalcular.")
            
        if st.button("🔄 Rodar Nova Auditoria (Sobrescrever Cache)"):
            with st.spinner("O Crítico está destruindo seus conceitos fracos..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    
                    # --- PROMPT BRUTAL ---
                    prompt_auditoria = f"""
                    VOCÊ É UM EDITOR LITERÁRIO SÊNIOR, CÍNICO E EXTREMAMENTE CRÍTICO (ESTILO GEORGE MARTIN EM UM DIA RUIM).
                    
                    SUA MISSÃO: Analisar o worldbuilding abaixo e DESTRUIR qualquer incoerência, clichê ou preguiça criativa.
                    Não seja educado. Seja realista. Se a economia não faz sentido, chame de estupidez. Se a magia não tem custo, chame de recurso narrativo fraco.
                    
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    
                    AVALIE ESTES 10 PILARES (Dê nota 0-10):
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
                        # Salva no Estado e no Banco
                        st.session_state.auditoria_dados = dados
                        salvar_cache_analise("auditoria", dados)
                        st.success("Auditoria Brutal Concluída e Salva!")
                    else: st.write(res.text)
                except Exception as e: st.error(str(e))
        
        # Exibe os dados (seja do cache ou novo)
        if st.session_state.auditoria_dados:
             for item in st.session_state.auditoria_dados:
                with st.expander(f"{item['titulo']} - Nota {item['nota']}"):
                    st.progress(item['nota']/10)
                    st.info(f"**Análise:** {item['analise']}")
                    st.warning(f"**Exigência:** {item['melhorias']}")

# === ABA 4: SUGESTÕES (PERSISTENTE) ===
with tab_sugestao:
    st.header("💡 Co-Autor Criativo")
    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.sugestoes_ia:
             st.info("Visualizando Sugestões Salvas.")
             
        if st.button("🔄 Gerar Novas Ideias (Sobrescrever Cache)", type="primary"):
            with st.spinner("Sonhando..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items()}
                    prompt = f"""
                    Atue como um Co-Autor Criativo.
                    TAREFA: Para CADA categoria, crie 3 a 5 TÓPICOS (Bullet Points) de ideias novas, plot twists ou segredos.
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    SAÍDA JSON: {{ "Categoria": "• Ideia 1\\n• Ideia 2", ... }}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt)
                    dados = extrair_json(res.text)
                    if dados:
                        st.session_state.sugestoes_ia = dados
                        salvar_cache_analise("sugestoes", dados)
                        st.success("Novas ideias salvas!")
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

# === ABA 5: INCOERÊNCIAS (BRUTAL E PERSISTENTE) ===
with tab_erros:
    st.header("⚡ Detector de Incoerências")
    with st.expander("📘 Metodologia", expanded=False):
        st.markdown("Cruzamento N x N. Cache Ativo.")

    if not api_key: st.warning("Insira a API Key.")
    else:
        if st.session_state.erros_ia:
             st.info("Visualizando Incoerências Salvas.")
             
        if st.button("🔄 Rastrear Contradições (Sobrescrever Cache)", type="primary"):
            with st.spinner("O Inquisidor está sendo implacável..."):
                try:
                    lore_ativo = {k:v for k,v in lore_data.items() if v.strip()}
                    
                    # --- PROMPT INQUISIDOR ---
                    prompt_erros = f"""
                    VOCÊ É UM INVESTIGADOR FORENSE DE LÓGICA E CONTINUIDADE.
                    Não seja "bonzinho". Seu trabalho é achar falhas. Seja pedante. Seja chato.
                    
                    TAREFA: 
                    1. Cruze TODOS os dados.
                    2. Se A contradiz B, aponte.
                    3. Se algo não faz sentido econômico ou físico, aponte.
                    
                    SAÍDA JSON: {{ "resumo_geral": "Veredito ácido...", "detalhes": {{ "Categoria": "• 🔴 ERRO: ...", ... }} }}
                    LORE: {json.dumps(lore_ativo, ensure_ascii=False)}
                    CATEGORIAS: {json.dumps(CATEGORIAS, ensure_ascii=False)}
                    """
                    model = genai.GenerativeModel(modelo_escolhido)
                    res = model.generate_content(prompt_erros)
                    dados_json = extrair_json(res.text)
                    if dados_json:
                        st.session_state.resumo_erros = dados_json.get("resumo_geral", "")
                        st.session_state.erros_ia = dados_json.get("detalhes", {})
                        
                        # Salva tudo no cache
                        salvar_cache_analise("erros", st.session_state.erros_ia)
                        salvar_cache_analise("resumo_erros", st.session_state.resumo_erros)
                        
                        st.success("Varredura completa e salva!")
                    else: st.write(res.text)
                except Exception as e: st.error(f"Erro: {e}")

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
                    if erro: st.error(f"🚨 **PROBLEMAS:**\n\n{erro}")
                    else: st.success("✅ Aprovado pelo Inquisidor")
                idx += 1
        st.divider()
        
    if st.session_state.erros_ia:
        criar_secao_erros("Geral", "Geral")
        criar_secao_erros("Timeline", "Timeline")
        criar_secao_erros("Povos", "Povo")

# === ABA 6: MAPA ===
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
