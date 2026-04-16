import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import time
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DE L'IA (SÉCURISÉE) ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("⚠️ Clé API manquante. Configurez 'GEMINI_API_KEY' dans les Secrets de Streamlit.")
    st.stop()

# Utilisation du nom de modèle standard
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Scanner BI Pro | Aminata Tech", 
    page_icon="💰", 
    layout="wide"
)

# Design personnalisé (CSS)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #0047AB; font-weight: bold; }
    .stButton>button { 
        width: 100%; border-radius: 10px; height: 3.5em; 
        background-color: #0047AB; color: white; font-weight: bold; 
    }
    .main-header { font-size: 2.2rem; color: #1E3A8A; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FONCTIONS LOGIQUES ---

def extract_from_cahier(images):
    """Analyse les photos pour extraire les données et les dates."""
    prompt = """
    Tu es un expert en saisie de données et BI. Analyse ces photos de cahier.
    Extrais les données sous forme de liste JSON uniquement.
    Chaque objet doit avoir ces clés exactes : "Date", "Article", "Prix", "Quantite".
    
    CONSIGNES :
    1. Capture la date telle qu'écrite (ex: "2 janv 2026", "02-06-25"). Si absente, laisse "".
    2. Ignore les lignes vides ou raturées.
    3. Sois précis sur les prix et les quantités.
    4. Retourne UNIQUEMENT le JSON (pas de texte avant ou après).
    """
    all_data = []
    for img_file in images:
        img = Image.open(img_file)
        try:
            response = model.generate_content([prompt, img])
            # Nettoyage pour isoler le JSON si l'IA ajoute des balises
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            data = json.loads(clean_text)
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)
        except Exception as e:
            st.error(f"Erreur technique sur une image : {e}")
            continue
    return pd.DataFrame(all_data)

def generate_wa_link(ca, top_art, count):
    """Prépare le lien WhatsApp."""
    message = f"*📊 RAPPORT DE VENTES BI*\n\n" \
              f"💰 *CA Total :* {ca:,.0f} FCFA\n" \
              f"🏆 *Top Produit :* {top_art}\n" \
              f"📦 *Nombre de lignes :* {count}\n\n" \
              f"_Digitalisé par @aminatatech_"
    return f"https://wa.me/?text={urllib.parse.quote(message)}"

# --- 4. INTERFACE ---

st.markdown("<h1 class='main-header'>📈 Scanner BI & Digitalisation</h1>", unsafe_allow_html=True)
st.write("---")

files = st.file_uploader("Flashez ou importez vos photos de cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    # ÉTAPE 1 : EXTRACTION
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'analyse intelligente"):
            with st.spinner("L'IA déchiffre les écritures et les dates..."):
                df_raw = extract_from_cahier(files)
                if not df_raw.empty:
                    # Ajout de 3 lignes vides pour permettre l'ajout manuel
                    empty_rows = pd.DataFrame([{"Date": "", "Article": "", "Prix": 0, "Quantite": 0}] * 3)
                    st.session_state.data_extracted = pd.concat([df_raw, empty_rows], ignore_index=True)
                    st.rerun()
                else:
                    st.error("Aucune donnée n'a été trouvée. Vérifiez la qualité de la photo.")

    # ÉTAPE 2 : VALIDATION ET NETTOYAGE
    if "data_extracted" in st.session_state:
        st.subheader("📝 1. Vérification & Nettoyage")
        st.info("Corrigez les dates hétérogènes (ex: '2 janv' ou '02-06-25') directement dans le tableau.")
        
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Valider et Générer le Tableau de Bord"):
            df_final = df_edited.copy()
            
            # Nettoyage magique des dates par Python
            df_final['Date_Clean'] = pd.to_datetime(df_final['Date'], errors='coerce')
            
            # Nettoyage numérique
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            # On retire les lignes sans article
            df_final = df_final[df_final["Article"] != ""]

            # Calcul des KPIs
            ca_total = df_final["Total"].sum()
            nb_ventes = len(df_final)
            top_prod = df_final.groupby("Article")["Total"].sum().idxmax() if nb_ventes > 0 else "N/A"

            # Affichage des KPIs
            st.write("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            c2.metric("Nb de Ventes", nb_ventes)
            c3.metric("Top Article", top_prod)

            # Analyse Temporelle
            st.write("---")
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                st.subheader("📉 Évolution temporelle")
                if not df_final['Date_Clean'].dropna().empty:
                    df_time = df_final.groupby('Date_Clean')['Total'].sum().reset_index()
                    fig_time = px.line(df_time, x='Date_Clean', y='Total', markers=True, 
                                      title="CA par Date (format nettoyé)")
                    st.plotly_chart(fig_time, use_container_width=True)
                else:
                    st.warning("Pas assez de dates valides pour le graphique temporel.")

            with col_right:
                st.subheader("📲 Partage")
                wa_url = generate_wa_link(ca_total, top_prod, nb_ventes)
                st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:10px; padding:10px; width:100%; cursor:pointer;">Envoyer au Patron (WhatsApp)</button></a>', unsafe_allow_html=True)
            
            if st.button("🔄 Nouveau Scan"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("👋 Bonjour ! Préparez vos photos de cahier pour commencer la digitalisation.")
    st.image("https://img.icons8.com/illustrations/official/xl/maintenance.png", width=250)
