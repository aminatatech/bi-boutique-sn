import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import time
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DE L'IA ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ Clé API manquante dans les Secrets Streamlit.")
    st.stop()

# Correction de l'erreur 404 : Utilisation du nom de modèle complet et stable
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash-latest")

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Scanner BI Pro | Aminata Tech", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #0047AB; font-weight: bold; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #0047AB; color: white; font-weight: bold; }
    .main-header { font-size: 2.2rem; color: #1E3A8A; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---

def extract_from_cahier(images):
    """Extraction avec gestion des dates et lignes vides via l'IA."""
    prompt = """
    Tu es un expert en saisie de données comptables. 
    Analyse ces photos de cahier de vente.
    Extrais les données sous forme de liste JSON uniquement. 
    Chaque objet doit avoir ces clés exactes : "Date", "Article", "Prix", "Quantite".
    
    CONSIGNES :
    1. Capture la date telle qu'écrite (ex: "2 janv 2026", "02-06-25"). Si absente, mets "".
    2. Ignore les lignes vides ou raturées.
    3. Ne retourne que le JSON, rien d'autre.
    Exemple : [{"Date": "2 janv 2026", "Article": "Pneu", "Prix": 25000, "Quantite": 1}]
    """
    all_data = []
    for img_file in images:
        img = Image.open(img_file)
        try:
            response = model.generate_content([prompt, img])
            json_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(json_text)
            all_data.extend(data)
        except Exception as e:
            st.error(f"Erreur de lecture sur une image : {e}")
            continue
    return pd.DataFrame(all_data)

def generate_wa_link(ca, top_art, count):
    """Lien WhatsApp pour partage rapide."""
    message = f"*📊 BILAN DE VENTES*\n\n💰 *Total :* {ca:,.0f} FCFA\n🏆 *Top :* {top_art}\n📦 *Ventes :* {count}\n\n_Solution par @aminatatech_"
    return f"https://wa.me/?text={urllib.parse.quote(message)}"

# --- 4. INTERFACE ---

st.markdown("<h1 class='main-header'>📈 Digitalisation & BI Scanner</h1>", unsafe_allow_html=True)
st.write("---")

files = st.file_uploader("Importez les photos de votre cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'analyse intelligente"):
            with st.spinner("L'IA analyse les écritures et les dates..."):
                df_raw = extract_from_cahier(files)
                if not df_raw.empty:
                    # Ajout de lignes vides pour la flexibilité
                    empty_rows = pd.DataFrame([{"Date": "", "Article": "", "Prix": 0, "Quantite": 0}] * 3)
                    st.session_state.data_extracted = pd.concat([df_raw, empty_rows], ignore_index=True)
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.subheader("📝 Validation & Nettoyage des dates")
        st.info("Corrigez les dates ou ajoutez des articles manuellement ci-dessous.")
        
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Valider et Générer les Graphiques"):
            df_final = df_edited.copy()
            
            # Conversion des dates (Nettoyage automatique de Python)
            df_final['Date_Clean'] = pd.to_datetime(df_final['Date'], errors='coerce')
            
            # Nettoyage numérique
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            # Supprimer les lignes sans article
            df_final = df_final[df_final["Article"] != ""]

            # KPIs
            ca_total = df_final["Total"].sum()
            nb_v = len(df_final)
            top_p = df_final.groupby("Article")["Total"].sum().idxmax() if nb_v > 0 else "N/A"

            col1, col2, col3 = st.columns(3)
            col1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            col2.metric("Ventes", nb_v)
            col3.metric("Top Article", top_p)

            st.write("---")
            
            # Graphique Temporel
            if not df_final['Date_Clean'].dropna().empty:
                df_time = df_final.groupby('Date_Clean')['Total'].sum().reset_index()
                fig_time = px.line(df_time, x='Date_Clean', y='Total', title="Évolution du CA dans le temps", markers=True)
                st.plotly_chart(fig_time, use_container_width=True)

            # Partage
            wa_url = generate_wa_link(ca_total, top_p, nb_v)
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; border:none; color:white; padding:10px; width:100%; border-radius:10px; cursor:pointer;">📲 Envoyer le rapport WhatsApp</button></a>', unsafe_allow_html=True)
            
            if st.button("🔄 Nouveau Scan"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("👋 Bienvenue ! Importez vos photos pour générer vos rapports BI.")
    st.image("https://img.icons8.com/illustrations/official/xl/data-analysis.png", width=250)
