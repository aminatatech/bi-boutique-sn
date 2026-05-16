import streamlit as st
import pandas as pd
from groq import Groq
from PIL import Image
import io
import base64
import json
import plotly.express as px
import urllib.parse
import hashlib

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

st.markdown("""
    <style>
    .stApp { background-color: #F8FAFC; color: #1E293B; }
    .main-header { font-size: 2.5rem; color: #0F172A; text-align: left; font-weight: 800; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #64748B; margin-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 2rem; color: #2563EB; font-weight: 700; }
    div[data-testid="metric-container"] { background-color: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #E2E8F0; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.2em; background-color: #2563EB; color: white; font-weight: 600; border: none; }
    .stButton>button:hover { background-color: #1D4ED8; color: white; }
    </style>
    """, unsafe_allow_html=True)

def calculate_image_hash(img_file):
    return hashlib.md5(img_file.getvalue()).hexdigest()

def encode_image_to_base64(img_file):
    image = Image.open(img_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. FONCTION D'EXTRACTION AVEC STRUCTURATION FORCÉE ---
def extract_data(images):
    all_data = []
    
    prompt = "Tu es un transcripteur OCR strict. Recopie mot pour mot le texte sans rien inventer, ni modifier. " \
             "Garde strictement l'ordre de colonnes suivant : 1. Date, 2. Article, 3. Prix, 4. Quantite. " \
             "Format JSON : [{\"Date\": \"...\", \"Article\": \"...\", \"Prix\": \"...\", \"Quantite\": \"...\"}]. " \
             "Si une colonne ou une ligne entière est vide sur l'image, tu dois obligatoirement l'inclure avec une chaîne vide \"\". " \
             "Ne retourne aucun texte explicatif, uniquement le JSON."
    
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
                temperature=0.0
            )
            
            text = response.choices[0].message.content.strip()
            
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx + 1]
            
            raw_json = json.loads(text)
            lines = raw_json if isinstance(raw_json, list) else [raw_json]
            
            for line in lines:
                structured_line = {"Date": "", "Article": "", "Prix": "", "Quantite": ""}
                for key in structured_line.keys():
                    if key in line and line[key] is not None:
                        structured_line[key] = str(line[key]).strip()
                all_data.append(structured_line)
                
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")
            
    df = pd.DataFrame(all_data)
    if not df.empty:
        df = df[["Date", "Article", "Prix", "Quantite"]]
    return df

# --- 4. INTERFACE GRAPHIQUE ---
st.markdown("<h1 class='main-header'>Analyse & Digitalisation de Ventes</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Suivi en temps réel et OCR de vos cahiers de commerce.</p>", unsafe_allow_html=True)

files = st.file_uploader("Déposez les photos de votre cahier de vente", type=["jpg", "png", "jpeg"], accept_multiple_files=True, label_visibility="collapsed")

if files:
    hashes = {}
    has_duplicate = False
    duplicate_names = []
    
    for f in files:
        f_hash = calculate_image_hash(f)
        if f_hash in hashes:
            has_duplicate = True
            duplicate_names.append((hashes[f_hash], f.name))
        else:
            hashes[f_hash] = f.name
            
    allow_proceed = True
    if has_duplicate:
        st.warning("⚠️ **Alerte Doublon Détectée**")
        for orig, dup in duplicate_names:
            st.write(f"L'image `{dup}` semble être identique à l'image `{orig}`.")
        
        confirm = st.radio("S'agit-il d'un choix volontaire ou d'une erreur d'importation ?", 
                           ["C'est fait exprès (importer tout de même)", "C'est une erreur (je vais corriger mes fichiers)"])
        if "erreur" in confirm.lower():
            allow_proceed = False
            st.info("Veuillez retirer l'image en double ou recharger la page pour corriger.")

    st.write("### Aperçu des documents importés")
    cols = st.columns(min(len(files), 6))
    for idx, f in enumerate(files):
        with cols[idx % 6]:
            st.image(f, use_container_width=True)
            st.caption(f.name[:15] + "..." if len(f.name) > 15 else f.name)
            
    st.write("")

    if "data_extracted" not in st.session_state and allow_proceed:
        if st.button("Visualiser les données"):
            with st.spinner("Extraction et mise en structure des colonnes..."):
                df_raw = extract_data(files)
                if not df_raw.empty:
                    st.session_state.data_extracted = df_raw
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.write("---")
        st.subheader("📝 Données capturées (Ordre strict respecté)")
        
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Générer le Rapport BI"):
            df_final = df_edited.copy()
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            
            df_report = df_final[df_final["Article"].str.strip() != ""]
            ca_total = df_report["Total"].sum()
            
            m1, m2 = st.columns(2)
            with m1:
                st.metric("Chiffre d'Affaires Global", f"{ca_total:,.0f} FCFA")
            with m2:
                st.metric("Lignes commercialisées", len(df_report))

            if "Date" in df_report.columns and not df_report["Date"].empty:
                df_report["Date_DT"] = pd.to_datetime(df_report["Date"], errors='coerce')
                df_time = df_report.dropna(subset=["Date_DT"]).groupby("Date_DT")["Total"].sum().reset_index()
                if not df_time.empty:
                    fig = px.line(df_time, x="Date_DT", y="Total", title="Courbe de performance des ventes", markers=True, template="plotly_white")
                    fig.update_traces(line_color='#2563EB')
                    st.plotly_chart(fig, use_container_width=True)

            msg = f"*📊 BILAN DE VENTES DIGITALISÉ*\nChiffre d'affaires : {ca_total:,.0f} FCFA"
            wa_url = f"https://wa.me/?text={urllib.parse.quote(msg)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#10B981; color:white; border:none; border-radius:8px; padding:12px; width:100%; cursor:pointer; font-weight:600;">📲 Transmettre le bilan sur WhatsApp</button></a>', unsafe_allow_html=True)

            if st.button("🔄 Réinitialiser le scanner"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("Sélectionnez vos images pour démarrer l'importation.")
