# -*- coding: utf-8 -*-
import io
import re
import html
import json
import sqlite3
import smtplib
import os
import time
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import pandas as pd

# ---------------------------------------------------------
# 3. Chave da API Embutida e Inicialização
# ---------------------------------------------------------
API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=API_KEY)

# ---------------------------------------------------------
# CONSTANTES DU SISTEMA
# ---------------------------------------------------------
EMAIL_ADM = "autolabdiagai@gmail.com"

# ---------------------------------------------------------
# 1. Configuração da Página du Streamlit
# ---------------------------------------------------------
st.set_page_config(
    page_title="AUTOLAB DIAG AI",
    page_icon="🧠",
    layout="wide"
)

# ---------------------------------------------------------
# 2. Estilização CSS Global (Oculta menu GitHub & Marca D'água)
# ---------------------------------------------------------
st.markdown("""
<style>
    /* Oculta totalmente o cabeçalho superior, menu hamburguer, ícones du github e footer */
    #MainMenu {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stHeader"] {display: none !important; visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    footer {visibility: hidden !important;}
    
    /* Remove elementos flutuantes de ferramentas du Streamlit */
    div[data-testid="stToolbar"] {display: none !important;}
    
    /* Estilização da Barra de Carregamento (Borda verde neon e preenchimento azul) */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #00E5FF 0%, #0088FF 100%) !important;
        box-shadow: 0 0 12px rgba(0, 229, 255, 0.6);
        border-radius: 10px;
    }
    .stProgress > div > div {
        background-color: #032314 !important;
        border: 2px solid #00FF88 !important;
        border-radius: 12px !important;
        padding: 3px;
        box-shadow: 0 0 15px rgba(0, 255, 136, 0.3);
    }
    
    /* Marca D'água Sutil da Logo ao Fundo du Sistema */
    .stApp::before {
        content: "";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 450px;
        height: 450px;
        background-image: url("logo_autolab.jpeg");
        background-size: contain;
        background-repeat: no-repeat;
        background-position: center;
        opacity: 0.04;
        z-index: 0;
        pointer-events: none;
    }

    .stApp {
        background-color: #03140C;
        color: #00FF88 !important;
    }
    
    h1, h2, h3, h4, h5, h6, p, label, div, span, .stMarkdown {
        color: #00FF88 !important;
    }
    
    caption, .stCaption {
        color: #A7F3D0 !important;
    }

    .stButton>button {
        background: linear-gradient(135deg, #064E3B 0%, #022C22 100%);
        color: #00FF88 !important;
        border-radius: 10px;
        font-weight: 700;
        border: 1px solid #00FF88;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        box-shadow: 0 0 12px rgba(0, 255, 136, 0.25);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #047857 0%, #065F46 100%);
        box-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        color: #FFFFFF !important;
        transform: translateY(-1px);
    }

    /* Efeitos Pulsantes para Redes Sociais e Planos */
    @keyframes pulse-neon-social {
        0% { transform: scale(1); box-shadow: 0 0 10px rgba(0, 255, 136, 0.3); border-color: #00FF88; }
        50% { transform: scale(1.02); box-shadow: 0 0 22px rgba(0, 255, 136, 0.7); border-color: #FFD700; }
        100% { transform: scale(1); box-shadow: 0 0 10px rgba(0, 255, 136, 0.3); border-color: #00FF88; }
    }

    .social-card-pulsing {
        background: linear-gradient(145deg, #052E16 0%, #021C11 100%);
        border: 2px solid #00FF88;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        animation: pulse-neon-social 3s infinite ease-in-out;
        box-shadow: 0 8px 25px rgba(0,0,0,0.5);
        margin-bottom: 10px;
    }
    
    .social-title {
        color: #FFD700 !important;
        font-weight: 800;
        font-size: 1.2rem;
        margin-bottom: 10px;
    }

    .btn-custom {
        display: block;
        width: 100%;
        padding: 12px 0;
        border-radius: 10px;
        font-weight: 800;
        text-decoration: none !important;
        text-align: center;
        font-size: 0.95rem;
        margin-top: 12px;
        transition: transform 0.2s;
    }
    .btn-custom:hover { transform: translateY(-2px); color: #FFF !important; }
    .btn-yt { background: linear-gradient(135deg, #FF0000 0%, #B30000 100%); color: white !important; box-shadow: 0 0 12px rgba(255, 0, 0, 0.4); }
    .btn-fb { background: linear-gradient(135deg, #1877F2 0%, #0C4A9E 100%); color: white !important; box-shadow: 0 0 12px rgba(24, 119, 242, 0.4); }
    .btn-ig { background: linear-gradient(45deg, #f09433 0%,#e6683c 25%,#dc2743 50%,#cc2366 75%,#bc1888 100%); color: white !important; box-shadow: 0 0 12px rgba(220, 39, 67, 0.4); }
    .btn-wsp { background: linear-gradient(135deg, #25D366 0%, #128C7E 100%); color: white !important; box-shadow: 0 0 12px rgba(37, 211, 102, 0.4); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 4. Banco de Dados SQLite (Usuários + Fichas + Validade + Histórico)
# ---------------------------------------------------------
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            whatsapp TEXT,
            senha TEXT,
            fichas INTEGER DEFAULT 7,
            data_cadastro TEXT,
            data_expiracao_teste TEXT,
            data_expiracao_assinatura TEXT,
            scanners_cadastrados TEXT,
            programadores_cadastrados TEXT,
            documento TEXT,
            nome_empresa TEXT
        )
    ''')
    
    for col in ["senha", "data_expiracao_teste", "data_expiracao_assinatura", "scanners_cadastrados", "programadores_cadastrados", "documento", "nome_empresa"]:
        try:
            c.execute(f"ALTER TABLE usuarios ADD COLUMN {col} TEXT")
        except Exception:
            pass

    c.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            data TEXT,
            veiculo TEXT,
            dtc TEXT,
            sintomas TEXT,
            relatorio TEXT
        )
    ''')
    
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_futura_1ano = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    senha_adm_hash = hash_senha("autolab2026")
    
    c.execute('SELECT id FROM usuarios WHERE email = ?', (EMAIL_ADM,))
    if not c.fetchone():
        c.execute('''
            INSERT INTO usuarios (nome, email, whatsapp, senha, fichas, data_cadastro, data_expiracao_teste, data_expiracao_assinatura, documento, nome_empresa)
            VALUES (?, ?, ?, ?, 7, ?, ?, ?, ?, ?)
        ''', ("Administrador AutoLab", EMAIL_ADM, "(00) 00000-0000", senha_adm_hash, data_atual, data_futura_1ano, data_futura_1ano, "00.000.000/0001-00", "AUTOLAB DIAGNÓSTICOS"))
    else:
        c.execute('UPDATE usuarios SET fichas = 7, senha = ?, data_expiracao_assinatura = ?, documento = ?, nome_empresa = ? WHERE email = ?', (senha_adm_hash, data_futura_1ano, "00.000.000/0001-00", "AUTOLAB DIAGNÓSTICOS", EMAIL_ADM))
        
    conn.commit()
    conn.close()

init_db()

# ---------------------------------------------------------
# 5. Funções de Disparo de E-mail
# ---------------------------------------------------------
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_EMISSOR = "seuemail@autolab.com.br"
SENHA_EMISSOR = "suasenhaouappkey"

def enviar_email_boas_vindas(nome, email):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_EMISSOR
        msg['To'] = email
        msg['Subject'] = "🧠 Seja Bem-vindo ao AUTOLAB DIAG AI - 7 Dias de Teste Liberados!"
        
        corpo = f"""
        Olá, {nome}!
        
        Seu cadastro no AUTOLAB DIAG AI foi realizado com sucesso.
        Você ganhou 7 FICHAS com validade de 7 DIAS para testar nossa Inteligência Artificial em diagnósticos avançados.
        
        Acesse du sistema utilizando seu e-mail ({email}) e a senha cadastrada.
        
        Bons diagnósticos!
        Equipe AutoLab LOA
        """
        msg.attach(MIMEText(corpo, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_EMISSOR, SENHA_EMISSOR)
        server.send_message(msg)
        server.quit()
    except Exception:
        pass

def enviar_email_oferta_assinatura(nome, email):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_EMISSOR
        msg['To'] = email
        msg['Subject'] = "⚡ Seu período de teste expirou! Continue com du plano ilimitado"
        
        corpo = f"""
        Olá, {nome}!
        
        Notamos que seu período de teste de 7 dias (ou suas fichas) du AUTOLAB DIAG AI chegou ao fim.
        
        Para continuar realizando diagnósticos ilimitados, gerar relatórios em PDF para seus clientes e ter suporte exclusivo da AutoLab por 1 ano, assine du plano ideal para sua oficina:
        
        👉 Acesse: https://autolabbr.com.br/
        
        Dúvidas? Fale conosco no WhatsApp: https://wa.me/message/H6EI475WHRPFF1
        
        Abraços,
        Equipe AutoLab LOA
        """
        msg.attach(MIMEText(corpo, 'plain'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_EMISSOR, SENHA_EMISSOR)
        server.send_message(msg)
        server.quit()
    except Exception:
        pass

# ---------------------------------------------------------
# 6. Gerenciamento de Usuários e Validade de Acesso
# ---------------------------------------------------------
if "logado" not in st.session_state:
    st.session_state["logado"] = False
    st.session_state["user_email"] = ""
    st.session_state["user_nome"] = ""
    st.session_state["user_fichas"] = 0
    st.session_state["user_tipo_acesso"] = "teste"
    st.session_state["user_empresa"] = ""
    st.session_state["user_documento"] = ""
    st.session_state["user_whatsapp"] = ""

def verificar_status_usuario(email):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('SELECT nome, email, whatsapp, fichas, senha, data_expiracao_teste, data_expiracao_assinatura, documento, nome_empresa FROM usuarios WHERE email = ?', (email.strip().lower(),))
    res = c.fetchone()
    conn.close()
    
    if not res:
        return None
        
    nome, mail, wsp, fichas, senha_cad, exp_teste, exp_assinatura, documento, nome_empresa = res
    agora = datetime.now()
    
    dados_user = {
        "nome": nome, "email": mail, "whatsapp": wsp, "fichas": fichas, 
        "documento": documento if documento else "00.000.000/0001-00", 
        "nome_empresa": nome_empresa if nome_empresa else "AUTOLAB DIAGNÓSTICOS"
    }
    
    if exp_assinatura:
        try:
            dt_exp_ass = datetime.strptime(exp_assinatura, "%Y-%m-%d %H:%M:%S")
            if agora < dt_exp_ass:
                dados_user["tipo"] = "assinante"
                dados_user["exp"] = exp_assinatura
                dados_user["fichas"] = 999
                return dados_user
        except Exception:
            pass

    if exp_teste:
        try:
            dt_exp_t = datetime.strptime(exp_teste, "%Y-%m-%d %H:%M:%S")
            if agora <= dt_exp_t and fichas > 0:
                dados_user["tipo"] = "teste"
                dados_user["exp"] = exp_teste
                return dados_user
        except Exception:
            pass
            
    dados_user["tipo"] = "expirado"
    dados_user["exp"] = "Expirado"
    dados_user["fichas"] = 0
    return dados_user

def autenticar_usuario(email, senha):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    senha_h = hash_senha(senha)
    c.execute('SELECT senha FROM usuarios WHERE email = ?', (email.strip().lower(),))
    res = c.fetchone()
    conn.close()
    
    if res and (res[0] == senha_h or (not res[0] and senha == "123456")):
        return verificar_status_usuario(email)
    return None

def atualizar_fichas_banco(email, novas_fichas):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('UPDATE usuarios SET fichas = ? WHERE email = ?', (novas_fichas, email.strip().lower()))
    conn.commit()
    conn.close()

def cadastrar_usuario(nome, email, whatsapp, senha, documento, nome_empresa):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    agora = datetime.now()
    data_atual_str = agora.strftime("%Y-%m-%d %H:%M:%S")
    data_exp_teste_str = (agora + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    senha_h = hash_senha(senha)
    
    try:
        c.execute('''
            INSERT INTO usuarios (nome, email, whatsapp, senha, fichas, data_cadastro, data_expiracao_teste, documento, nome_empresa)
            VALUES (?, ?, ?, ?, 7, ?, ?, ?, ?)
        ''', (nome.strip(), email.strip().lower(), whatsapp.strip(), senha_h, data_atual_str, data_exp_teste_str, documento.strip(), nome_empresa.strip()))
        conn.commit()
        conn.close()
        enviar_email_boas_vindas(nome, email)
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

if st.session_state.get("user_email") == EMAIL_ADM:
    st.session_state["user_fichas"] = 999

# ---------------------------------------------------------
# 7. Tela de Login, Cadastro e Planos na Home (High-Tech)
# ---------------------------------------------------------
def renderizar_css_planos():
    st.markdown("""
    <style>
        @keyframes pulse-yellow {
            0% { transform: scale(1); text-shadow: 0 0 10px rgba(255, 215, 0, 0.6); }
            50% { transform: scale(1.03); text-shadow: 0 0 22px rgba(255, 215, 0, 0.9); }
            100% { transform: scale(1); text-shadow: 0 0 10px rgba(255, 215, 0, 0.6); }
        }
        @keyframes border-pulse {
            0% { border-color: rgba(255, 215, 0, 0.5); box-shadow: 0 0 12px rgba(255, 215, 0, 0.2); }
            50% { border-color: rgba(255, 215, 0, 1); box-shadow: 0 0 25px rgba(255, 215, 0, 0.6); }
            100% { border-color: rgba(255, 215, 0, 0.5); box-shadow: 0 0 12px rgba(255, 215, 0, 0.2); }
        }
        @keyframes btn-pulse {
            0% { box-shadow: 0 0 10px rgba(255, 215, 0, 0.4); }
            50% { box-shadow: 0 0 22px rgba(255, 215, 0, 0.8); }
            100% { box-shadow: 0 0 10px rgba(255, 215, 0, 0.4); }
        }

        .pulsing-title { animation: pulse-yellow 2s infinite ease-in-out; color: #FFD700 !important; font-weight: 800; }
        .extreme-badge { background-color: #03140C; color: #FFD700 !important; border: 2px solid #FFD700; padding: 4px 14px; border-radius: 8px; font-weight: 900; font-size: 11px; letter-spacing: 1.5px; animation: pulse-yellow 1.5s infinite ease-in-out; display: inline-block; margin-bottom: 8px; box-shadow: 0 0 15px rgba(255, 215, 0, 0.4); }
        .card-lux-1, .card-lux-3 { background: linear-gradient(145deg, #052E16 0%, #021C11 100%); padding: 20px; border-radius: 16px; border: 1px solid #065F46; text-align: center; min-height: 380px; box-shadow: 0 8px 25px rgba(0,0,0,0.5); }
        .card-lux-extreme { background: linear-gradient(145deg, #022C22 0%, #011611 100%); padding: 20px; border-radius: 16px; border: 2px solid #FFD700; text-align: center; min-height: 380px; animation: border-pulse 3s infinite ease-in-out; box-shadow: 0 8px 30px rgba(255, 215, 0, 0.25); }
        .btn-pulsing-link { display: block; width: 100%; background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); color: #03140C !important; padding: 10px 0; border-radius: 10px; font-weight: 800; text-decoration: none !important; text-align: center; font-size: 0.9rem; animation: btn-pulse 2s infinite ease-in-out; margin-top: 15px; transition: transform 0.2s; }
        .btn-pulsing-link:hover { transform: translateY(-2px); background: linear-gradient(135deg, #FFEE55 0%, #FFB700 100%); color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

def tela_login():
    url_video_fundo = "https://assets.mixkit.co/videos/preview/mixkit-digital-animation-of-screens-and-data-41538-large.mp4"
    link_reels = "https://www.instagram.com/reel/DbGLJBPR0pL/embed"

    st.markdown("""
    <style>
        .stApp { background-color: #03140C !important; }
        [data-testid="stSidebar"] { display: none !important; }
        
        .main .block-container { background: transparent !important; padding-top: 1rem !important; max-width: 1300px; }
        
        .video-bg-container {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            z-index: -999; overflow: hidden; background: #03140C;
        }
        .video-bg-container video {
            width: 100vw; height: 100vh; object-fit: cover;
            filter: brightness(0.3) contrast(1.25);
        }
        .video-mask {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            background: radial-gradient(circle, rgba(3, 20, 12, 0.3) 0%, rgba(2, 12, 8, 0.9) 100%);
        }

        div[data-testid="stForm"], div.stBlock-col {
            background: rgba(3, 20, 12, 0.88) !important;
            backdrop-filter: blur(14px) !important;
            border: 1px solid rgba(0, 255, 136, 0.45) !important;
            border-radius: 18px !important;
            padding: 22px !important;
            box-shadow: 0 0 35px rgba(0, 255, 136, 0.25) !important;
        }

        .impact-box {
            background: linear-gradient(135deg, rgba(5, 46, 22, 0.88) 0%, rgba(2, 44, 34, 0.92) 100%);
            border: 1px solid #00FF88;
            border-radius: 16px;
            padding: 22px;
            box-shadow: 0 0 22px rgba(0, 255, 136, 0.25);
            margin-bottom: 20px;
        }

        .device-badge {
            display: inline-block;
            background-color: rgba(0, 255, 136, 0.15);
            border: 1px solid #00FF88;
            color: #00FF88;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 0.85rem;
            margin-right: 8px;
            margin-top: 10px;
        }
    </style>

    <div class="video-bg-container">
        <video autoplay loop muted playsinline>
            <source src="https://assets.mixkit.co/videos/preview/mixkit-digital-animation-of-screens-and-data-41538-large.mp4" type="video/mp4">
        </video>
        <div class="video-mask"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center; color: #00FF88; font-weight: 900; text-shadow: 0 0 20px rgba(0,255,136,0.8); font-size: 2.5rem; margin-bottom: 5px;'>🧠 AUTOLAB DIAG AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #FFD700; font-size: 1.15rem; font-weight: 700; text-shadow: 0 0 10px rgba(255,215,0,0.5); margin-bottom: 25px;'>O Assistente de Diagnóstico mais rápido du mundo à sua disposição</p>", unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # PLAYER DE ÁUDIO ROBUSTO (VELOCIDADE 1.25X)
    # ---------------------------------------------------------
    st.markdown("""
    <div style="background: linear-gradient(135deg, #052E16 0%, #022C22 100%); border: 2px solid #00FF88; padding: 15px; border-radius: 14px; text-align: center; margin-bottom: 25px; box-shadow: 0 0 25px rgba(0,255,136,0.35);">
        <h4 style="color: #FFD700 !important; margin-bottom: 6px; font-size: 1.1rem;">🔊 APRESENTAÇÃO EXCLUSIVA 🔊</h4>
        <p style="color: #A7F3D0 !important; font-size: 0.9rem; margin-bottom: 12px;">Aperte du play e descubra como du AutoLab Diag AI vai revolucionar sua oficina:</p>
    </div>
    """, unsafe_allow_html=True)

    caminho_audio = "davinci__ei__voc__mesmo_a__na_bancada____d__uma_olhada_nis.mp3"
    if os.path.exists(caminho_audio):
        import base64
        with open(caminho_audio, "rb") as f:
            audio_bytes = f.read()
        audio_base64 = base64.b64encode(audio_bytes).decode()
        
        st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <audio id="audio_autolab_v2" controls style="width: 100%; max-width: 500px;">
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                Seu navegador não suporta du elemento de áudio.
            </audio>
            <script>
                var aud = document.getElementById('audio_autolab_v2');
                if(aud) {{
                    aud.playbackRate = 1.25;
                    aud.defaultPlaybackRate = 1.25;
                }}
            </script>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"⚠️ Arquivo de áudio não encontrado na pasta: {caminho_audio}")

    col_info, col_forms = st.columns([1.1, 0.9], gap="large")
    
    with col_info:
        st.markdown("""
        <div class="impact-box">
            <h3 style="color: #00FF88 !important; font-size: 1.25rem; font-weight: 800; margin-bottom: 12px; line-height: 1.4;">
                ⚡ Imagine um Assistente à sua disposição 24 horas por dia fazendo Diagnósticos complexos em tempo recorde! ⚡
            </h3>
            <p style="color: #A7F3D0 !important; font-size: 0.95rem; line-height: 1.5; margin-bottom: 12px;">
                Agora sua oficina não precisa mais pagar treinamentos avançados para todos os mecânicos, com du AUTOLAB DIAG AI você faz diagnósticos Complexos em Tempo recorde, basta Alimentar du sistema com os Sintomas e Paramêtros dos Veículos através de textos, áudios, fotos e videos que du AUTOLAB DIAG AI faz du diagnóstico e entrega um passo a passo completo e detalhado com relatório técnico completo para que seus Mecânicos, Chaveiros E Eletricistas façam os testes conforme a instrução du Diagnóstico Inteligente gerado.
            </p>
            <p style="color: #FFD700 !important; font-size: 0.95rem; font-weight: 700; margin-bottom: 15px;">
                🌐 Alimentado pelo maior banco de dados técnico existente du mundo através de Inteligência Artificial 💻.
            </p>
            <div>
                <span class="device-badge">💻 100% Otimizado para Computadores</span>
                <span class="device-badge">📱 100% Otimizado para Celulares</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        celular_reels_html = f"""
        <div style="display: flex; justify-content: center; align-items: center; margin-bottom: 25px;">
            <div style="
                width: 270px; 
                height: 420px; 
                background: linear-gradient(135deg, #00FF88 0%, #FFD700 100%);
                padding: 5px; 
                border-radius: 32px; 
                box-shadow: 0px 0px 25px rgba(0, 255, 136, 0.4);
            ">
                <div style="
                    width: 100%; 
                    height: 100%; 
                    background-color: #000; 
                    border-radius: 28px; 
                    overflow: hidden; 
                    position: relative;
                ">
                    <div style="
                        position: absolute; top: 0; left: 50%; transform: translateX(-50%); 
                        width: 70px; height: 14px; background-color: #111; 
                        border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; z-index: 10;
                    "></div>
                    <iframe 
                        src="{link_reels}" 
                        width="100%" 
                        height="100%" 
                        frameborder="0" 
                        scrolling="no" 
                        allowtransparency="true"
                        style="border:none; overflow:hidden;">
                    </iframe>
                </div>
            </div>
        </div>
        """
        st.markdown(celular_reels_html, unsafe_allow_html=True)

    with col_forms:
        aba_acesso, aba_cadastro = st.tabs(["💻 ÁREA DE ACESSO 📱", "📝 Criar Conta / Teste por 7 Dias)"])
        
        with aba_acesso:
            st.subheader("🕵️‍♂️ Acesso du Usuário 💻📱")
            email_login = st.text_input("E-mail Cadastrado", key="email_log_input")
            senha_login = st.text_input("Sua Senha", type="password", key="senha_log_input")
            
            if st.button("Entrar", width="stretch"):
                if email_login and senha_login:
                    usr = autenticar_usuario(email_login, senha_login)
                    if usr:
                        st.session_state["logado"] = True
                        st.session_state["user_nome"] = usr["nome"]
                        st.session_state["user_email"] = usr["email"]
                        st.session_state["user_fichas"] = usr["fichas"]
                        st.session_state["user_tipo_acesso"] = usr["tipo"]
                        st.session_state["user_empresa"] = usr["nome_empresa"]
                        st.session_state["user_documento"] = usr["documento"]
                        st.session_state["user_whatsapp"] = usr["whatsapp"]
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos, ou período de teste de 7 dias expirado.")
                else:
                    st.warning("Por favor, preencha du e-mail e a senha.")

        with aba_cadastro:
            st.subheader("🚀 Teste sem Custos (7 Créditos por 7 Dias)")
            
            with st.form("form_cadastro_autolab"):
                nome_cad = st.text_input("Nome Completo / Oficina", key="nome_cad_input")
                doc_cad = st.text_input("CPF ou CNPJ", key="doc_cad_input", placeholder="Ex: 000.000.000-00 ou 00.000.000/0001-00")
                email_cad = st.text_input("E-mail Principal", key="email_cad_input")
                wsp_cad = st.text_input("WhatsApp com DDD", key="wsp_cad_input")
                senha_cad = st.text_input("Crie uma Senha", type="password", key="senha_cad_input")
                senha_conf = st.text_input("Confirme a Senha", type="password", key="senha_conf_input")
                
                btn_enviar_cadastro = st.form_submit_button("Criar Conta & Iniciar Teste")
            
            if btn_enviar_cadastro:
                if nome_cad.strip() and doc_cad.strip() and email_cad.strip() and wsp_cad.strip() and senha_cad.strip():
                    if senha_cad == senha_conf:
                        # Chamando a função passando o CPF/CNPJ junto
                        sucesso = cadastrar_usuario(nome_cad, email_cad, wsp_cad, senha_cad, doc_cad, "AUTOLAB DIAGNÓSTICOS")
                        if sucesso:
                            st.success("🎉 Conta criada com sucesso! 7 Fichas e 7 dias de teste liberados. Faça login na aba ao lado.")
                        else:
                            st.error("⚠️ Este e-mail já está cadastrado no sistema.")
                    else:
                        st.error("⚠️ As senhas não coincidem. Digite novamente.")
                else:
                    st.warning("⚠️ Por favor, preencha todos os campos para se cadastrar.")

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin-top: 25px; margin-bottom: 30px;">
        <a href="https://wa.me/message/H6EI475WHRPFF1" target="_blank" style="
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
            color: white !important;
            padding: 16px 32px;
            border-radius: 40px;
            font-weight: 900;
            text-decoration: none;
            font-size: 1.15rem;
            box-shadow: 0 0 30px rgba(37, 211, 102, 0.6);
            transition: transform 0.2s;
        ">
            <span style="font-size: 1.4rem; margin-right: 12px;">💬</span> DÚVIDAS? FALE COM SUPORTE AUTOLAB LOA
        </a>
    </div>
    """, unsafe_allow_html=True)

    renderizar_css_planos()
    st.markdown("<h3 style='text-align: center; color: #00FF88;'>💎 Conheça Nossos Planos Anuais (Acesso Ilimitado por 1 Ano) 💎 </h3>", unsafe_allow_html=True)
    st.write("<p style='text-align: center; color: #A7F3D0;'>Escolha du nível ideal para a sua oficina e tenha du AUTOLAB DIAG AI à sua disposição.</p>", unsafe_allow_html=True)
    st.write("")

    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.markdown("""
        <div class="card-lux-1">
            <div style="font-size: 26px; margin-bottom: 5px;">🛡️</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px; font-size: 1.1rem;">NÍVEL 1 - AMADOR</h4>
            <h2 style="color: #FFD700 !important; font-size: 1.8rem; margin-top: 5px;">R$ 57<span style="font-size: 12px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 12px 0;">
            <p style="color: #00FF88 !important; font-size: 13px; text-align: left; margin: 6px 0;">✨ <b>AUTOLAB DIAG</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 5px 0;">✔️ Diagnósticos com IA avançada</p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 5px 0;">✔️ Relatórios em PDF</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F3rcpp" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 1</a>', unsafe_allow_html=True)

    with col_p2:
        st.markdown("""
        <div class="card-lux-extreme">
            <div><span class="extreme-badge">🌟 EXTREME</span></div>
            <div style="font-size: 26px; margin-bottom: 2px;">⚡</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px; font-size: 1.1rem;">NÍVEL 2 - PROFISSIONAL</h4>
            <h2 style="color: #FFD700 !important; font-size: 1.8rem; margin-top: 5px;">R$ 97<span style="font-size: 12px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 12px 0;">
            <p style="color: #00FF88 !important; font-size: 13px; text-align: left; margin: 6px 0;">🚀 <b>AUTOLAB DIAG + SUPORTE</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 5px 0;">✔️ Diagnósticos ilimitados</p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 5px 0;">✔️ Suporte Técnico Especializado</p>
            <p style="color: #FFD700 !important; font-size: 11.5px; text-align: left; margin-top: 6px;"><b>🕒 Seg / Qua / Sex: 08h às 18h</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F4Kxw7" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 2</a>', unsafe_allow_html=True)

    with col_p3:
        st.markdown("""
        <div class="card-lux-3">
            <div style="font-size: 26px; margin-bottom: 5px;">👑</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px; font-size: 1.1rem;">NÍVEL 3 - ESPECIALISTA</h4>
            <h2 style="color: #FFD700 !important; font-size: 1.8rem; margin-top: 5px;">R$ 197<span style="font-size: 12px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 12px 0;">
            <p style="color: #00FF88 !important; font-size: 13.5px; text-align: left; margin: 6px 0;">🏆 <b>PACOTE COMPLETO MÁXIMO</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 4px 0;">✔️ AutoLab Diag + Banco de Dados</p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 4px 0;">✔️ Curso Completo (Programação de ECU)</p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 4px 0;">✔️ Suporte Técnico Prioritário</p>
            <p style="color: #FFD700 !important; font-size: 11.5px; text-align: left; margin-top: 6px;"><b>🕒 Seg / Qua / Sex: 08h às 18h</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F5BAYN" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 3</a>', unsafe_allow_html=True)

if not st.session_state["logado"]:
    tela_login()
    st.stop()

# ---------------------------------------------------------
# 9. Barra Lateral (Sidebar) com Dados da Oficina Editáveis & Logo
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <style>
        @keyframes pulse-red-alert {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.8); background-color: rgba(239, 68, 68, 0.2); }
            70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); background-color: rgba(239, 68, 68, 0.4); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); background-color: rgba(239, 68, 68, 0.2); }
        }
        
        .fichas-esgotadas-box {
            border: 2px solid #EF4444;
            color: #EF4444 !important;
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            font-weight: 800;
            font-size: 1.05rem;
            animation: pulse-red-alert 1.8s infinite;
            margin-bottom: 15px;
        }

        .fichas-ok-box {
            border: 1px solid #10B981;
            background-color: rgba(16, 185, 129, 0.15);
            color: #00FF88 !important;
            padding: 10px;
            border-radius: 10px;
            text-align: center;
            font-weight: 700;
            margin-bottom: 15px;
        }
    </style>
    """, unsafe_allow_html=True)
        
    col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
    with col_logo2:
        caminho_foto = "logo_autolab.jpeg"
        if os.path.exists(caminho_foto):
            try:
                imagem_pil = Image.open(caminho_foto)
                st.image(imagem_pil, width=120)
            except Exception:
                st.markdown("🚗 **AutoLab**", unsafe_allow_html=True)
        else:
            st.markdown("🚗 **AutoLab**", unsafe_allow_html=True)
    
    st.markdown("🕵️‍♂️ **Agente de Diagnóstico**")
    st.markdown("---")

    tipo_acesso_atual = st.session_state.get('user_tipo_acesso', 'teste')
    fichas_atuais = st.session_state.get('user_fichas', 0)

    if tipo_acesso_atual == "assinante":
        st.markdown('<div class="fichas-ok-box">👑 Plano Anual Ativo (Ilimitado)</div>', unsafe_allow_html=True)
    elif fichas_atuais <= 0:
        st.markdown('<div class="fichas-esgotadas-box">🎟️ Teste Expirado (0 Fichas / 7 Dias)</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="fichas-ok-box">🎟️ Fichas de Teste: ({fichas_atuais}/7)</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("🏢 Dados da Oficina (Editáveis)")
    
    # Vincula com os dados vindos do login ou sessão
    val_empresa_sessao = st.session_state.get('user_empresa', 'AUTOLAB DIAGNÓSTICOS')
    val_doc_sessao = st.session_state.get('user_documento', '00.000.000/0001-00')
    val_wsp_sessao = st.session_state.get('user_whatsapp', '(00) 00000-0000')

    nome_oficina = st.text_input("Nome da Oficina / Empresa", value=val_empresa_sessao)
    cnpj_oficina = st.text_input("CNPJ / CPF", value=val_doc_sessao)
    tel_oficina = st.text_input("Telefone/WhatsApp", value=val_wsp_sessao)

    # Armazena na sessão global para acesso nos relatórios
    st.session_state.oficina_nome = nome_oficina
    st.session_state.oficina_cnpj = cnpj_oficina
    st.session_state.oficina_tel = tel_oficina

    st.markdown("---")
    # BOTÃO DE SAIR COM ÍCONE DE PORTA NA BARRA LATERAL
    if st.button("🚪 Sair du Sistema", key="btn_sair_sistema_sidebar", type="primary", use_container_width=True):
        st.session_state["logado"] = False
        st.session_state["user_email"] = ""
        st.session_state["user_nome"] = ""
        st.rerun()

# ---------------------------------------------------------
# 10. Funções de Apoio (Histórico, PDF e Arquivos Binários)
# ---------------------------------------------------------
def salvar_diagnostico(email, veiculo, dtc, sintomas, relatorio):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute('''
        INSERT INTO historico (user_email, data, veiculo, dtc, sintomas, relatorio)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (email, data_atual, veiculo, dtc, sintomas, relatorio))
    conn.commit()
    conn.close()

def carregar_historico(email):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('SELECT id, data, veiculo, dtc, sintomas, relatorio FROM historico WHERE user_email = ? ORDER BY id DESC', (email,))
    registros = c.fetchall()
    conn.close()
    return registros

def contar_diagnosticos(email):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM historico WHERE user_email = ?', (email,))
    total = c.fetchone()[0]
    conn.close()
    return total

def obter_detalhes_usuario_banco(email):
    conn = sqlite3.connect('diagnosticos.db')
    c = conn.cursor()
    c.execute('SELECT data_cadastro, data_expiracao_teste, data_expiracao_assinatura FROM usuarios WHERE email = ?', (email.strip().lower(),))
    res = c.fetchone()
    conn.close()
    if res:
        return res[0], res[1], res[2]
    return "N/A", "N/A", "N/A"

def gerar_pdf_relatorio(nome_oficina, cnpj, telefone, veiculo, dtc, sintomas, relatorio_texto, titulo_pdf="AUTOLAB DIAG AI", imagem_placa_pil=None, imagens_ferramentas=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=16,
        textColor=colors.HexColor('#047857'), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9,
        textColor=colors.HexColor('#555555'), spaceAfter=10
    )
    h2_style = ParagraphStyle(
        'H2Style', parent=styles['Heading2'],
        fontName='Helvetica-Bold', fontSize=12,
        textColor=colors.HexColor('#065F46'), spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9.5, leading=13,
        textColor=colors.HexColor('#222222')
    )
    
    story = []
    nome_clean = html.escape(nome_oficina.upper())
    story.append(Paragraph(f"<b>{nome_clean}</b> | AUTOLAB DIAG AI", title_style))
    header_info = f"CNPJ/CPF: {html.escape(cnpj)} | Tel: {html.escape(telefone)} | Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    story.append(Paragraph(header_info, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#047857'), spaceAfter=12))
    
    data_veiculo = [
        [Paragraph("<b>Veículo/Módulo:</b>", body_style), Paragraph(html.escape(veiculo), body_style)],
        [Paragraph("<b>Códigos/Ref:</b>", body_style), Paragraph(html.escape(dtc) if dtc else "Nenhum informado", body_style)],
        [Paragraph("<b>Sintomas/Solicitação:</b>", body_style), Paragraph(html.escape(sintomas) if sintomas else "Análise Multimídia / Eletrônica", body_style)]
    ]
    
    t = Table(data_veiculo, colWidths=[110, 430])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ECFDF5')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A7F3D0')),
        ('PADDING', (0,0), (-1,-1), 5),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(Paragraph(titulo_pdf, h2_style))

    if imagem_placa_pil is not None:
        try:
            img_io = io.BytesIO()
            im_copia = imagem_placa_pil.copy()
            im_copia.thumbnail((450, 320))
            im_copia.save(img_io, format='JPEG', quality=90)
            img_io.seek(0)
            rl_img = RLImage(img_io, width=im_copia.width, height=im_copia.height)
            story.append(Spacer(1, 5))
            story.append(rl_img)
            story.append(Spacer(1, 10))
        except Exception as e:
            print(f"Erro ao inserir imagem du PDF: {e}")

    if imagens_ferramentas:
        story.append(Paragraph("<b>🛠️ EQUIPAMENTOS RECOMENDADOS PARA ESTA BANCADA:</b>", h2_style))
        for nome_ferramenta, img_fer_pil in imagens_ferramentas.items():
            if img_fer_pil:
                try:
                    f_io = io.BytesIO()
                    f_copia = img_fer_pil.copy()
                    f_copia.thumbnail((160, 120))
                    f_copia.save(f_io, format='JPEG', quality=85)
                    f_io.seek(0)
                    r_f = RLImage(f_io, width=f_copia.width, height=f_copia.height)
                    story.append(Paragraph(f"<b>• {nome_ferramenta}</b>", body_style))
                    story.append(r_f)
                    story.append(Spacer(1, 4))
                except Exception: pass
    
    linhas = relatorio_texto.split('\n')
    for linha in linhas:
        linha_str = linha.strip()
        if linha_str:
            linha_segura = html.escape(linha_str)
            linha_formatada = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', linha_segura)
            try:
                story.append(Paragraph(linha_formatada, body_style))
            except Exception:
                texto_puro = re.sub(r'<[^>]*>', '', linha_formatada)
                story.append(Paragraph(texto_puro, body_style))
            story.append(Spacer(1, 3))
            
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#cccccc'), spaceAfter=8))
    story.append(Paragraph("<i>Laudo técnico gerado por Inteligência Artificial - AUTOLAB DIAG AI.</i>", subtitle_style))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def gerar_foto_equipamento(nome_equipamento):
    img_eq = Image.new('RGB', (300, 180), color=(5, 46, 22))
    d = ImageDraw.Draw(img_eq)
    d.rectangle([5, 5, 295, 175], outline=(0, 255, 136), width=2)
    try:
        font_titulo = ImageFont.truetype("arial.ttf", size=13)
        font_sub = ImageFont.truetype("arial.ttf", size=11)
    except Exception:
        font_titulo = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    d.text((15, 20), "AUTOLAB PRO-GEAR", fill=(255, 215, 0), font=font_titulo)
    d.line([15, 40, 285, 40], fill=(6, 95, 70), width=2)
    palavras = nome_equipamento.split()
    linha1 = " ".join(palavras[:3])
    linha2 = " ".join(palavras[3:])
    d.text((15, 65), linha1, fill=(255, 255, 255), font=font_titulo)
    if linha2:
        d.text((15, 88), linha2, fill=(255, 255, 255), font=font_titulo)
    d.text((15, 135), "✅ Homologado Oficina AutoLab", fill=(167, 243, 208), font=font_sub)
    return img_eq

# ---------------------------------------------------------
# FUNÇÃO 1: MAPEAMENTO COLORIDO POR CIRCUITOS
# ---------------------------------------------------------
def processar_e_desenhar_mapa_placa(imagem_pil, identificacao_uce):
    largura, altura = imagem_pil.size
    prompt_mapeamento = f"""
    Analise esta foto da placa da UCE ({identificacao_uce}) e identifique os principais setores e componentes visíveis.
    Retorne EXCLUSIVAMENTE um objeto JSON válido contendo a chave "regioes", onde cada item possui:
    - "rotulo": Nome du circuito/componente (Ex: "MCU", "EEPROM", "DRIVER INJETOR", "REGULADOR 5V")
    - "cor": Nome da cor ("green", "blue", "yellow", "red", "magenta", "cyan")
    - "caixa": Coordenadas normalizadas de 0 a 1000 [ymin, xmin, ymax, xmax].
    EXEMPLO: {{"regioes": [{{"rotulo": "MCU", "cor": "green", "caixa": [300, 400, 550, 650]}}]}}
    """
    buf = io.BytesIO()
    imagem_pil.save(buf, format="JPEG", quality=90)
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt_mapeamento, types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")],
            config=types.GenerateContentConfig(temperature=0.1)
        )
        texto_resp = response.text.strip().replace("```json", "").replace("```", "").strip()
        dados = json.loads(texto_resp)
        
        imagem_mapeada = imagem_pil.copy()
        draw = ImageDraw.Draw(imagem_mapeada)
        try:
            font = ImageFont.truetype("arial.ttf", size=max(14, int(altura * 0.02)))
        except Exception:
            font = ImageFont.load_default()

        mapa_cores = {
            "green": (0, 255, 136), "blue": (0, 150, 255), "yellow": (255, 215, 0),
            "red": (255, 50, 50), "magenta": (255, 0, 255), "cyan": (0, 255, 255)
        }

        for item in dados.get("regioes", []):
            rotulo, nome_cor = item.get("rotulo", "Setor"), item.get("cor", "cyan").lower()
            cor_rgb = mapa_cores.get(nome_cor, (0, 255, 136))
            ymin, xmin, ymax, xmax = item.get("caixa", [0, 0, 0, 0])
            left, top, right, bottom = (xmin / 1000.0) * largura, (ymin / 1000.0) * altura, (xmax / 1000.0) * largura, (ymax / 1000.0) * altura
            
            for i in range(max(3, int(altura * 0.005))):
                draw.rectangle([left-i, top-i, right+i, bottom+i], outline=cor_rgb)
            bbox_text = draw.textbbox((left, max(0, top - 22)), f" {rotulo} ", font=font)
            draw.rectangle(bbox_text, fill=cor_rgb)
            draw.text((left, max(0, top - 22)), f" {rotulo} ", fill=(0, 0, 0), font=font)
        return imagem_mapeada, True
    except Exception as e:
        print(f"Erro no mapeamento colorido: {e}")
        return imagem_pil, False

# ---------------------------------------------------------
# FUNÇÃO 2: MAPEAMENTO NUMERADO COM DESCRIÇÕES
# ---------------------------------------------------------
def processar_e_desenhar_mapa_numerado(imagem_pil, identificacao_uce):
    largura, altura = imagem_pil.size
    prompt_mapeamento = f"""
    Analise esta foto detalhada da placa da UCE ({identificacao_uce}). Identifique TODOS os componentes principais e setores visíveis.
    NUMERE cada um sequencialmente de 1 até N.
    Retorne EXCLUSIVAMENTE um objeto JSON válido contendo a chave "componentes", onde cada item possui:
    - "numero": Inteiro sequencial (1, 2, 3...)
    - "nome": Nome técnico exato du componente (Ex: "MCU MPC5xx", "EEPROM SOIC8", "TRANSFORMADOR DC-DC")
    - "descricao": Descrição técnica da função e cuidados du reparo.
    - "caixa": Coordenadas normalizadas [ymin, xmin, ymax, xmax].
    EXEMPLO: {{"componentes": [{{"numero": 1, "nome": "MCU", "descricao": "Processador central.", "caixa": [300, 300, 600, 550]}}]}}
    """
    buf = io.BytesIO()
    imagem_pil.save(buf, format="JPEG", quality=90)
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=[prompt_mapeamento, types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")],
            config=types.GenerateContentConfig(temperature=0.1)
        )
        texto_resp = response.text.strip().replace("```json", "").replace("```", "").strip()
        dados = json.loads(texto_resp)
        
        imagem_mapeada = imagem_pil.copy()
        draw = ImageDraw.Draw(imagem_mapeada)
        try:
            font = ImageFont.truetype("arial.ttf", size=max(16, int(altura * 0.03)))
        except Exception:
            font = ImageFont.load_default()

        lista_mapeada = []
        for item in dados.get("componentes", []):
            num, nome, desc = item.get("numero", 1), item.get("nome", "Componente"), item.get("descricao", "Sem descrição.")
            ymin, xmin, ymax, xmax = item.get("caixa", [0, 0, 0, 0])
            left, top, right, bottom = (xmin / 1000.0) * largura, (ymin / 1000.0) * altura, (xmax / 1000.0) * largura, (ymax / 1000.0) * altura
            
            for i in range(max(3, int(altura * 0.004))):
                draw.rectangle([left-i, top-i, right+i, bottom+i], outline=(0, 255, 136))
                
            raio = max(12, int(altura * 0.02))
            centro_x, centro_y = left + raio, top + raio
            draw.ellipse([centro_x - raio, centro_y - raio, centro_x + raio, centro_y + raio], fill=(255, 215, 0), outline=(0, 0, 0))
            draw.text((centro_x - 6, centro_y - 10), str(num), fill=(0, 0, 0), font=font)
            
            lista_mapeada.append({"numero": num, "nome": nome, "descricao": desc})
        return imagem_mapeada, lista_mapeada, True
    except Exception as e:
        print(f"Erro no mapeamento numerado: {e}")
        return imagem_pil, [], False

# ---------------------------------------------------------
# 11. Interface Principal e Abas
# ---------------------------------------------------------
st.title("🔬 Sistema de Diagnóstico Avançado 🔬")
st.write("Análise de sinais de osciloscópio, leituras de parâmetros de scanner, códigos de falha (DTC), textos, áudios e vídeos técnicos.")

is_adm = str(st.session_state.get('user_email', '')).strip().lower() == EMAIL_ADM.lower()

if is_adm:
    aba_empresa, aba1, aba_uces, aba_scanners, aba_programadores, aba_programacao, aba2, aba3, aba4, aba5, aba6 = st.tabs([
        "🏢 Minha Empresa",
        "🔬 Diagnóstico", 
        "🔌 Suporte U.C.Es",
        "📡 Suporte Scanners",
        "💻 Suporte Programadores",
        "⚙️ Suporte Programação",
        "📜 Histórico", 
        "🎓 Cursos & Redes Sociais", 
        "💬 Connect WhatsApp", 
        "💳 Assinatura",
        "💎 Gestão de Clientes 💎"
    ])
else:
    aba_empresa, aba1, aba_uces, aba_scanners, aba_programadores, aba_programacao, aba2, aba3, aba4, aba5 = st.tabs([
        "🏢 Minha Empresa",
        "🔬 Diagnóstico", 
        "🔌 Suporte U.C.Es",
        "📡 Suporte Scanners",
        "💻 Suporte Programadores",
        "⚙️ Suporte Programação",
        "📜 Histórico", 
        "🎓 Cursos & Redes Sociais", 
        "💬 Connect WhatsApp", 
        "💳 Assinatura"
    ])

# =========================================================
# ABA 🏢 MINHA EMPRESA (SELO DE QUALIDADE EM DIAGNÓSTICO)
# =========================================================
with aba_empresa:
    st.markdown("""
    <style>
        .selo-container {
            background: linear-gradient(135deg, rgba(3, 20, 12, 0.95) 0%, rgba(5, 46, 22, 0.9) 100%);
            border: 2px solid #00FF88;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 0 35px rgba(0, 255, 136, 0.35);
            margin-bottom: 25px;
        }
        .selo-header {
            text-align: center;
            border-bottom: 2px dashed #00FF88;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .selo-titulo {
            color: #FFD700 !important;
            font-size: 1.8rem;
            font-weight: 900;
            text-shadow: 0 0 12px rgba(255, 215, 0, 0.6);
            margin: 0;
            text-transform: uppercase;
        }
        .selo-subtitulo {
            color: #00FF88 !important;
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 5px;
        }
        .info-label {
            color: #00E5FF !important;
            font-weight: 700;
            font-size: 0.95rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .info-value {
            color: #FFFFFF !important;
            font-weight: 800;
            font-size: 1.15rem;
            background: rgba(0, 229, 255, 0.08);
            border-left: 4px solid #00E5FF;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 15px;
        }
        .metric-card-neon {
            background: rgba(5, 46, 22, 0.7);
            border: 1px solid #FFD700;
            border-radius: 12px;
            padding: 15px;
            text-align: center;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.2);
        }
    </style>
    """, unsafe_allow_html=True)

    email_usuario = st.session_state.get('user_email', '')
    nome_usuario_logado = st.session_state.get('user_nome', 'Agente de Diagnóstico')
    tipo_acesso = st.session_state.get('user_tipo_acesso', 'teste')
    fichas_restantes = st.session_state.get('user_fichas', 0)
    total_diag_feitos = contar_diagnosticos(email_usuario)
    
    dt_cad, dt_teste, dt_ass = obter_detalhes_usuario_banco(email_usuario)
    
    if email_usuario == EMAIL_ADM or fichas_restantes >= 999 or tipo_acesso == "assinante":
        nome_plano = "👑 Plano Anual Ilimitado (Nível Especialista)"
        data_expira = dt_ass if dt_ass != "N/A" else "365 Dias"
    else:
        nome_plano = "🚀 Período de Teste Inicial (7 Dias)"
        data_expira = dt_teste if dt_teste != "N/A" else "7 Dias"

    st.markdown(f"""
    <div class="selo-container">
        <div class="selo-header">
            <div style="font-size: 40px; margin-bottom: 5px;">🛡️</div>
            <h2 class="selo-titulo">Selo de Qualidade em Diagnóstico Automotivo</h2>
            <p class="selo-subtitulo">Certificado Oficial AutoLab LOA – Excelência em Engenharia de Diagnósticos</p>
        </div>
    """, unsafe_allow_html=True)

    col_emp1, col_emp2 = st.columns(2, gap="large")

    with col_emp1:
        st.markdown(f"""
        <div class="info-label">🏢 Nome da Empresa / Oficina</div>
        <div class="info-value">{st.session_state.get('oficina_nome', 'AUTOLAB DIAGNÓSTICOS')}</div>

        <div class="info-label">📄 CPF / CNPJ</div>
        <div class="info-value">{st.session_state.get('oficina_cnpj', '00.000.000/0001-00')}</div>

        <div class="info-label">📞 Celular / WhatsApp</div>
        <div class="info-value">{st.session_state.get('oficina_tel', '(00) 00000-0000')}</div>

        <div class="info-label">🕵️‍♂️ Agente de Diagnóstico (Usuário)</div>
        <div class="info-value">{nome_usuario_logado}</div>
        """, unsafe_allow_html=True)

    with col_emp2:
        st.markdown(f"""
        <div class="info-label">💎 Plano Escolhido</div>
        <div class="info-value">{nome_plano}</div>

        <div class="info-label">📥 Contratado em</div>
        <div class="info-value">{dt_cad}</div>

        <div class="info-label">⏳ Expira em</div>
        <div class="info-value">{data_expira}</div>

        <div class="info-label">🎟️ Fichas / Créditos Disponíveis</div>
        <div class="info-value">{fichas_restantes if fichas_restantes < 999 else 'Ilimitado'} Fichas</div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    
    col_painel1, col_painel2, col_painel3 = st.columns(3)
    with col_painel1:
        st.markdown(f"""
        <div class="metric-card-neon">
            <div style="color: #00E5FF; font-size: 14px; font-weight: 700;">📈 TOTAL DE DIAGNÓSTICOS</div>
            <div style="color: #FFD700; font-size: 2rem; font-weight: 900; margin-top: 5px;">{total_diag_feitos}</div>
        </div>
        """, unsafe_allow_html=True)
    with col_painel2:
        st.markdown(f"""
        <div class="metric-card-neon">
            <div style="color: #00E5FF; font-size: 14px; font-weight: 700;">⚡ STATUS DA CONTA</div>
            <div style="color: #00FF88; font-size: 1.5rem; font-weight: 900; margin-top: 8px;">ATIVO</div>
        </div>
        """, unsafe_allow_html=True)
    with col_painel3:
        st.markdown(f"""
        <div class="metric-card-neon">
            <div style="color: #00E5FF; font-size: 14px; font-weight: 700;">🌟 PADRÃO TÉCNICO</div>
            <div style="color: #FFD700; font-size: 1.5rem; font-weight: 900; margin-top: 8px;">Especialista</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# ABA 1: DIAGNÓSTICO AVANÇADO
# =========================================================
with aba1:
    st.subheader("🤖 Diagnóstico Automotivo Inteligente 🤖")

    tem_audio_wsp = 'audio_wsp_bytes' in st.session_state and st.session_state['audio_wsp_bytes']
    tem_video_wsp = 'video_wsp_bytes' in st.session_state and st.session_state['video_wsp_bytes']
    if tem_audio_wsp or tem_video_wsp or st.session_state.get('sintomas_wsp'):
        midias_status = []
        if st.session_state.get('sintomas_wsp'): midias_status.append("Texto")
        if tem_audio_wsp: midias_status.append("Áudio")
        if tem_video_wsp: midias_status.append("Vídeo")
        st.info(f"🟢 **Mídias importadas du WhatsApp prontas para envio:** {', '.join(midias_status)}")

    col_veiculo, col_dtc = st.columns(2)
    with col_veiculo:
        motor = st.text_input(
            "🚗 Veículo / Motor / Sistema ECU",
            placeholder="Ex: Fiat Toro 2.0 Diesel Bosch EDC17C69",
            help="Informe a montadora, modelo, motorização ou modelo du módulo ECU."
        )

    with col_dtc:
        dtc = st.text_input(
            "🔍 Códigos de Falha (DTC)",
            placeholder="Ex: P0300, P0100, P0299",
            help="Informe os códigos de falhas registrados du scanner."
        )

    val_sintomas_wsp = st.session_state.get('sintomas_wsp', '')
    valores = st.text_area(
        "📝 Relato dos Sintomas / Informações Detalhadas / Medições elétricos Aplicados",
        value=val_sintomas_wsp,
        placeholder="Descreva o comportamento do veículo, falhas intermitentes, pressões de combustível, tensões medidas, etc.",
        height=100
    )

    st.markdown("---")

    st.markdown("""
    <style>
        @keyframes pulse-yellow-btn {
            0% {
                background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%);
                box-shadow: 0 0 10px rgba(255, 215, 0, 0.6);
            }
            50% {
                background: linear-gradient(135deg, #FFEE55 0%, #FFB300 100%);
                box-shadow: 0 0 25px rgba(255, 215, 0, 1);
            }
            100% {
                background: linear-gradient(135deg, #FFD700 0%, #FFC107 100%);
                box-shadow: 0 0 10px rgba(255, 215, 0, 0.6);
            }
        }

        .btn-kts-container .stButton>button {
            animation: pulse-yellow-btn 1.8s infinite ease-in-out !important;
            color: #03140C !important;
            font-weight: 900 !important;
            font-size: 1rem !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            border: 2px solid #00FF88 !important;
            border-radius: 12px !important;
            padding: 0.8rem 1.5rem !important;
            width: 100% !important;
            transition: transform 0.2s ease !important;
        }

        .btn-kts-container .stButton>button:hover {
            transform: translateY(-2px) scale(1.01) !important;
            color: #000000 !important;
            border-color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if 'abrir_parametros_kts' not in st.session_state:
        st.session_state['abrir_parametros_kts'] = False

    st.markdown('<div class="btn-kts-container">', unsafe_allow_html=True)
    if st.button("💻 PARÂMETROS DE FUNCIONAMENTO - AQUI VOCÊ AUMENTA A PRECISÃO DU DIAGNÓSTICO 💻"):
        st.session_state['abrir_parametros_kts'] = not st.session_state['abrir_parametros_kts']
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("💻 DESCREVA OS PARAMETROS EM TEMPO REAL 💻", expanded=st.session_state['abrir_parametros_kts']):
        st.caption("Insira as leituras obtidas du scanner para que a IA analise du desvio técnico de funcionamento em tempo real.")
        
        tab_kts_inj, tab_kts_ar, tab_kts_temp, tab_kts_ele, tab_kts_emis = st.tabs([
            "⛽ Injeção & Combustível", 
            "💨 Admissão & Turbo", 
            "🌡️ Temp. & Ignição", 
            "⚡ Elétrica & Módulo", 
            "🍃 Sonda & Pós-Tratamento"
        ])

        with tab_kts_inj:
            st.markdown("**Valores du Sistema de Combustível (Otto / GDI / Diesel Common Rail)**")
            k1, k2, k3, k4 = st.columns(4)
            with k1:
                p_ti = st.text_input("TI | Tempo Injeção (ms)", placeholder="Ex: 2.8 ms (PID 01)", key="p_ti")
                p_stft1 = st.text_input("STFT1 | Adap. Curto B1 (%)", placeholder="Ex: +2.5 % (PID 06)", key="p_stft1")
            with k2:
                p_fLow = st.text_input("FLP | Pressão Comb. Baixa (bar)", placeholder="Ex: 4.2 bar (PID 0A)", key="p_fLow")
                p_ltft1 = st.text_input("LTFT1 | Adap. Longo B1 (%)", placeholder="Ex: -5.0 % (PID 07)", key="p_ltft1")
            with k3:
                p_fRail = st.text_input("FPR | Pressão Rail/Alta (bar/MPa)", placeholder="Ex: 1350 bar (PID 23)", key="p_fRail")
                p_flex = st.text_input("ALC | Teor de Etanol Flex (%)", placeholder="Ex: 100 % (PID 52)", key="p_flex")
            with k4:
                p_fuel_sys = st.text_input("SYS | Status Malha (Open/Closed)", placeholder="Ex: Closed Loop (PID 03)", key="p_fuel_sys")
                p_fuel_rate = st.text_input("FR | Consumo Instantâneo (L/h)", placeholder="Ex: 0.9 L/h (PID 5E)", key="p_fuel_rate")

        with tab_kts_ar:
            st.markdown("**Valores de Admissão, Borboleta e Sobrealimentação**")
            k5, k6, k7, k8 = st.columns(4)
            with k5:
                p_map = st.text_input("MAP | Pressão Coletor (mbar/kPa)", placeholder="Ex: 350 mbar (PID 0B)", key="p_map")
                p_tps = st.text_input("TPS | Posição Borboleta (%)", placeholder="Ex: 11.5 % (PID 11)", key="p_tps")
            with k6:
                p_maf = st.text_input("MAF | Massa de Ar (g/s)", placeholder="Ex: 2.4 g/s (PID 10)", key="p_maf")
                p_app = st.text_input("APP | Pos. Pedal Acelerador (%)", placeholder="Ex: 0 % (PID 47)", key="p_app")
            with k7:
                p_boost = st.text_input("BOOST | Pressão Turbo (bar)", placeholder="Ex: 1.2 bar (PID 69/70)", key="p_boost")
                p_load = st.text_input("LOAD | Carga du Motor (%)", placeholder="Ex: 22 % (PID 04)", key="p_load")
            with k8:
                p_baro = st.text_input("BARO | Pressão Barométrica (kPa)", placeholder="Ex: 98 kPa (PID 33)", key="p_baro")

        with tab_kts_temp:
            st.markdown("**Valores de Temperatura de Trabalho, Rotação e Ignição**")
            k9, k10, k11, k12 = st.columns(4)
            with k9:
                p_rpm = st.text_input("RPM | Rotação Motor (rpm)", placeholder="Ex: 820 rpm (PID 0C)", key="p_rpm")
                p_ect = st.text_input("ECT | Temp. Arrefecimento (°C)", placeholder="Ex: 90 °C (PID 05)", key="p_ect")
            with k10:
                p_ign = st.text_input("IGN | Avanço du Ponto de Ignição (°)", placeholder="Ex: 8.5 ° (PID 0E)", key="p_ign")
                p_iat = st.text_input("IAT | Temp. Ar Admissão (°C)", placeholder="Ex: 32 °C (PID 0F)", key="p_iat")
            with k11:
                p_vss = st.text_input("VSS | Velocidade Veículo (km/h)", placeholder="Ex: 0 km/h (PID 0D)", key="p_vss")
                p_oil = st.text_input("EOT | Temp. Óleo du Motor (°C)", placeholder="Ex: 95 °C (PID 5C)", key="p_oil")
            with k12:
                p_cat_temp = st.text_input("CAT | Temp. Catalisador (°C)", placeholder="Ex: 450 °C (PID 3C)", key="p_cat_temp")

        with tab_kts_ele:
            st.markdown("**Tensões de Alimentação, Bateria e Status de Rede**")
            k13, k14, k15 = st.columns(3)
            with k13:
                p_vbat = st.text_input("VBAT | Tensão Módulo/Bateria (V)", placeholder="Ex: 13.9 V (PID 42)", key="p_vbat")
            with k14:
                p_run_time = st.text_input("RUN | Tempo Funcionamento (s)", placeholder="Ex: 450 s (PID 1F)", key="p_run_time")
            with k15:
                p_mil_dist = st.text_input("MIL | Distância c/ Luz Acesa (km)", placeholder="Ex: 120 km (PID 31)", key="p_mil_dist")

        with tab_kts_emis:
            st.markdown("**Análise de Sonda Lambda, EGR, DPF e Arla 32 (SCR)**")
            k16, k17, k18, k19 = st.columns(4)
            with k16:
                p_lambda1 = st.text_input("LAMBDA 1 | Razão / Tensão (λ / V)", placeholder="Ex: 1.00 / 450mV (PID 24)", key="p_lambda1")
                p_egr = st.text_input("EGR | Pos. Comandada EGR (%)", placeholder="Ex: 15 % (PID 2C)", key="p_egr")
            with k17:
                p_lambda2 = st.text_input("LAMBDA 2 | Sonda Pós-Cat (mV)", placeholder="Ex: 720 mV (PID 15)", key="p_lambda2")
                p_dpf_press = st.text_input("DPF | Pressão Diferencial (mbar)", placeholder="Ex: 12 mbar (PID 78)", key="p_dpf_press")
            with k18:
                p_evap = st.text_input("EVAP | Purga Cânister (%)", placeholder="Ex: 0 % (PID 2E)", key="p_evap")
                p_dpf_temp = st.text_input("DPF_TEMP | Temp. Filtro DPF (°C)", placeholder="Ex: 280 °C (PID 7A)", key="p_dpf_temp")
            with k19:
                p_nox = st.text_input("NOX | Concentração NOx (ppm)", placeholder="Ex: 45 ppm (PID 83)", key="p_nox")
                p_arla = st.text_input("DEF | Nível Arla 32 / SCR (%)", placeholder="Ex: 80 % (PID 85)", key="p_arla")

    st.markdown("---")

    col_os, col_audio, col_video = st.columns(3)
    with col_os:
        st.markdown("### 📄 Ordem de Serviço (O.S.)")
        arquivo_os = st.file_uploader("Anexe a O.S. (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"], key="uploader_os")

    with col_audio:
        st.markdown("### 🎙️ Gravar Áudio du Sintoma")
        audio_sintomas = st.audio_input("Grave seu Relato Aqui", key="mic_audio_sintoma")

    with col_video:
        st.markdown("### 🎥 Vídeo du Diagnóstico")
        video_sintomas = st.file_uploader(
            "Vídeo do Relato (Máx: 1 min)", 
            type=["mp4", "mov", "avi", "mkv"], 
            key="uploader_video_diag",
            help="Anexe um vídeo curto gravado du problema, fumaça, barulho de motor ou falha no painel."
        )

    st.markdown("---")
    st.markdown("### 📸 Imagens Técnicas a serem analisadas 📸")

    imagens_anexadas = []
    col_img1, col_img2, col_img3, col_img4 = st.columns(4)

    with col_img1:
        img1 = st.file_uploader("Fotos du Scanner / DTCs", type=["png", "jpg", "jpeg"], key="img_scanner")
        if img1: imagens_anexadas.append(("Scanner", Image.open(img1)))

    with col_img2:
        img2 = st.file_uploader("Fotos da Tela du Osciloscópio", type=["png", "jpg", "jpeg"], key="img_osc")
        if img2: imagens_anexadas.append(("Osciloscopio", Image.open(img2)))

    with col_img3:
        img3 = st.file_uploader("Leitura du Multímetro", type=["png", "jpg", "jpeg"], key="img_mult")
        if img3: imagens_anexadas.append(("Multimetro", Image.open(img3)))

    with col_img4:
        img4 = st.file_uploader("Fotos da Placa UCEs / Componentes UCEs", type=["png", "jpg", "jpeg"], key="img_placa")
        if img4: imagens_anexadas.append(("Placa_ECU", Image.open(img4)))

    st.write("") 

    col_img5, col_img6, col_img7, col_img8 = st.columns(4)

    with col_img5:
        img5 = st.file_uploader("Esquema Elétrico / Pinagem UCE", type=["png", "jpg", "jpeg"], key="img_esquema")
        if img5: imagens_anexadas.append(("Esquema_Eletrico", Image.open(img5)))

    with col_img6:
        img6 = st.file_uploader("Estado Físico de Peças / Chicotes", type=["png", "jpg", "jpeg"], key="img_pecas")
        if img6: imagens_anexadas.append(("Pecas_Chicote", Image.open(img6)))

    with col_img7:
        img7 = st.file_uploader("Fotos de Sensores / Atuadores", type=["png", "jpg", "jpeg"], key="img_sensores")
        if img7: imagens_anexadas.append(("Sensores_Atuadores", Image.open(img7)))

    with col_img8:
        img8 = st.file_uploader("Luzes do Painel / Quadrante", type=["png", "jpg", "jpeg"], key="img_painel")
        if img8: imagens_anexadas.append(("Painel_Luzes", Image.open(img8)))

    st.markdown("---")

    if st.button("🚀 Executar Diagnóstico Avançado 🚀", width="stretch"):
        status_atual_check = verificar_status_usuario(st.session_state['user_email'])
        if st.session_state['user_email'] != EMAIL_ADM and (status_atual_check["tipo"] == "expirado" or (status_atual_check["tipo"] == "teste" and status_atual_check["fichas"] <= 0)):
            st.error("⚠️ Seu período de teste de 7 dias ou suas fichas esgotaram! Assine um dos planos na aba 💳 Assinatura para continuar.")
        else:
            parametros_kts = []
            if p_ti: parametros_kts.append(f"• Tempo de Injeção (TI): {p_ti}")
            if p_stft1: parametros_kts.append(f"• Adap. Combustível Curto Prazo (STFT1): {p_stft1}")
            if p_ltft1: parametros_kts.append(f"• Adap. Combustível Longo Prazo (LTFT1): {p_ltft1}")
            if p_fLow: parametros_kts.append(f"• Pressão de Combustível Baixa (FLP): {p_fLow}")
            if p_fRail: parametros_kts.append(f"• Pressão da Rail / Alta Pressão (FPR): {p_fRail}")
            if p_flex: parametros_kts.append(f"• Teor de Etanol Reconhecido (ALC): {p_flex}")
            if p_fuel_sys: parametros_kts.append(f"• Status Malha de Injeção: {p_fuel_sys}")
            if p_fuel_rate: parametros_kts.append(f"• Consumo Instantâneo: {p_fuel_rate}")

            if p_map: parametros_kts.append(f"• Pressão Absoluta Coletor (MAP): {p_map}")
            if p_maf: parametros_kts.append(f"• Fluxo de Massa de Ar (MAF): {p_maf}")
            if p_tps: parametros_kts.append(f"• Pos. Borboleta Aceleração (TPS): {p_tps}")
            if p_app: parametros_kts.append(f"• Pos. Pedal Acelerador (APP): {p_app}")
            if p_boost: parametros_kts.append(f"• Pressão de Sobrealimentação/Turbo (BOOST): {p_boost}")
            if p_load: parametros_kts.append(f"• Carga Calculada du Motor (LOAD): {p_load}")
            if p_baro: parametros_kts.append(f"• Pressão Barométrica (BARO): {p_baro}")

            if p_rpm: parametros_kts.append(f"• Rotação du Motor (RPM): {p_rpm}")
            if p_ect: parametros_kts.append(f"• Temp. Arrefecimento/Líquido (ECT): {p_ect}")
            if p_iat: parametros_kts.append(f"• Temp. Ar de Admissão (IAT): {p_iat}")
            if p_ign: parametros_kts.append(f"• Avanço du Ponto de Ignição (IGN): {p_ign}")
            if p_vss: parametros_kts.append(f"• Velocidade du Veículo (VSS): {p_vss}")
            if p_oil: parametros_kts.append(f"• Temp. Óleo du Motor (EOT): {p_oil}")
            if p_cat_temp: parametros_kts.append(f"• Temp. Catalisador (CAT): {p_cat_temp}")

            if p_vbat: parametros_kts.append(f"• Tensão da ECU/Bateria (VBAT): {p_vbat}")
            if p_run_time: parametros_kts.append(f"• Tempo desde a Partida: {p_run_time}")
            if p_mil_dist: parametros_kts.append(f"• Distância c/ Luz MIL Acesa: {p_mil_dist}")

            if p_lambda1: parametros_kts.append(f"• Sonda Lambda Pré / Razão A/F (O2S11): {p_lambda1}")
            if p_lambda2: parametros_kts.append(f"• Sonda Lambda Pós Catalisador (O2S12): {p_lambda2}")
            if p_egr: parametros_kts.append(f"• Comando Valvula EGR: {p_egr}")
            if p_evap: parametros_kts.append(f"• Purga du Cânister (EVAP): {p_evap}")
            if p_dpf_press: parametros_kts.append(f"• Pressão Diferencial DPF: {p_dpf_press}")
            if p_dpf_temp: parametros_kts.append(f"• Temp. Filtro DPF: {p_dpf_temp}")
            if p_nox: parametros_kts.append(f"• Concentração de NOx: {p_nox}")
            if p_arla: parametros_kts.append(f"• Nível/Dosagem Arla 32 (DEF): {p_arla}")

            texto_kts_formatado = "\n".join(parametros_kts) if parametros_kts else "Nenhum parâmetro real específico du scanner informado."
            tem_video_direto = video_sintomas is not None

            if motor and (imagens_anexadas or audio_sintomas or video_sintomas or valores or arquivo_os or tem_audio_wsp or tem_video_wsp or parametros_kts):
                
                # BARRA DE CARREGAMENTO (0% A 100%)
                barra_progresso = st.progress(0)
                status_texto = st.empty()
                
                status_texto.markdown("🔍 **[0%]** — Lendo parâmetros KTS, O.S. e mídias anexadas...")
                barra_progresso.progress(10)
                time.sleep(0.3)

                status_texto.markdown("🧠 **[35%]** — Cruzando dados com a base técnica AutoLab AI...")
                barra_progresso.progress(35)
                time.sleep(0.3)

                status_texto.markdown("⚙️ **[70%]** — Processando engenharia reversa e oscilogramas...")
                barra_progresso.progress(70)
                time.sleep(0.3)

                instrucao_sistema = "Você é du AUTOLAB DIAG AI, especialista sênior em diagnóstico automotivo, análise de dados de scanner em tempo real (padrão Bosch KTS/SAE J1979), osciloscópio e engenharia reversa de ECUs."
                
                prompt_caso = f"""DADOS DO CASO:
- Motor/Veículo: {motor}
- Códigos DTC: {dtc if dtc else 'Consulte imagens/O.S.'}
- Sintomas Digitados/Importados: {valores if valores else 'Consulte O.S., áudios ou vídeos anexados'}

📊 VALORES REAIS DU SCANNER (ESTRUTURA BOSCH KTS / SAE J1979):
{texto_kts_formatado}

INSTRUÇÕES DE ANÁLISE:
1. Analise detalhadamente cada parâmetro real du scanner fornecido.
2. Caso exista O.S., extraia histórico e peças já substituídas.
3. Analise áudio ou vídeo enviado.
4. Cruze todas essas informações com capturas fornecidas.
5. Forneça relatório claro e direto."""

                conteudo_envio = [prompt_caso]
                
                if arquivo_os:
                    try:
                        arquivo_os.seek(0)
                        bytes_os = arquivo_os.read()
                        mime_os = "application/pdf" if arquivo_os.type == "application/pdf" else "image/jpeg"
                        conteudo_envio.append(types.Part.from_bytes(data=bytes_os, mime_type=mime_os))
                    except Exception: pass

                for label, img_pil in imagens_anexadas:
                    try:
                        img_copy = img_pil.copy()
                        img_copy.thumbnail((1280, 1280))
                        buf = io.BytesIO()
                        img_copy.save(buf, format="JPEG", quality=85)
                        conteudo_envio.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg"))
                    except Exception: pass

                if audio_sintomas:
                    try:
                        audio_sintomas.seek(0)
                        conteudo_envio.append(types.Part.from_bytes(data=audio_sintomas.read(), mime_type="audio/wav"))
                    except Exception: pass
                elif tem_audio_wsp:
                    conteudo_envio.append(types.Part.from_bytes(data=st.session_state['audio_wsp_bytes'], mime_type=st.session_state.get('audio_wsp_mime', 'audio/wav')))

                if tem_video_direto:
                    try:
                        video_sintomas.seek(0)
                        conteudo_envio.append(types.Part.from_bytes(data=video_sintomas.read(), mime_type=video_sintomas.type if video_sintomas.type else "video/mp4"))
                    except Exception: pass
                elif tem_video_wsp:
                    conteudo_envio.append(types.Part.from_bytes(data=st.session_state['video_wsp_bytes'], mime_type=st.session_state.get('video_wsp_mime', 'video/mp4')))

                relatorio_resultado = ""
                config_requisicao = types.GenerateContentConfig(system_instruction=instrucao_sistema, temperature=0.2)

                try:
                    modelos_disponiveis = ['gemini-3-flash-preview', 'gemini-3.5-flash', 'gemini-2.5-pro']
                    for mod in modelos_disponiveis:
                        try:
                            response = client.models.generate_content(model=mod, contents=conteudo_envio, config=config_requisicao)
                            if response and hasattr(response, 'text') and response.text:
                                relatorio_resultado = response.text
                                break
                        except Exception: pass

                    # 100% CONCLUÍDO
                    barra_progresso.progress(100)
                    status_texto.markdown("✅ **[100%]** — Laudo Técnico Concluído com Sucesso!")
                    time.sleep(0.5)
                    
                    barra_progresso.empty()
                    status_texto.empty()

                    if relatorio_resultado.strip():
                        st.session_state['ultimo_relatorio'] = relatorio_resultado
                        st.session_state['ultimo_motor'] = motor
                        st.session_state['ultimo_dtc'] = dtc
                        sintomas_salvamento = valores if valores else "Analisado via Mídia / O.S."
                        if parametros_kts: sintomas_salvamento += f" | {len(parametros_kts)} Val. Reais KTS"
                        st.session_state['ultimo_sintomas'] = sintomas_salvamento
                        
                        fichas_atuais = st.session_state.get('user_fichas', 7)
                        email_atual = st.session_state.get('user_email', '')
                        
                        if email_atual != EMAIL_ADM and fichas_atuais < 999:
                            fichas_atuais -= 1
                            st.session_state['user_fichas'] = fichas_atuais
                            atualizar_fichas_banco(email_atual, fichas_atuais)
                            if fichas_atuais == 0:
                                enviar_email_oferta_assinatura(st.session_state.get('user_nome', 'Técnico'), email_atual)

                        salvar_diagnostico(email_atual, motor, dtc, st.session_state['ultimo_sintomas'], relatorio_resultado)
                        st.success("Diagnóstico Completo Gerado e Salvo du Histórico!")
                    else:
                        st.error("⚠️ Nenhuma resposta gerada.")
                except Exception as e:
                    barra_progresso.empty()
                    status_texto.empty()
                    st.error(f"Erro na requisição: {e}")
            else:
                st.warning("Atenção: Preencha du campo Veículo/Motor e adicione informações de análise.")

    if 'ultimo_relatorio' in st.session_state and st.session_state['ultimo_relatorio']:
        st.markdown("---")
        st.subheader("📋 Relatório Atual Gerado")
        st.markdown(st.session_state['ultimo_relatorio'])
        
        pdf_diag_direto = gerar_pdf_relatorio(
            st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
            motor, dtc, st.session_state.get('ultimo_sintomas', ''),
            st.session_state['ultimo_relatorio'],
            titulo_pdf="LAUDO TÉCNICO DE DIAGNÓSTICO AVANÇADO"
        )
        st.download_button(
            label="📥 BAIXAR ESTE RELATÓRIO EM PDF",
            data=pdf_diag_direto,
            file_name=f"Laudo_Autolab_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width="stretch"
        )

# =========================================================
# ABA 2: SUPORTE U.C.Es (COM BARRA 0-100% E PDF)
# =========================================================
with aba_uces:
    st.subheader("🔌 Suporte Especializado em Módulos Eletrônicos (U.C.Es)")
    st.write("Análise de hardware, datasheets, componentes, boot pinout, oscilogramas, curva característica e dupla opção de mapeamento visual.")
    st.markdown("---")

    modulo_tipo_sel = st.selectbox(
        "📌 Selecione a Categoria du Módulo / U.C.E:",
        [
            "🚗 UCE Motor / Injeção Eletrônica (ECU/PCM)",
            "🛑 ABS / Controle de Estabilidade (ESP)",
            "🎈 Airbag / Sistema SRS",
            "📟 Painel de Instrumentos (IC / Kombi)",
            "⚡ BCM / Carroceria / Conforto / Gateway",
            "⚙️ Câmbio Automático / TCU / TCM",
            "🔑 Imobilizador / Chaves / PATS",
            "🅿️ EPB (Freio Elétrico) & Direção Elétrica (EPS)"
        ],
        key="sel_cat_modulo_uce"
    )

    col_u_id, col_u_duv = st.columns([1, 1])
    with col_u_id:
        veiculo_uce_geral = st.text_input(
            "🚘 Identificação du Módulo / Veículo / Código da Peça:",
            placeholder="Ex: Bosch ME7.5 / Marelli IAW 4GV / Denso Hilux / ABS Bosch 9.0",
            key="veiculo_uce_geral"
        )
    with col_u_duv:
        duvida_uce_principal = st.text_area(
            "💬 Descreva sua Dúvida Técnica Geral sobre a U.C.E:",
            placeholder="Ex: Carro não grava arquivo, sem comunicação CAN, estouro de capacitor, reset de crash...",
            height=80,
            key="duvida_uce_principal"
        )

    st.markdown("---")
    st.markdown("### 🎙️ / 📸 / 🎥 Mídias de Análise para Diagnóstico de Bancada UCEs")
    
    col_mu1, col_mu2, col_mu3, col_mu4 = st.columns(4)
    with col_mu1:
        audio_uce = st.audio_input("🎙️ Gravar Áudio", key="audio_uce_input")
    with col_mu2:
        foto_uce_1 = st.file_uploader("📸 Foto de Bancada 1", type=["png", "jpg", "jpeg"], key="foto_uce_1_input")
    with col_mu3:
        foto_uce_2 = st.file_uploader("📸 Foto de Bancada 2", type=["png", "jpg", "jpeg"], key="foto_uce_2_input")
    with col_mu4:
        video_uce = st.file_uploader("🎥 Anexar Vídeo", type=["mp4", "mov", "avi", "mkv"], key="video_uce_input")

    st.markdown("---")
    st.markdown("### 🔬 Análise Detalhada de Módulos Eletrônicos Veicular")

    def analisar_ponto_individual(titulo_ponto, prompt_ponto, midia_file=None):
        if veiculo_uce_geral:
            with st.spinner(f"🔬 Analisando {titulo_ponto}..."):
                sys_inst = "Você é du Engenheiro Especialista em Reparo de Módulos UCEs da AutoLab."
                contents = [f"MÓDULO: {veiculo_uce_geral}\nCATEGORIA: {modulo_tipo_sel}\n{prompt_ponto}"]
                
                if midia_file:
                    try:
                        midia_file.seek(0)
                        if getattr(midia_file, 'type', '') == "application/pdf":
                            contents.append(types.Part.from_bytes(data=midia_file.read(), mime_type="application/pdf"))
                        else:
                            img_p = Image.open(midia_file)
                            img_p.thumbnail((1280, 1280))
                            buf_p = io.BytesIO()
                            img_p.save(buf_p, format="JPEG", quality=85)
                            contents.append(types.Part.from_bytes(data=buf_p.getvalue(), mime_type="image/jpeg"))
                    except Exception: pass

                try:
                    res = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=contents,
                        config=types.GenerateContentConfig(system_instruction=sys_inst, temperature=0.2)
                    )
                    return res.text if hasattr(res, 'text') else "Sem resposta."
                except Exception as e:
                    return f"Erro na análise: {e}"
        else:
            st.warning("Preencha a Identificação du Módulo / Veículo no topo antes de consultar.")
            return None

    with st.expander("1. 🖥️ Analisar Placa Completa (Opções de Mapeamento Visual)", expanded=False):
        img_placa_comp = st.file_uploader("Foto da Placa Inteira (PCB Frontal or Traseira)", type=["png", "jpg", "jpeg"], key="u_placa_comp")
        duvida_placa = st.text_area("Dúvida sobre a placa completa:", placeholder="Ex: Qual setor é responsável pelos injetores?", key="d_placa")
        
        tipo_map_escolhido = st.radio(
            "🎨 Escolha du estilo de mapeamento visual desejado:",
            [
                "Mapeamento Colorido por Circuitos",
                "Mapeamento Numerado com Descrição Individual",
                "Gerar Ambos os Mapeamentos"
            ],
            key="radio_tipo_map"
        )
        
        col_btn_m1, col_btn_m2 = st.columns([1, 1])
        
        with col_btn_m1:
            if st.button("🖼️ Processar Mapeamento Visual Escolhido", key="btn_gerar_mapa_escolhido", width="stretch"):
                if img_placa_comp and veiculo_uce_geral:
                    with st.spinner("🗺️ IA PROCESSANDO A PLACA CONFORME A SUA ESCOLHA..."):
                        img_original = Image.open(img_placa_comp)
                        st.session_state.pop('imagem_mapeada_num', None)
                        st.session_state.pop('imagem_mapeada_cor', None)
                        
                        if tipo_map_escolhido in ["Mapeamento Colorido por Circuitos", "Gerar Ambos os Mapeamentos"]:
                            img_c, s_c = processar_e_desenhar_mapa_placa(img_original, veiculo_uce_geral)
                            if s_c: st.session_state['imagem_mapeada_cor'] = img_c
                            
                        if tipo_map_escolhido in ["Mapeamento Numerado com Descrição Individual", "Gerar Ambos os Mapeamentos"]:
                            img_n, lista_n, s_n = processar_e_desenhar_mapa_numerado(img_original, veiculo_uce_geral)
                            if s_n:
                                st.session_state['imagem_mapeada_num'] = img_n
                                st.session_state['lista_componentes_num'] = lista_n
                                
                    st.success("Mapeamento(s) gerado(s) com sucesso!")
                else:
                    st.warning("Preencha a Identificação du Módulo e anexe a foto da placa.")

        with col_btn_m2:
            if st.button("🔍 Analisar Placa (Texto Técnico)", key="btn_ind_placa", width="stretch"):
                ans = analisar_ponto_individual("Placa Completa", f"Análise da Placa: {duvida_placa}", img_placa_comp)
                if ans: st.info(ans)

        if 'imagem_mapeada_cor' in st.session_state:
            st.markdown("#### 🎨 Mapeamento Colorido por Setores de Circuitos")
            st.image(st.session_state['imagem_mapeada_cor'], caption="Mapeamento Colorido - AutoLab LOA", use_container_width=True)
            st.markdown("""
            **Legenda:** 🟢 Processadores | 🔵 Memórias | 🟡 Reguladores/Fonte | 🔴 Drivers de Potência | 🟣 Comunicação CAN/LIN
            """)
            
        if 'imagem_mapeada_num' in st.session_state:
            st.markdown("#### 🔢 Mapeamento Numerado com Descrição Individual")
            st.image(st.session_state['imagem_mapeada_num'], caption="Mapeamento Numerado - AutoLab LOA", use_container_width=True)
            if 'lista_componentes_num' in st.session_state:
                st.markdown("##### 📋 Descrição Individual de Cada Componente Numerado:")
                for comp in st.session_state['lista_componentes_num']:
                    st.markdown(f"**[{comp['numero']}] {comp['nome']}**: {comp['descricao']}")

    with st.expander("2. 🔬 Analisar Componente Eletrônico", expanded=False):
        img_comp = st.file_uploader("Foto aproximada du componente (Driver, SOIC, MOSFET)", type=["png", "jpg", "jpeg"], key="u_comp")
        duvida_comp = st.text_area("Dúvida sobre du componente:", placeholder="Ex: Qual du substituto direto desse driver?", key="d_comp")
        if st.button("🔍 Analisar Componente Agora", key="btn_ind_comp"):
            ans = analisar_ponto_individual("Componente Eletrônico", f"Dúvida Componente: {duvida_comp}", img_comp)
            if ans: st.info(ans)

    with st.expander("3. 🔍 Buscar Datasheet pela Identificação du Componente", expanded=False):
        part_number = st.text_input("Digite a marcação / Silk / Part Number du componente:", placeholder="Ex: BOSCH 30343, V5036, ST L9637D, TLE6244X", key="p_num")
        duvida_pn = st.text_area("O que deseja saber sobre a peça?", key="d_pn")
        if st.button("🔍 Buscar Datasheet Agora", key="btn_ind_pn"):
            ans = analisar_ponto_individual("Busca Datasheet", f"Part Number: {part_number}. Dúvida: {duvida_pn}")
            if ans: st.info(ans)

    with st.expander("4. 📄 Analisar Datasheet (Arquivo PDF / Imagem)", expanded=False):
        file_ds = st.file_uploader("Anexe du arquivo du Datasheet", type=["pdf", "png", "jpg", "jpeg"], key="u_ds")
        duvida_ds = st.text_area("Dúvida técnica sobre a especificação du datasheet:", key="d_ds")
        if st.button("🔍 Analisar Arquivo Datasheet", key="btn_ind_ds"):
            ans = analisar_ponto_individual("Datasheet Anexado", f"Dúvida Datasheet: {duvida_ds}", file_ds)
            if ans: st.info(ans)

    with st.expander("5. 💾 Analisar Memórias SOIC (EEPROM / FLASH)", expanded=False):
        img_soic = st.file_uploader("Foto da Memória SOIC na Placa", type=["png", "jpg", "jpeg"], key="u_soic")
        duvida_soic = st.text_area("Dúvida sobre a leitura/gravação da memória (ex: 24C02, 95320, 29F400):", key="d_soic")
        if st.button("🔍 Analisar Memória SOIC", key="btn_ind_soic"):
            ans = analisar_ponto_individual("Memória SOIC", f"Dúvida SOIC: {duvida_soic}", img_soic)
            if ans: st.info(ans)

    with st.expander("6. 🧠 Analisar Processadores (Microcontrolador MCU)", expanded=False):
        img_mcu = st.file_uploader("Foto du Processador (TriCore, Renesas, PowerPC, MPC)", type=["png", "jpg", "jpeg"], key="u_mcu")
        duvida_mcu = st.text_area("Dúvida sobre du processador / Arquivo de Boot:", key="d_mcu")
        if st.button("🔍 Analisar Processador", key="btn_ind_mcu"):
            ans = analisar_ponto_individual("Processador MCU", f"Dúvida Processador: {duvida_mcu}", img_mcu)
            if ans: st.info(ans)

    with st.expander("7. 🔌 Analisar Boots de Módulos UCEs (Boot / BDM / JTAG / Bench)", expanded=False):
        img_boot = st.file_uploader("Foto dos Pontos de Teste / Boot Pinout", type=["png", "jpg", "jpeg"], key="u_boot")
        duvida_boot = st.text_area("Dúvida sobre ligação em bancada (GTP / KTAG / VVDI / Flex / DFOX):", key="d_boot")
        if st.button("🔍 Analisar Boot/Bench", key="btn_ind_boot"):
            ans = analisar_ponto_individual("Boot/Bench Pinout", f"Dúvida Boot: {duvida_boot}", img_boot)
            if ans: st.info(ans)

    with st.expander("8. 📈 Analisar Imagem de Sinais Gerados por Osciloscópio", expanded=False):
        img_osc_uce = st.file_uploader("Foto du Sinal du Osciloscópio", type=["png", "jpg", "jpeg"], key="u_osc_uce")
        duvida_osc_uce = st.text_area("Dúvida sobre du sinal capturado:", key="d_osc_uce")
        if st.button("🔍 Analisar Sinal Osciloscópio", key="btn_ind_osc"):
            ans = analisar_ponto_individual("Osciloscópio UCE", f"Dúvida Sinal: {duvida_osc_uce}", img_osc_uce)
            if ans: st.info(ans)

    with st.expander("9. 📉 Analisar Curva Característica (Tracker / Rastreador de Defeitos V/I)", expanded=False):
        img_curva = st.file_uploader("Foto da Curva V/I du Componente", type=["png", "jpg", "jpeg"], key="u_curva")
        duvida_curva = st.text_area("Dúvida sobre a forma de onda / curva característica:", key="d_curva")
        if st.button("🔍 Analisar Curva V/I", key="btn_ind_curva"):
            ans = analisar_ponto_individual("Curva V/I", f"Dúvida Curva V/I: {duvida_curva}", img_curva)
            if ans: st.info(ans)

    st.markdown("---")

    if st.button("🧠 EXECUTAR ANÁLISE COMPLETA CONSOLIDADA E GERAR REPORT U.C.E 🚀", width="stretch"):
        status_atual_check = verificar_status_usuario(st.session_state['user_email'])
        if st.session_state['user_email'] != EMAIL_ADM and (status_atual_check["tipo"] == "expirado" or (status_atual_check["tipo"] == "teste" and status_atual_check["fichas"] <= 0)):
            st.error("⚠️ Seu período de teste de 7 dias ou suas fichas esgotaram! Assine um dos planos na aba 💳 Assinatura para continuar.")
        else:
            if veiculo_uce_geral:
                
                # BARRA DE CARREGAMENTO (0% A 100%) PARA U.C.Es
                barra_prog_uce = st.progress(0)
                status_txt_uce = st.empty()
                
                status_txt_uce.markdown("🔌 **[0%]** — Lendo hardware, fotos e dúvidas da U.C.E...")
                barra_prog_uce.progress(15)
                time.sleep(0.3)

                status_txt_uce.markdown("🧠 **[45%]** — Executando engenharia reversa com AutoLab AI...")
                barra_prog_uce.progress(45)
                time.sleep(0.3)

                status_txt_uce.markdown("⚙️ **[75%]** — Mapeando ferramentas em cascata (Scanner, Bancada e OBD2)...")
                barra_prog_uce.progress(75)
                time.sleep(0.3)
                
                detalhes_componentes_num = ""
                if 'lista_componentes_num' in st.session_state:
                    detalhes_componentes_num = "\nCOMPONENTES NUMERADOS NA PLACA:\n" + "\n".join([f"[{c['numero']}] {c['nome']}: {c['descricao']}" for c in st.session_state['lista_componentes_num']])

                prompt_lab = f"""
                ATUE COMO O ESPECIALISTA CHEFE EM ENGENHARIA REVERSA DE U.C.ES DA AUTOLAB.
                
                CATEGORIA du MÓDULO: {modulo_tipo_sel}
                IDENTIFICAÇÃO du MÓDULO/VEÍCULO: {veiculo_uce_geral}
                DÚVIDA TÉCNICA PRINCIPAL: {duvida_uce_principal if duvida_uce_principal else 'Consulte os tópicos abaixo'}
                {detalhes_componentes_num}

                SITUAÇÕES ANALISADAS PELO TÉCNICO:
                - Placa Completa: {duvida_placa if duvida_placa else 'Não enviada'}
                - Componente Específico: {duvida_comp if duvida_comp else 'Não enviado'}
                - Part Number/Silk: {part_number if part_number else 'Não informado'} | {duvida_pn}
                - Dúvida Datasheet: {duvida_ds if duvida_ds else 'Não informada'}
                - Dúvida Memória SOIC: {duvida_soic if duvida_soic else 'Não informada'}
                - Dúvida Processador MCU: {duvida_mcu if duvida_mcu else 'Não informada'}
                - Dúvida Boot / Bench: {duvida_boot if duvida_boot else 'Não informada'}
                - Dúvida Osciloscópio: {duvida_osc_uce if duvida_osc_uce else 'Não informada'}
                - Dúvida Curva V/I: {duvida_curva if duvida_curva else 'Não informada'}

                ESTRUTURA OBRIGATÓRIA DO RELATÓRIO TÉCNICO CONSOLIDADO AUTOLAB U.C.E:

                ### 🎯 1. ANÁLISE TÉCNICA DOS HARDWARES E DÚVIDAS REGISTRADAS
                (Responda detalhadamente os procedimentos de teste, medição de componentes/drivers, pinagem, comunicação CAN/LIN e dicas de reparo).

                ---
                ### ⚙️ 2. EQUIPAMENTOS RECOMENDADOS PARA ESTE MÓDULO (INFORMAÇÃO IMEDIATA EM CASCATA):

                #### 📟 MELHOR SCANNER
                (Informe du scanner de diagnóstico ideal para esta U.C.E. Ex: Bosch KTS, Launch X431, Autel Maxisys, Rasther III, Raven, G-Scan, etc., detalhando du motivo).

                #### 💻 MELHOR PROGRAMADOR PARA PROGRAMAÇÃO (BANCADA / BOOT / BDM / BENCH / JTAG)
                (Informe os melhores gravadores/programadores de bancada para este módulo específico. Ex: KTAG, VVDI Prog, Flex Magicmotorsport, Transdata, I/O Terminal, Orange5, UPA-USB, CGDI, DFOX, etc.).

                #### 🔌 MELHOR PROGRAMADOR VIA OBD2
                (Informe du melhor programador via tomada OBD2 direto du veículo para esta U.C.E. Ex: KESS V2, Autohex, VVDI Key Tool Plus, PCMFlash, BitBox, MPPS, Zed-Full, Obdstar, Lonsdor, etc.).
                """

                conteudo_lab = [prompt_lab]

                if audio_uce:
                    try:
                        audio_uce.seek(0)
                        conteudo_lab.append(types.Part.from_bytes(data=audio_uce.read(), mime_type="audio/wav"))
                    except Exception: pass

                if foto_uce_1:
                    try:
                        foto_uce_1.seek(0)
                        img_f1 = Image.open(foto_uce_1)
                        img_f1.thumbnail((1280, 1280))
                        buf_f1 = io.BytesIO()
                        img_f1.save(buf_f1, format="JPEG", quality=85)
                        conteudo_lab.append(types.Part.from_bytes(data=buf_f1.getvalue(), mime_type="image/jpeg"))
                    except Exception: pass

                if foto_uce_2:
                    try:
                        foto_uce_2.seek(0)
                        img_f2 = Image.open(foto_uce_2)
                        img_f2.thumbnail((1280, 1280))
                        buf_f2 = io.BytesIO()
                        img_f2.save(buf_f2, format="JPEG", quality=85)
                        conteudo_lab.append(types.Part.from_bytes(data=buf_f2.getvalue(), mime_type="image/jpeg"))
                    except Exception: pass

                if video_uce:
                    try:
                        video_uce.seek(0)
                        conteudo_lab.append(types.Part.from_bytes(data=video_uce.read(), mime_type=video_uce.type if video_uce.type else "video/mp4"))
                    except Exception: pass

                lista_uploads = [
                    (img_placa_comp, "Placa_Completa"), (img_comp, "Componente"), (file_ds, "Datasheet"),
                    (img_soic, "SOIC"), (img_mcu, "MCU"), (img_boot, "Boot"), (img_osc_uce, "Osciloscopio"), (img_curva, "Curva_VI")
                ]

                for up_file, rotulo in lista_uploads:
                    if up_file:
                        try:
                            up_file.seek(0)
                            if getattr(up_file, 'type', '') == "application/pdf":
                                conteudo_lab.append(types.Part.from_bytes(data=up_file.read(), mime_type="application/pdf"))
                            else:
                                img_p = Image.open(up_file)
                                img_p.thumbnail((1280, 1280))
                                buf_p = io.BytesIO()
                                img_p.save(buf_p, format="JPEG", quality=85)
                                conteudo_lab.append(types.Part.from_bytes(data=buf_p.getvalue(), mime_type="image/jpeg"))
                        except Exception: pass

                config_lab = types.GenerateContentConfig(
                    system_instruction="Você é du Especialista Master em Reparo de Módulos UCEs e Engenharia Reversa da AutoLab.",
                    temperature=0.2
                )

                try:
                    resp_lab = client.models.generate_content(
                        model='gemini-3-flash-preview',
                        contents=conteudo_lab,
                        config=config_lab
                    )
                    
                    # 100% CONCLUÍDO
                    barra_prog_uce.progress(100)
                    status_txt_uce.markdown("✅ **[100%]** — Report U.C.E Concluído com Sucesso!")
                    time.sleep(0.5)
                    
                    barra_prog_uce.empty()
                    status_txt_uce.empty()

                    if resp_lab and hasattr(resp_lab, 'text') and resp_lab.text:
                        texto_laudo = resp_lab.text
                        st.session_state['relatorio_uce_laboratorio'] = texto_laudo
                        
                        salvar_diagnostico(
                            email_usuario,
                            f"U.C.E: {veiculo_uce_geral} ({modulo_tipo_sel})",
                            "N/A (Bancada U.C.E)",
                            duvida_uce_principal if duvida_uce_principal else "Análise de Hardware / Mapeamento",
                            texto_laudo
                        )
                        
                        ferramentas_encontradas = {}
                        for linha in texto_laudo.split('\n'):
                            if "SCANNER:" in linha.upper() or "BANCADA:" in linha.upper() or "OBD2:" in linha.upper():
                                partes = linha.split(":")
                                if len(partes) > 1:
                                    nome_eq = partes[1].strip().replace("*", "")[:40]
                                    if len(nome_eq) > 3:
                                        ferramentas_encontradas[nome_eq] = gerar_foto_equipamento(nome_eq)
                        
                        if len(ferramentas_encontradas) < 3:
                            ferramentas_encontradas["Scanner Profissional de Bancada"] = gerar_foto_equipamento("Scanner Profissional")
                            ferramentas_encontradas["Programador de Bancada (Boot/BDM)"] = gerar_foto_equipamento("Programador Bancada")
                            ferramentas_encontradas["Programador OBD2 Direto"] = gerar_foto_equipamento("Programador OBD2")

                        st.session_state['imagens_ferramentas_uce'] = ferramentas_encontradas
                        st.success("Análise Consolidada de U.C.Es Concluída e Salva no Histórico!")
                    else:
                        st.error("Não foi possível gerar a análise técnica du momento.")
                except Exception as err_l:
                    barra_prog_uce.empty()
                    status_txt_uce.empty()
                    st.error(f"Erro na requisição: {err_l}")
            else:
                st.warning("Informe a identificação du Módulo / Veículo no topo antes de executar.")

    if 'relatorio_uce_laboratorio' in st.session_state and st.session_state['relatorio_uce_laboratorio']:
        st.markdown("---")
        st.markdown("### 📋 REPORT AUTOLAB U.C.E - RELATÓRIO CONSOLIDADO")
        relatorio_uce_final = st.session_state['relatorio_uce_laboratorio']
        st.markdown(relatorio_uce_final)

        if 'imagens_ferramentas_uce' in st.session_state and st.session_state['imagens_ferramentas_uce']:
            st.markdown("---")
            st.markdown("#### 🛠️ Equipamentos Sugeridos para esta Bancada:")
            cols_fer = st.columns(len(st.session_state['imagens_ferramentas_uce']))
            for idx, (nome_fer, img_f) in enumerate(st.session_state['imagens_ferramentas_uce'].items()):
                with cols_fer[idx]:
                    st.image(img_f, caption=nome_fer, use_container_width=True)

        st.markdown("---")
        st.markdown("#### ⚡ Atalhos de Consulta Rápidas de Ferramentas")
        
        texto_laudo_cache = st.session_state['relatorio_uce_laboratorio']
        scanner_txt, bancada_txt, obd_txt = "Consulte du laudo acima.", "Consulte du laudo acima.", "Consulte du laudo acima."
        for linha in texto_laudo_cache.split('\n'):
            if "SCANNER" in linha.upper(): scanner_txt = linha
            elif "BANCADA" in linha.upper() or "BOOT" in linha.upper(): bancada_txt = linha
            elif "OBD" in linha.upper(): obd_txt = linha

        c_casc1, c_casc2, c_casc3 = st.columns(3)
        with c_casc1:
            with st.expander("📟 Melhor Scanner Recomendado", expanded=False):
                st.info(scanner_txt)
        with c_casc2:
            with st.expander("💻 Melhor Programador para Bancada", expanded=False):
                st.info(bancada_txt)
        with c_casc3:
            with st.expander("🔌 Melhor Programador via OBD2", expanded=False):
                st.info(obd_txt)

        st.markdown("---")
        
        img_pdf_arg = st.session_state.get('imagem_mapeada_num', st.session_state.get('imagem_mapeada_cor', None))
        imgs_fer_arg = st.session_state.get('imagens_ferramentas_uce', None)
        
        pdf_uce = gerar_pdf_relatorio(
            st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
            veiculo_uce_geral if veiculo_uce_geral else "Módulo Eletrônico UCE",
            "Análise de Bancada / Hardware",
            duvida_uce_principal if duvida_uce_principal else "Engenharia Reversa UCE",
            relatorio_uce_final,
            titulo_pdf="REPORT AUTOLAB U.C.E - LAUDO DE HARDWARE & ENGENHARIA REVERSA",
            imagem_placa_pil=img_pdf_arg,
            imagens_ferramentas=imgs_fer_arg
        )

        st.download_button(
            label="📥 BAIXAR REPORT AUTOLAB U.C.E EM PDF",
            data=pdf_uce,
            file_name=f"Report_AutoLab_UCE_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            width="stretch"
        )

# =========================================================
# ABA 📡 SUPORTE SCANNERS (COM BARRA 0-100% E PDF)
# =========================================================
with aba_scanners:
    st.subheader("📡 Suporte Avançado de Scanners & Compatibilidade")
    st.write("Cadastre os scanners que você possui na oficina para a IA analisar a viabilidade de execução dos procedimentos ou tire dúvidas técnicas.")
    st.markdown("---")

    col_sc_cad, col_sc_duv = st.columns([1, 1], gap="large")

    with col_sc_cad:
        st.markdown("### 🛠️ Cadastro de Scanners da Oficina")
        scanners_disponiveis = [
            "Bosch KTS (540 / 560 / 590 / 350)",
            "Launch X431 (Pro / Pad / Diagzone)",
            "Autel MaxiSys (Elite / MS908 / Ultra)",
            "Tecnomotor Rasther (III / TS / I)",
            "Raven (III / II)",
            "G-Scan (2 / 3 / Z)",
            "Kess / K-Tag / DFOX (Bancada)",
            "Outros Scanners / Interface J2534"
        ]
        scanners_selecionados = st.multiselect("Selecione seus Scanners:", scanners_disponiveis, default=["Bosch KTS (540 / 560 / 590 / 350)", "Launch X431 (Pro / Pad / Diagzone)"])
        outro_scanner = st.text_input("Cadastre Aqui Seus Scanners / Versão Específica:", placeholder="Ex: Scanner específico...")
        
        if st.button("💾 Salvar Inventário de Scanners", width="stretch"):
            lista_final_scanners = ", ".join(scanners_selecionados)
            if outro_scanner: lista_final_scanners += f", {outro_scanner}"
            conn = sqlite3.connect('diagnosticos.db')
            c = conn.cursor()
            c.execute('UPDATE usuarios SET scanners_cadastrados = ? WHERE email = ?', (lista_final_scanners, email_usuario))
            conn.commit()
            conn.close()
            st.success("✅ Scanners salvos com sucesso!")

    with col_sc_duv:
        st.markdown("### 💬 Dúvidas sobre Procedimentos com Scanners")
        veiculo_scanner_duvida = st.text_input("Veículo / Sistema para Procedimento:", placeholder="Ex: Hilux 2.8 D4D - Sangria de ABS ou Codificação de Bicos")
        pergunta_scanner = st.text_area("Descreva a dúvida sobre o procedimento:")
        col_m_sc1, col_m_sc2 = st.columns(2)
        with col_m_sc1: foto_tela_scanner = st.file_uploader("📸 Foto a ser analisada", type=["png", "jpg", "jpeg"], key="foto_tela_sc")
        with col_m_sc2: audio_video_scanner = st.file_uploader("🎥 Vídeo / Áudio / Imagem Extra", type=["mp4", "mov", "avi", "mkv", "mp3", "wav", "ogg"], key="midia_extra_sc")
        mic_sc = st.audio_input("🎙️ Gravar sua Dúvida por Áudio Aqui)", key="mic_sc")

    st.markdown("---")
    if st.button("🚀 Analisar Procedimento com Scanners 🚀", width="stretch"):
        if veic_sc := veiculo_scanner_duvida:
            
            # BARRA DE CARREGAMENTO (0% A 100%) PARA SCANNERS
            barra_prog_sc = st.progress(0)
            status_txt_sc = st.empty()
            
            status_txt_sc.markdown("📡 **[0%]** — Lendo inventário de scanners e dados du veículo...")
            barra_prog_sc.progress(20)
            time.sleep(0.3)

            status_txt_sc.markdown("🧠 **[50%]** — Verificando compatibilidade de menus com a IA...")
            barra_prog_sc.progress(50)
            time.sleep(0.3)

            status_txt_sc.markdown("⚙️ **[80%]** — Formatando passo a passo técnico...")
            barra_prog_sc.progress(80)
            time.sleep(0.3)

            scanners_do_usuario = ", ".join(scanners_selecionados) if 'scanners_selecionados' in locals() else "Nenhum cadastrado"
            prompt_scanner_ia = f"""
            ATUE COMO O ENGENHEIRO CHEFE EM DIAGNÓSTICO AUTOMOTIVO E ESPECIALISTA EM SCANNERS DA AUTOLAB.
            - Veículo/Sistema: {veiculo_scanner_duvida}
            - Dúvida: {pergunta_scanner}
            - Scanners Disponíveis: {scanners_do_usuario}
            Forneça análise de compatibilidade e passo a passo detalhado du menu du scanner.
            """
            contents_sc = [prompt_scanner_ia]
            if mic_sc:
                mic_sc.seek(0)
                contents_sc.append(types.Part.from_bytes(data=mic_sc.read(), mime_type="audio/wav"))
            if foto_tela_scanner:
                foto_tela_scanner.seek(0)
                img_s = Image.open(foto_tela_scanner)
                img_s.thumbnail((1280, 1280))
                buf_s = io.BytesIO()
                img_s.save(buf_s, format="JPEG", quality=85)
                contents_sc.append(types.Part.from_bytes(data=buf_s.getvalue(), mime_type="image/jpeg"))
            
            resp_sc = client.models.generate_content(model='gemini-3-flash-preview', contents=contents_sc)
            texto_resp_sc = resp_sc.text if hasattr(resp_sc, 'text') else "Sem resposta."
            
            # 100% CONCLUÍDO
            barra_prog_sc.progress(100)
            status_txt_sc.markdown("✅ **[100%]** — Análise de Scanner Concluída com Sucesso!")
            time.sleep(0.4)
            
            barra_prog_sc.empty()
            status_txt_sc.empty()
            
            salvar_diagnostico(
                email_usuario,
                f"Scanner / Veículo: {veiculo_scanner_duvida}",
                "Procedimento de Scanner",
                pergunta_scanner,
                texto_resp_sc
            )
            
            st.markdown(texto_resp_sc)
            st.success("Análise de Scanner salva no Histórico!")
            
            # OPÇÃO DE PDF PARA SCANNERS
            pdf_sc = gerar_pdf_relatorio(
                st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
                f"Veículo: {veiculo_scanner_duvida}",
                "Procedimento de Scanner",
                pergunta_scanner,
                texto_resp_sc,
                titulo_pdf="LAUDO TÉCNICO - SUPORTE DE SCANNERS"
            )
            st.download_button(
                label="📥 BAIXAR ESTE LAUDO DE SCANNER EM PDF",
                data=pdf_sc,
                file_name=f"Laudo_Scanner_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                width="stretch"
            )

# =========================================================
# ABA 💻 SUPORTE PROGRAMADORES (COM BARRA 0-100% E PDF)
# =========================================================
with aba_programadores:
    st.subheader("💻 Suporte de Programadores, Boots, Memórias & Processadores")
    st.write("Tire dúvidas sobre conexões de Boot, BDM, JTAG, leitura de memórias SOIC/Flash e processadores MCU.")
    st.markdown("---")

    col_pg_cad, col_pg_duv = st.columns([1, 1], gap="large")
    with col_pg_cad:
        st.markdown("### 🛠️ Cadastro de Programadores")
        prog_disp = ["K-Tag / Kess", "VVDI Prog / Key Tool Plus", "Orange 5", "UPA-USB", "Flex", "DFOX", "I/O Terminal"]
        prog_sel = st.multiselect("Selecione seus Programadores:", prog_disp, default=["K-Tag / Kess", "VVDI Prog / Key Tool Plus"])
        if st.button("💾 Salvar Programadores", width="stretch"):
            conn = sqlite3.connect('diagnosticos.db')
            c = conn.cursor()
            c.execute('UPDATE usuarios SET programadores_cadastrados = ? WHERE email = ?', (", ".join(prog_sel), email_usuario))
            conn.commit()
            conn.close()
            st.success("✅ Programadores salvos!")

    with col_pg_duv:
        st.markdown("### 💬 Dúvidas de Bancada (Boot / MCU / Memória)")
        mod_pg = st.text_input("Módulo / MCU / Memória:", placeholder="Ex: EDC17C69 (Tricore TC1793)")
        duv_pg = st.text_area("Descreva a dúvida de boot/conexão:")
        foto_pg = st.file_uploader("📸 Foto da Placa / Conexão de Boot", type=["png", "jpg", "jpeg"], key="foto_pg")
        mic_pg = st.audio_input("🎙️ Gravar Dúvida por Áudio (Programadores)", key="mic_pg")

    st.markdown("---")
    if st.button("🚀 Analisar Conexão de Bancada 🚀", width="stretch"):
        if mod_pg:
            
            # BARRA DE CARREGAMENTO (0% A 100%) PARA PROGRAMADORES
            barra_prog_pg = st.progress(0)
            status_txt_pg = st.empty()
            
            status_txt_pg.markdown("💻 **[0%]** — Lendo processador/memória e conexão de bancada...")
            barra_prog_pg.progress(25)
            time.sleep(0.3)

            status_txt_pg.markdown("🧠 **[60%]** — Mapeando pinos de Boot/BDM com a IA...")
            barra_prog_pg.progress(60)
            time.sleep(0.3)

            prompt_pg_ia = f"Módulo/MCU: {mod_pg}. Dúvida: {duv_pg}. Ferramentas: {prog_sel}."
            c_pg = [prompt_pg_ia]
            if mic_pg:
                mic_pg.seek(0)
                c_pg.append(types.Part.from_bytes(data=mic_pg.read(), mime_type="audio/wav"))
            if foto_pg:
                foto_pg.seek(0)
                img_pg_f = Image.open(foto_pg)
                img_pg_f.thumbnail((1280, 1280))
                buf_pg = io.BytesIO()
                img_pg_f.save(buf_pg, format="JPEG", quality=85)
                c_pg.append(types.Part.from_bytes(data=buf_pg.getvalue(), mime_type="image/jpeg"))
            
            resp_pg = client.models.generate_content(model='gemini-3-flash-preview', contents=c_pg)
            texto_resp_pg = resp_pg.text if hasattr(resp_pg, 'text') else "Sem resposta."
            
            # 100% CONCLUÍDO
            barra_prog_pg.progress(100)
            status_txt_pg.markdown("✅ **[100%]** — Análise de Bancada Concluída com Sucesso!")
            time.sleep(0.4)
            
            barra_prog_pg.empty()
            status_txt_pg.empty()
            
            salvar_diagnostico(
                email_usuario,
                f"Programador / MCU: {mod_pg}",
                "Boot / BDM / Bench",
                duv_pg,
                texto_resp_pg
            )
            
            st.markdown(texto_resp_pg)
            st.success("Análise de Bancada salva no Histórico!")
            
            # OPÇÃO DE PDF PARA PROGRAMADORES
            pdf_pg = gerar_pdf_relatorio(
                st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
                f"Módulo/MCU: {mod_pg}",
                "Boot / BDM / Bench",
                duv_pg,
                texto_resp_pg,
                titulo_pdf="LAUDO TÉCNICO - PROGRAMADORES & BANCADA"
            )
            st.download_button(
                label="📥 BAIXAR ESTE LAUDO DE BANCADA EM PDF",
                data=pdf_pg,
                file_name=f"Laudo_Bancada_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                mime="application/pdf",
                width="stretch"
            )

# =========================================================
# ABA ⚙️ SUPORTE PROGRAMAÇÃO (COM BARRA 0-100% E PDF NAS DÚVIDAS)
# =========================================================
with aba_programacao:
    st.subheader("⚙️ Suporte Avançado de Programação & Arquivos Binários")
    st.write("Calculadora científica/programador estilo Windows, Editor HEX com visualizador Buffer 16 colunas, Leitor de CKS & ASCII Inteligente via IA, e Comparador de Arquivos.")
    st.markdown("---")

    tab_calc, tab_hex, tab_cks, tab_comp, tab_duv_prog = st.tabs([
        "🧮 Calculadora Computador", 
        "📝 Editor HEX & Buffer 16xN", 
        "🔍 CKS & Extração ASCII (IA)", 
        "📊 Comparador de Arquivos", 
        "💬 Dúvidas sobre Arquivos"
    ])

    with tab_calc:
        st.markdown("### 🧮 Calculadora Profissional (Estilo Windows)")
        st.caption("Você pode clicar nos botões du mouse ou digitar diretamente du visor com du teclado du computador:")

        if 'calc_input' not in st.session_state:
            st.session_state['calc_input'] = "0"

        def click_btn(val):
            curr = str(st.session_state['calc_input'])
            if curr == "0" or curr == "Erro":
                st.session_state['calc_input'] = str(val)
            else:
                st.session_state['calc_input'] += str(val)

        def limpar_calc():
            st.session_state['calc_input'] = "0"

        def calcular_resultado():
            try:
                expr = str(st.session_state['calc_input']).replace('×', '*').replace('÷', '/')
                res = eval(expr)
                st.session_state['calc_input'] = str(res)
            except Exception:
                st.session_state['calc_input'] = "Erro"

        visor_val = st.session_state['calc_input']
        st.markdown(f"""
        <div style="background-color: #011611; border: 2px solid #00FF88; padding: 15px; border-radius: 10px; text-align: right; font-size: 2rem; font-weight: 900; color: #00FF88; margin-bottom: 15px; box-shadow: 0 0 15px rgba(0,255,136,0.3);">
            {visor_val}
        </div>
        """, unsafe_allow_html=True)

        try:
            num_base = int(float(visor_val))
            st.markdown(f"""
            <div style="background-color: rgba(0,229,255,0.08); border-left: 4px solid #00E5FF; padding: 10px; border-radius: 6px; margin-bottom: 20px; font-weight: 700; color: #00E5FF;">
                HEX: <span style="color:#FFF;">0x{num_base:X}</span> | DEC: <span style="color:#FFF;">{num_base}</span> | OCT: <span style="color:#FFF;">{oct(num_base)}</span> | BIN: <span style="color:#FFF;">{bin(num_base)}</span>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            pass

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            if st.button("C", key="btn_c", width="stretch"): limpar_calc()
            if st.button("7", key="btn_7", width="stretch"): click_btn('7')
            if st.button("4", key="btn_4", width="stretch"): click_btn('4')
            if st.button("1", key="btn_1", width="stretch"): click_btn('1')
            if st.button("0", key="btn_0", width="stretch"): click_btn('0')
        with c2:
            if st.button("(", key="btn_par_dir", width="stretch"): click_btn('(')
            if st.button("8", key="btn_8", width="stretch"): click_btn('8')
            if st.button("5", key="btn_5", width="stretch"): click_btn('5')
            if st.button("2", key="btn_2", width="stretch"): click_btn('2')
            if st.button("00", key="btn_00", width="stretch"): click_btn('00')
        with c3:
            if st.button(")", key="btn_par_esq", width="stretch"): click_btn(')')
            if st.button("9", key="btn_9", width="stretch"): click_btn('9')
            if st.button("6", key="btn_6", width="stretch"): click_btn('6')
            if st.button("3", key="btn_3", width="stretch"): click_btn('3')
            if st.button(".", key="btn_ponto", width="stretch"): click_btn('.')
        with c4:
            if st.button("÷", key="btn_div", width="stretch"): click_btn('÷')
            if st.button("×", key="btn_mult", width="stretch"): click_btn('×')
            if st.button("-", key="btn_menos", width="stretch"): click_btn('-')
            if st.button("+", key="btn_mais", width="stretch"): click_btn('+')
            if st.button("=", key="btn_igual", width="stretch"): calcular_resultado()
        with c5:
            if st.button("A", key="btn_a", width="stretch"): click_btn('A')
            if st.button("B", key="btn_b", width="stretch"): click_btn('B')
            if st.button("C", key="btn_c_hex", width="stretch"): click_btn('C')
            if st.button("D", key="btn_d", width="stretch"): click_btn('D')
            col_e, col_f = st.columns(2)
            with col_e: 
                if st.button("E", key="btn_e", width="stretch"): click_btn('E')
            with col_f: 
                if st.button("F", key="btn_f", width="stretch"): click_btn('F')

    with tab_hex:
        st.markdown("### 📝 Editor HEX & Buffer (16 Colunas x Linhas Ilimitadas)")
        arquivo_hex_vis = st.file_uploader("Carregar arquivo binário para visualização em Buffer HEX", type=["bin", "hex", "ori", "mod"], key="up_hex_vis")
        
        if arquivo_hex_vis:
            dados_bin = arquivo_hex_vis.read()
            tamanho_total = len(dados_bin)
            st.info(f"📁 Arquivo carregado com sucesso! Tamanho total: **{tamanho_total} bytes**")
            
            linhas_buffer = []
            chunk_size = 16
            for i in range(0, min(tamanho_total, 4096), chunk_size):
                chunk = dados_bin[i:i+chunk_size]
                offset_str = f"{i:08X}"
                hex_parte = " ".join(f"{b:02X}" for b in chunk)
                ascii_parte = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                linhas_buffer.append(f"{offset_str}  {hex_parte.ljust(47)}  |{ascii_parte}|")
            
            buffer_formatado = "\n".join(linhas_buffer)
            st.code(buffer_formatado, language="text")
            if tamanho_total > 4096:
                st.caption(f"ℹ️ Exibindo os primeiros 4096 bytes de {tamanho_total} bytes totais du buffer para visualização fluida.")

    with tab_cks:
        st.markdown("### 🔍 Cálculo de CKS & Leitura ASCII Inteligente (IA)")
        arquivo_cks = st.file_uploader("Carregar arquivo para análise de CKS e ASCII", type=["bin", "hex", "ori", "mod"], key="up_cks")
        
        if arquivo_cks:
            bytes_cks = arquivo_cks.read()
            tamanho_arq = len(bytes_cks)
            ascii_bruto = "".join([chr(b) if 32 <= b <= 126 else "." for b in bytes_cks])
            padrao_vin = re.findall(r'[A-HJ-NPR-Z0-9]{17}', ascii_bruto)
            
            col_cks_info, col_cks_ia = st.columns([1, 1], gap="large")
            with col_cks_info:
                st.markdown(f"**Tamanho du Arquivo:** `{tamanho_arq} bytes`")
                st.markdown(f"**Hash SHA256:** `{hashlib.sha256(bytes_cks).hexdigest()}`")
                if padrao_vin:
                    st.success(f"🔍 **VIN Encontrado:** {', '.join(set(padrao_vin))}")
                else:
                    st.info("Nenhum VIN de 17 dígitos detectado na varredura simples.")
            
            with col_cks_ia:
                if st.button("🤖 Pedir Análise Completa de ASCII e CKS à IA", width="stretch", key="btn_ia_cks"):
                    
                    # BARRA DE CARREGAMENTO PARA CKS / IA
                    barra_prog_cks = st.progress(0)
                    status_txt_cks = st.empty()
                    
                    status_txt_cks.markdown("🔍 **[0%]** — Lendo estrutura binária e CKS...")
                    barra_prog_cks.progress(30)
                    time.sleep(0.3)
                    
                    amostra_ascii = ascii_bruto[:2000]
                    prompt_ia_bin = f"""
                    Analise estes dados extraídos em ASCII de um arquivo binário automotivo:
                    {amostra_ascii}
                    Identifique e liste:
                    1. Número da Peça / Software / Hardware
                    2. Informações de Imobilizador / VIN
                    3. Status provável du Checksum (CKS).
                    """
                    res_bin_ia = client.models.generate_content(model='gemini-3-flash-preview', contents=[prompt_ia_bin])
                    texto_res_cks = res_bin_ia.text if hasattr(res_bin_ia, 'text') else "Sem dados."
                    
                    # 100% CONCLUÍDO
                    barra_prog_cks.progress(100)
                    status_txt_cks.markdown("✅ **[100%]** — Análise Binária Concluída!")
                    time.sleep(0.4)
                    
                    barra_prog_cks.empty()
                    status_txt_cks.empty()
                    
                    st.markdown(texto_res_cks)

    with tab_comp:
        st.markdown("### 📊 Comparador de Arquivos (File Comparer)")
        col_cp1, col_cp2 = st.columns(2)
        with col_cp1: arq_original = st.file_uploader("Arquivo Original (.ori)", type=["bin", "hex", "ori"], key="ori_file")
        with col_cp2: arq_modificado = st.file_uploader("Arquivo Modificado (.mod)", type=["bin", "hex", "mod"], key="mod_file")
            
        if arq_original and arq_modificado:
            b_ori = arq_original.read()
            b_mod = arq_modificado.read()
            if len(b_ori) == len(b_mod):
                diferencas = sum(1 for o, m in zip(b_ori, b_mod) if o != m)
                st.success(f"✅ Arquivos com o mesmo tamanho ({len(b_ori)} bytes).")
                st.warning(f"🔄 **Bytes diferentes encontrados:** {diferencas} bytes alterados.")
            else:
                st.error(f"⚠️ Tamanhos diferentes! Original: {len(b_ori)} bytes | Modificado: {len(b_mod)} bytes.")

    with tab_duv_prog:
        st.markdown("### 💬 Dúvidas sobre Arquivos, CKS ou Modificações")
        duv_arq_texto = st.text_area("Descreva sua dúvida:", placeholder="Ex: Preciso de ajuda para corrigir du CKS...", key="duv_arq_txt")
        arq_duvida_sup = st.file_uploader("Anexar arquivo para suporte", type=["bin", "hex", "ori", "mod"], key="arq_duv_up")
        foto_arq_sup = st.file_uploader("📸 Foto da central ou erro", type=["png", "jpg", "jpeg"], key="foto_duv_up")
        mic_prog_sup = st.audio_input("🎙️ Gravar Dúvida por Áudio", key="mic_prog_sup")

        if st.button("🚀 Enviar Dúvida para a IA 🚀", width="stretch", key="btn_enviar_duv_prog"):
            if duv_arq_texto:
                
                # BARRA DE CARREGAMENTO PARA SUPORTE DE ARQUIVOS
                barra_prog_arq = st.progress(0)
                status_txt_arq = st.empty()
                
                status_txt_arq.markdown("💬 **[0%]** — Lendo arquivo e solicitação técnica...")
                barra_prog_arq.progress(30)
                time.sleep(0.3)
                
                c_prog_sup = [f"Dúvida sobre arquivos/programação: {duv_arq_texto}"]
                if mic_prog_sup:
                    mic_prog_sup.seek(0)
                    c_prog_sup.append(types.Part.from_bytes(data=mic_prog_sup.read(), mime_type="audio/wav"))
                if foto_arq_sup:
                    foto_arq_sup.seek(0)
                    img_ds = Image.open(foto_arq_sup)
                    img_ds.thumbnail((1280, 1280))
                    buf_ds = io.BytesIO()
                    img_ds.save(buf_ds, format="JPEG", quality=85)
                    c_prog_sup.append(types.Part.from_bytes(data=buf_ds.getvalue(), mime_type="image/jpeg"))
                
                r_prog_sup = client.models.generate_content(model='gemini-3-flash-preview', contents=c_prog_sup)
                texto_resp_prog = r_prog_sup.text if hasattr(r_prog_sup, 'text') else "Sem resposta."
                
                # 100% CONCLUÍDO
                barra_prog_arq.progress(100)
                status_txt_arq.markdown("✅ **[100%]** — Suporte Concluído com Sucesso!")
                time.sleep(0.4)
                
                barra_prog_arq.empty()
                status_txt_arq.empty()
                
                salvar_diagnostico(
                    email_usuario,
                    "Suporte de Arquivos & CKS",
                    "Binário / Flash / EEPROM",
                    duv_arq_texto,
                    texto_resp_prog
                )
                
                st.markdown(texto_resp_prog)
                st.success("Consulta de Arquivos salva no Histórico!")
                
                # OPÇÃO DE PDF PARA ARQUIVOS
                pdf_arq = gerar_pdf_relatorio(
                    st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
                    "Suporte de Arquivos & CKS",
                    "Binário / Flash / EEPROM",
                    duv_arq_texto,
                    texto_resp_prog,
                    titulo_pdf="LAUDO TÉCNICO - SUPORTE DE ARQUIVOS"
                )
                st.download_button(
                    label="📥 BAIXAR ESTE LAUDO DE ARQUIVOS EM PDF",
                    data=pdf_arq,
                    file_name=f"Laudo_Arquivos_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    width="stretch"
                )
            else:
                st.warning("Escreva a sua dúvida antes de enviar.")

# =========================================================
# ABA 3: HISTÓRICO DOS DIAGNÓSTICOS
# =========================================================
with aba2:
    st.subheader("📜 Histórico Geral de Todas as Consultas e Diagnósticos")
    registros = carregar_historico(st.session_state['user_email'])
    
    if registros:
        for reg in registros:
            reg_id, reg_data, reg_veiculo, reg_dtc, reg_sintomas, reg_relatorio = reg
            with st.expander(f"🗓️ {reg_data} | 🚗 {reg_veiculo} | Ref/DTC: {reg_dtc or 'N/A'}"):
                st.write(f"**Detalhes / Sintomas:** {reg_sintomas or 'Não informado'}")
                st.markdown("**Relatório Técnico Gerado:**")
                st.markdown(reg_relatorio)
                
                pdf_hist = gerar_pdf_relatorio(
                    st.session_state.oficina_nome, st.session_state.oficina_cnpj, st.session_state.oficina_tel,
                    reg_veiculo, reg_dtc, reg_sintomas, reg_relatorio
                )
                st.download_button(
                    label="📥 Baixar PDF deste Relatório",
                    data=pdf_hist,
                    file_name=f"relatorio_historico_{reg_id}.pdf",
                    mime="application/pdf",
                    key=f"btn_pdf_{reg_id}"
                )
    else:
        st.info("Nenhum diagnóstico ou consulta salva até du momento.")

# =========================================================
# ABA 4: CURSOS & REDES SOCIAIS (COM EFEITO PULSANTE NEON)
# =========================================================
with aba3:
    st.markdown("### 🎓 Capacitação Técnica AutoLab LOA")
    st.write("Acesse a plataforma oficial de treinamentos e especialize-se em diagnóstico avançado.")
    
    st.link_button("🚀 ACESSAR PLATAFORMA DE CURSOS OFICIAL", "https://autolabbr.com.br/nossos-cursos/", width="stretch")
    st.markdown("---")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.markdown('''
            <div class="social-card-pulsing">
                <div style="font-size: 24px; margin-bottom: 5px;">📺</div>
                <div class="social-title">YouTube</div>
                <a href="https://youtube.com/@autolab77loa?si=VOHIITIGpI44lNvN" target="_blank" class="btn-custom btn-yt">Inscrever-se</a>
            </div>
        ''', unsafe_allow_html=True)
    with col_s2:
        st.markdown('''
            <div class="social-card-pulsing">
                <div style="font-size: 24px; margin-bottom: 5px;">📸</div>
                <div class="social-title">Instagram</div>
                <a href="https://www.instagram.com/autolab.laboratorio/" target="_blank" class="btn-custom btn-ig">Seguir</a>
            </div>
        ''', unsafe_allow_html=True)
    with col_s3:
        st.markdown('''
            <div class="social-card-pulsing">
                <div style="font-size: 24px; margin-bottom: 5px;">📘</div>
                <div class="social-title">Facebook</div>
                <a href="https://www.facebook.com/share/1EqhYtsNnK/?mibextid=wwXIfr" target="_blank" class="btn-custom btn-fb">Curtir</a>
            </div>
        ''', unsafe_allow_html=True)
    with col_s4:
        st.markdown('''
            <div class="social-card-pulsing">
                <div style="font-size: 24px; margin-bottom: 5px;">💬</div>
                <div class="social-title">WhatsApp</div>
                <a href="https://wa.me/message/H6EI475WHRPFF1" target="_blank" class="btn-custom btn-wsp">Contato</a>
            </div>
        ''', unsafe_allow_html=True)

# =========================================================
# ABA 5: WHATSAPP WEB INTEGRADO
# =========================================================
with aba4:
    st.markdown("### 💬 WhatsApp Web Integrado")
    st.write("Abra du WhatsApp Web da oficina ou envie textos, áudios e vídeos de clientes direto para a análise da IA.")
    st.markdown("---")
    
    col_wsp1, col_wsp2 = st.columns([1, 1])
    
    with col_wsp1:
        st.markdown("""
        <div style="background-color: #052E16; border: 1px solid #25D366; padding: 20px; border-radius: 12px; text-align: center;">
            <h4 style="color: #00FF88 !important; margin-bottom: 10px;">🟢 Acesso Direto du WhatsApp Web</h4>
            <p style="color: #A7F3D0 !important; font-size: 0.9rem;">Devido às políticas de segurança du WhatsApp, abra a sessão diretamente em seu navegador.</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        st.link_button("🚀 Abrir WhatsApp Web em Nova Aba", "https://web.whatsapp.com", width="stretch")
        
    with col_wsp2:
        st.markdown("""
        <div style="background-color: #052E16; border: 1px solid #065F46; padding: 20px; border-radius: 12px; text-align: center;">
            <h4 style="color: #00FF88 !important; margin-bottom: 10px;">📋 Copiar Mensagem, Áudio ou Vídeo du Cliente</h4>
            <p style="color: #A7F3D0 !important; font-size: 0.9rem;">Anexe os arquivos recebidos du WhatsApp para enviar direto à aba de Diagnóstico.</p>
        </div>
        """, unsafe_allow_html=True)
        
        texto_wsp = st.text_area("Texto/Transcrição du WhatsApp:", placeholder="Ex: Cliente relatou que du carro falha...", height=100)
        audio_file_wsp = st.file_uploader("🎙️ Anexar Áudio du WhatsApp (.ogg, .mp3, .wav, .m4a)", type=["ogg", "mp3", "wav", "m4a"], key="upload_audio_wsp")
        video_file_wsp = st.file_uploader("🎥 Anexar Vídeo du WhatsApp (.mp4, .mov, .avi, .mkv)", type=["mp4", "mov", "avi", "mkv"], key="upload_video_wsp")
        
        if st.button("🚀 Enviar Dados para Aba de Diagnóstico", width="stretch"):
            if texto_wsp.strip() or audio_file_wsp or video_file_wsp:
                if texto_wsp.strip(): st.session_state['sintomas_wsp'] = texto_wsp
                if audio_file_wsp:
                    st.session_state['audio_wsp_bytes'] = audio_file_wsp.read()
                    st.session_state['audio_wsp_mime'] = audio_file_wsp.type
                if video_file_wsp:
                    st.session_state['video_wsp_bytes'] = video_file_wsp.read()
                    st.session_state['video_wsp_mime'] = video_file_wsp.type
                
                st.success("Dados transferidos com sucesso! Vá para a Aba 🔬 Diagnóstico.")
                st.rerun()
            else:
                st.warning("Cole um texto, ou anexe um áudio/vídeo antes de enviar.")

# =========================================================
# ABA 6: PLANOS & ASSINATURA
# =========================================================
with aba5:
    renderizar_css_planos()
    st.markdown("<h3 style='text-align: center; color: #00FF88;'>💎 Planos & Níveis de Classificação AUTOLAB DIAG AI</h3>", unsafe_allow_html=True)
    st.write("<p style='text-align: center; color: #A7F3D0;'>Eleve du patamar tecnológico da sua oficina com inteligência artificial de alta performance.</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.markdown("""
        <div class="card-lux-1">
            <div style="font-size: 28px; margin-bottom: 5px;">🛡️</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px;">NÍVEL 1 - AMADOR</h4>
            <h2 style="color: #FFD700 !important; font-size: 2rem; margin-top: 5px;">R$ 57<span style="font-size: 13px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 15px 0;">
            <p style="color: #00FF88 !important; font-size: 13.5px; text-align: left; margin: 8px 0;">✨ <b>AUTOLAB DIAG</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 6px 0;">✔️ Diagnósticos com IA avançada</p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 6px 0;">✔️ Relatórios em PDF</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F3rcpp" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 1</a>', unsafe_allow_html=True)

    with col_p2:
        st.markdown("""
        <div class="card-lux-extreme">
            <div><span class="extreme-badge">🌟 EXTREME</span></div>
            <div style="font-size: 28px; margin-bottom: 2px;">⚡</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px;">NÍVEL 2 - PROFISSIONAL</h4>
            <h2 style="color: #FFD700 !important; font-size: 2rem; margin-top: 5px;">R$ 97<span style="font-size: 13px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 15px 0;">
            <p style="color: #00FF88 !important; font-size: 13.5px; text-align: left; margin: 8px 0;">🚀 <b>AUTOLAB DIAG + SUPORTE</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 6px 0;">✔️ Diagnósticos ilimitados</p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 6px 0;">✔️ Suporte Técnico Especializado</p>
            <p style="color: #FFD700 !important; font-size: 12px; text-align: left; margin-top: 8px;"><b>🕒 Seg / Qua / Sex: 08h às 18h</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F4Kxw7" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 2</a>', unsafe_allow_html=True)

    with col_p3:
        st.markdown("""
        <div class="card-lux-3">
            <div style="font-size: 28px; margin-bottom: 5px;">👑</div>
            <h4 class="pulsing-title" style="margin-bottom: 2px;">NÍVEL 3 - ESPECIALISTA</h4>
            <h2 style="color: #FFD700 !important; font-size: 2rem; margin-top: 5px;">R$ 197<span style="font-size: 13px;">/mês</span></h2>
            <hr style="border-color: #065F46; margin: 15px 0;">
            <p style="color: #00FF88 !important; font-size: 13.5px; text-align: left; margin: 6px 0;">🏆 <b>PACOTE COMPLETO MÁXIMO</b></p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 4px 0;">✔️ AutoLab Diag + Banco de Dados</p>
            <p style="color: #A7F3D0 !important; font-size: 12.5px; text-align: left; margin: 4px 0;">✔️ Curso Completo (Programação de ECU)</p>
            <p style="color: #A7F3D0 !important; font-size: 12px; text-align: left; margin: 4px 0;">✔️ Suporte Técnico Prioritário</p>
            <p style="color: #FFD700 !important; font-size: 11.5px; text-align: left; margin-top: 6px;"><b>🕒 Seg / Qua / Sex: 08h às 18h</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<a href="https://pag.ae/81-F5BAYN" target="_blank" class="btn-pulsing-link">ASSINAR NÍVEL 3</a>', unsafe_allow_html=True)

# =========================================================
# ABA 7: 💎 GESTÃO DE CLIENTES & ASSINATURAS (EXCLUSIVO ADM)
# =========================================================
if is_adm:
    with aba6:
        st.markdown("""
            <div style="background: linear-gradient(135deg, #052E16 0%, #064E3B 100%); 
                        border: 1px solid #10B981; padding: 20px; border-radius: 12px; margin-bottom: 20px;">
                <h3 style="color: #00FF88 !important; margin: 0; padding-bottom: 5px;">👑 Painel du Administrador - Gestão de Assinaturas & Clientes</h3>
                <p style="color: #A7F3D0 !important; margin: 0; font-size: 0.95rem;">
                    Liberar plano anual (365 dias) para clientes pagantes, recarregar fichas de teste e exportar base de clientes em Excel.
                </p>
            </div>
        """, unsafe_allow_html=True)

        with st.expander("👑 Ativar Plano Anual (365 Dias) para Cliente", expanded=True):
            email_ativar = st.text_input("E-mail du Cliente para Ativar Assinatura Anual", placeholder="cliente@oficina.com")
            if st.button("Ativar 1 Ano de Acesso Ilimitado"):
                if email_ativar.strip():
                    conn = sqlite3.connect('diagnosticos.db')
                    c = conn.cursor()
                    nova_exp_ass = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
                    c.execute('UPDATE usuarios SET data_expiracao_assinatura = ? WHERE email = ?', (nova_exp_ass, email_ativar.strip().lower()))
                    linhas_a = c.rowcount
                    conn.commit()
                    conn.close()
                    if linhas_a > 0:
                        st.success(f"Plano anual de 365 dias ativado com sucesso para {email_ativar.strip()}!")
                    else:
                        st.error("E-mail não encontrado du banco de dados.")
                else:
                    st.warning("Digite um e-mail válido.")

        with st.expander("🔑 Gerenciar Fichas de Teste", expanded=False):
            col_adm_f1, col_adm_f2 = st.columns(2)
            with col_adm_f1:
                email_target = st.text_input("E-mail du Usuário para Recarregar Teste", placeholder="usuario@oficina.com")
            with col_adm_f2:
                fichas_add = st.number_input("Quantidade de Fichas", min_value=1, max_value=500, value=7)
            
            if st.button("Recarregar Fichas de Teste"):
                if email_target.strip():
                    conn = sqlite3.connect('diagnosticos.db')
                    c = conn.cursor()
                    c.execute('UPDATE usuarios SET fichas = fichas + ? WHERE email = ?', (fichas_add, email_target.strip().lower()))
                    linhas_afetadas = c.rowcount
                    conn.commit()
                    conn.close()
                    if linhas_afetadas > 0:
                        st.success(f"Adicionadas {fichas_add} fichas para {email_target.strip()} com sucesso!")
                    else:
                        st.error("E-mail não encontrado du banco de dados.")
                else:
                    st.warning("Digite um e-mail válido.")

        st.markdown("---")

        conn = sqlite3.connect('diagnosticos.db')
        df_clientes = pd.read_sql_query("SELECT id, nome, nome_empresa, documento, email, whatsapp, fichas, data_cadastro, data_expiracao_teste, data_expiracao_assinatura FROM usuarios", conn)
        conn.close()

        total_clientes = len(df_clientes)
        col_m1, col_m2, col_m3 = st.columns(3)
        
        with col_m1:
            st.metric("👥 Total de Clientes", total_clientes)
        with col_m2:
            st.metric("🟢 Status da Base", "Ativa" if total_clientes > 0 else "Sem Cadastros")
        with col_m3:
            st.metric("📊 Formato de Exportação", "Excel (.xlsx)")

        st.write("")

        if not df_clientes.empty:
            st.subheader("📋 Lista de Clientes Ativos")
            st.dataframe(df_clientes, width="stretch")
            
            buffer_excel = io.BytesIO()
            with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                df_clientes.to_excel(writer, index=False, sheet_name='Clientes_AutoLab')
            data_excel = buffer_excel.getvalue()
            
            st.download_button(
                label="📥 Baixar Lista de Clientes em Excel (.xlsx)",
                data=data_excel,
                file_name="clientes_cadastrados_autolab.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch"
            )
        else:
            st.info("ℹ️ Nenhum cliente registrado na base de dados du momento.")
