import streamlit as st
import pandas as pd
from google import genai 
from PIL import Image
import json
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DU CLIENT ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    # Utilisation du nouveau SDK unifié de 2026
    client = genai.Client(api_key=API_KEY)
    
    # On utilise le 1.5-flash qui a des quotas gratuits plus généreux
    MODEL_NAME = "gemini-1.5-flash" 
    
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Scanner BI Pro | Aminata Tech", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #0047AB; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #0047AB; color: white; font-weight: bold; }
    .main-header { font-size: 2.2rem; color: #1E3A8A; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LOGIQUE D'EXTRACTION ---

def extract_data(images):
    all_data = []
    prompt = """
    Tu es un expert en BI et OCR. Analyse ce cahier de vente.
    Extrais les données en JSON : [{"Date": "AAAA-MM-JJ", "Article": "...", "Prix": 0, "Quantite": 0}]
    CONSIGNES :
    1. Si la date est incomplète, essaie de déduire l'année 2026.
    2. Déchiffre intelligemment l'écriture (ex: 'P' pour 'Pneu').
    3. Ne retourne QUE le JSON brut.
    """
    for img_file in images:
        img = Image.open(img_file)
        try:
            # Appel via le nouveau SDK
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[prompt, img]
            )
            
            text = response.text.strip()
            # Nettoyage des balises markdown si présentes
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            data = json.loads(text)
            all_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            st.error(f"Erreur technique sur une image : {e}")
    return pd.DataFrame(all_data)

# --- 4. INTERFACE UTILISATEUR ---

st.markdown("<h1 class='main-header'>📈 Scanner BI & Digitalisation</h1>", unsafe_allow_html=True)
st.write("---")

files = st.file_uploader("Importez vos photos de cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'Analyse Intelligente"):
            with st.spinner("Analyse en cours..."):
                df_raw = extract_data(files)
                if not df_raw.empty:
                    # Ajout de lignes vides pour la saisie manuelle
                    empty_rows = pd.DataFrame([{"Date": "", "Article": "", "Prix": 0, "Quantite": 0}] * 3)
                    st.session_state.data_extracted = pd.concat([df_raw, empty_rows], ignore_index=True)
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.subheader("📝 Validation des données")
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Générer le Dashboard"):
            df_final = df_edited.copy()
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            df_final = df_final[df_final["Article"] != ""]

            # KPIs
            ca_total = df_final["Total"].sum()
            nb_v = len(df_final)
            
            st.write("---")
            c1, c2 = st.columns(2)
            c1.metric("Chiffre d'Affaires Total", f"{ca_total:,.0f} FCFA")
            c2.metric("Nombre de Ventes", nb_v)

            # Graphique
            if "Date" in df_final.columns:
                df_final["Date_DT"] = pd.to_datetime(df_final["Date"], errors='coerce')
                df_time = df_final.groupby("Date_DT")["Total"].sum().reset_index()
                fig = px.line(df_time, x="Date_DT", y="Total", title="Évolution des ventes", markers=True)
                st.plotly_chart(fig, use_container_width=True)

            # WhatsApp
            msg = f"*📊 BILAN DE VENTES*\nTotal : {ca_total:,.0f} FCFA\n_Généré par Aminata Tech_"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:10px; padding:10px; width:100%; cursor:pointer;">📲 Partager sur WhatsApp</button></a>', unsafe_allow_html=True)

            if st.button("🔄 Nouveau Scan"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("👋 Bonjour ! Importez vos photos pour commencer la digitalisation.")
