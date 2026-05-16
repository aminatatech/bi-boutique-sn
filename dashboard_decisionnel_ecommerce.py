import streamlit as st
import pandas as pd
from groq import Groq
from PIL import Image
import io
import base64
import json
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DU CLIENT GROQ ---
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
    client = Groq(api_key=API_KEY)
    MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct" 
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. CONFIGURATION DE LA PAGE & STYLE MODERNE ---
st.set_page_config(page_title="Business Intelligence Dashboard", layout="wide", page_icon="📈")

# Style CSS pour une interface épurée, moderne et intuitive
st.markdown("""
    <style>
    /* Fond de l'application et police */
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    
    /* Titre Principal Harmonieux */
    .main-header { font-size: 2.5rem; color: #0F172A; text-align: left; font-weight: 800; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748B; margin-bottom: 2rem; }
    
    /* Cartes de métriques modernes */
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #2563EB; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem; color: #64748B; font-weight: 500; }
    div[data-testid="metric-container"] { background-color: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }
    
    /* Boutons épurés sans fioritures */
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; background-color: #2563EB; color: white; font-weight: 600; border: none; transition: all 0.2s; }
    .stButton>button:hover { background-color: #1D4ED8; border: none; color: white; }
    
    /* Bouton secondaire d'affichage */
    div.stActionButton>button { background-color: #F1F5F9 !important; color: #334155 !important; border: 1px solid #CBD5E1 !important; }
    </style>
    """, unsafe_allow_html=True)

def encode_image_to_base64(img_file):
    image = Image.open(img_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. FONCTION D'EXTRACTION STRICTE (OCR BRUT) ---
def extract_data(images):
    all_data = []
    
    # Prompt strict : Interdiction de deviner, modifier ou nettoyer. Recopie brute.
    prompt = "Tu es un outil d'OCR brut. Ton rôle est de transcrire FIDÈLEMENT et MOT POUR MOT le texte de l'image sans rien corriger, sans rien deviner, et sans nettoyer l'écriture. " \
             "Garde strictement cet ordre de colonnes pour chaque ligne : 1. Date, 2. Article, 3. Prix, 4. Quantite. " \
             "Format JSON attendu : [{\"Date\": \"...\", \"Article\": \"...\", \"Prix\": \"...\", \"Quantite\": \"...\"}]. " \
             "CONSIGNES ABSOLUES :\n" \
             "1. Ne devine JAMAIS l'année ou le jour si c'est incomplet ou absent. Écris exactement ce qui est écrit.\n" \
             "2. Ne nettoie pas le texte des articles (laisse les abréviations ou fautes du cahier).\n" \
             "3. Si une case est vide sur la photo, laisse une chaîne vide \"\" dans le JSON. Ne l'invente pas.\n" \
             "4. Ne retourne aucun texte d'explication, uniquement le tableau JSON brut."
    
    for img_file in images:
        try:
            base64_image = encode_image_to_base64(img_file)
            
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                temperature=0.0  # Force le modèle à être le plus factuel et le moins créatif possible
            )
            
            text = response.choices[0].message.content.strip()
            
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx + 1]
            
            data = json.loads(text)
            all_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")
            
    return pd.DataFrame(all_data)

# --- 4. INTERFACE GRAPHIQUE MODERNE ---
st.markdown("<h1 class='main-header'>Analyse & Digitalisation de Ventes</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Transformez vos notes manuscrites en données décisionnelles exploitables instantanément.</p>", unsafe_allow_html=True)

# Zone d'importation épurée dans une colonne latérale ou bien espacée
col_upload, col_view = st.columns([2, 1])

with col_upload:
    files = st.file_uploader("Déposez les photos de votre cahier de vente", type=["jpg", "png", "jpeg"], accept_multiple_files=True, label_visibility="collapsed")

with col_view:
    if files:
        # Bouton moderne demandé, sans icône, aligné à côté de l'importateur
        if st.button("Afficher l'image", key="view_img_btn"):
            for f in files:
                st.image(f, caption=f.name, use_container_width=True)

if files:
    st.write("---")
    
    # Session state pour conserver l'état des données
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer la numérisation brute"):
            with st.spinner("Transcription fidèle de votre écriture en cours..."):
                df_raw = extract_data(files)
                if not df_raw.empty:
                    # Garantir que toutes les colonnes requises existent dans le bon ordre avant édition
                    for col in ["Date", "Article", "Prix", "Quantite"]:
                        if col not in df_raw.columns:
                            df_raw[col] = ""
                    df_raw = df_raw[["Date", "Article", "Prix", "Quantite"]]
                    
                    st.session_state.data_extracted = df_raw
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.subheader("📝 Validation des données capturées")
        st.caption("Les données ci-dessous sont la copie brute de votre document. Vous pouvez les corriger ou compléter les vides ici avant de générer les graphiques.")
        
        # Éditeur de données plein écran et dynamique
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Générer le Rapport BI"):
            df_final = df_edited.copy()
            
            # Conversion propre pour les calculs mathématiques
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            # Filtrer les lignes totalement vides pour le rapport
            df_report = df_final[df_final["Article"].str.strip() != ""]

            ca_total = df_report["Total"].sum()
            
            st.write("---")
            # Métriques présentées sous forme de cartes minimalistes
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Chiffre d'Affaires Global", f"{ca_total:,.0f} FCFA")
            with m2:
                st.metric("Lignes commercialisées", len(df_report))

            # Graphique d'évolution si des dates valides existent
            if "Date" in df_report.columns and not df_report["Date"].empty:
                df_report["Date_DT"] = pd.to_datetime(df_report["Date"], errors='coerce')
                df_time = df_report.dropna(subset=["Date_DT"]).groupby("Date_DT")["Total"].sum().reset_index()
                
                if not df_time.empty:
                    fig = px.line(df_time, x="Date_DT", y="Total", title="Courbe de performance des ventes", markers=True, template="plotly_white")
                    fig.update_traces(line_color='#2563EB')
                    st.plotly_chart(fig, use_container_width=True)

            # Exportation / Partage rapide
            msg = f"*📊 BILAN DE VENTES DIGITALISÉ*\nChiffre d'affaires : {ca_total:,.0f} FCFA"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#10B981; color:white; border:none; border-radius:8px; padding:12px; width:100%; cursor:pointer; font-weight:600;">📲 Transmettre le bilan sur WhatsApp</button></a>', unsafe_allow_html=True)

            if st.button("🔄 Réinitialiser le scanner"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("Sélectionnez vos fichiers pour commencer.")
