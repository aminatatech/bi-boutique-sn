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
    st.error("⚠️ Clé API manquante. Configurez 'GEMINI_API_KEY' dans les Secrets de Streamlit.")
    st.stop()

# Configuration du modèle pour la robustesse (OCR difficile et stabilité API)
generation_config = {
    "temperature": 0.1,  # Très bas pour éviter que l'IA n'invente des chiffres
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

# Utilisation du nom de modèle standard (le plus compatible)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config
)

# --- 2. CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Scanner BI Pro | Aminata Tech", 
    page_icon="💰", 
    layout="wide"
)

# Style CSS pour l'ergonomie (Mobile-friendly)
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
    """Analyse les photos avec OCR renforcé pour images de basse qualité."""
    prompt = """
    Tu es un expert en reconnaissance de caractères (OCR) et en comptabilité.
    Analyse cette photo de cahier de vente, même si l'image est floue ou sombre.
    
    INSTRUCTIONS :
    1. Déchiffre intelligemment les écritures manuscrites (ex: 'Pn' -> 'Pneu', '5' vs 'S').
    2. Extrais les données sous forme de liste JSON uniquement.
    3. Clés requises : "Date", "Article", "Prix", "Quantite".
    4. Si une date est absente, laisse "".
    5. Ignore les lignes vides, les ratures et les gribouillis.
    6. Retourne UNIQUEMENT le JSON brut sans balises Markdown.
    """
    all_data = []
    for img_file in images:
        img = Image.open(img_file)
        try:
            # Envoi de l'image à Gemini
            response = model.generate_content([prompt, img])
            
            # Nettoyage du texte reçu
            clean_text = response.text.replace('```json', '').replace('```', '').strip()
            
            # Tentative de lecture JSON
            data = json.loads(clean_text)
            if isinstance(data, list):
                all_data.extend(data)
            else:
                all_data.append(data)
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")
            continue
    return pd.DataFrame(all_data)

def generate_wa_link(ca, top_art, count):
    """Génère le message WhatsApp pour le client/patron."""
    message = f"*📊 RAPPORT BI - AMINATA TECH*\n\n" \
              f"💰 *CA Total :* {ca:,.0f} FCFA\n" \
              f"🏆 *Top Produit :* {top_art}\n" \
              f"📦 *Ventes enregistrées :* {count}\n\n" \
              f"_Digitalisé avec succès par votre assistante BI_"
    return f"https://wa.me/?text={urllib.parse.quote(message)}"

# --- 4. INTERFACE UTILISATEUR ---

st.markdown("<h1 class='main-header'>📈 Digitalisation & BI Scanner</h1>", unsafe_allow_html=True)
st.write("---")

# Importation des fichiers
files = st.file_uploader("Flashez ou importez les photos du cahier", 
                        type=["jpg", "png", "jpeg"], 
                        accept_multiple_files=True)

if files:
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'analyse intelligente"):
            with st.spinner("L'IA analyse les écritures difficiles..."):
                df_raw = extract_from_cahier(files)
                if not df_raw.empty:
                    # Ajout de lignes vides pour la saisie manuelle
                    empty_rows = pd.DataFrame([{"Date": "", "Article": "", "Prix": 0, "Quantite": 0}] * 3)
                    st.session_state.data_extracted = pd.concat([df_raw, empty_rows], ignore_index=True)
                    st.rerun()
                else:
                    st.error("Désolé, l'IA n'a pu lire aucune donnée. Essayez une photo plus nette ou plus proche.")

    # Validation et Affichage
    if "data_extracted" in st.session_state:
        st.subheader("📝 1. Vérification & Nettoyage")
        st.info("L'IA gère les dates (ex: '2 janv' ou '02-06-25'). Validez les données ci-dessous.")
        
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Générer le Dashboard Final"):
            df_final = df_edited.copy()
            
            # Conversion intelligente des dates
            df_final['Date_Clean'] = pd.to_datetime(df_final['Date'], errors='coerce')
            
            # Nettoyage numérique
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            # Supprimer les lignes vides
            df_final = df_final[df_final["Article"] != ""]

            # Calcul des indicateurs
            ca_total = df_final["Total"].sum()
            nb_v = len(df_final)
            top_p = df_final.groupby("Article")["Total"].sum().idxmax() if nb_v > 0 else "N/A"

            # Dashboard
            st.write("---")
            c1, c2, c3 = st.columns(3)
            c1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            c2.metric("Lignes traitées", nb_v)
            c3.metric("Meilleure vente", top_p)

            st.write("---")
            col_l, col_r = st.columns([2, 1])
            
            with col_l:
                if not df_final['Date_Clean'].dropna().empty:
                    df_time = df_final.groupby('Date_Clean')['Total'].sum().reset_index()
                    fig = px.line(df_time, x='Date_Clean', y='Total', markers=True, 
                                 title="Évolution du Chiffre d'Affaires")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Aucune date valide trouvée pour le graphique.")

            with col_r:
                wa_url = generate_wa_link(ca_total, top_p, nb_v)
                st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:10px; padding:10px; width:100%; cursor:pointer;">📲 Partager le bilan (WhatsApp)</button></a>', unsafe_allow_html=True)
            
            if st.button("🔄 Scanner de nouveau"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("👋 Bonjour ! Importez vos photos de cahier pour commencer.")
    st.image("https://img.icons8.com/illustrations/official/xl/financial-growth.png", width=250)
