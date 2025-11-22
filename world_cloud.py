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

# --- 🎨 ESTILO VISUAL (CSS MÁGICO) ---
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
        .stTabs [data-baseweb="tab"] { background-color: transparent; border-radius: 4px 4px 0 0; color: #8b949e
