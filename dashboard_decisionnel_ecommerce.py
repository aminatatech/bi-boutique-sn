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
    # Récupération sécurisée de la clé depuis les secrets de Streamlit
    API_KEY = st.secrets["GROQ_API_KEY"]
    
    # Création du client Groq
    client = Groq(api_key=API_KEY)
    
    # Modèle de vision de Groq (pour l'OCR d'images)
    MODEL_NAME = "llama-3.2-90b-vision-instruct" 
    
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.info("Vérifiez que vous avez ajouté GROQ_API_KEY dans les Secrets de Streamlit.")
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

# --- Fonction utilitaire pour encoder l'image en Base64 pour Groq ---
def encode_image_to_base64(img_file):
    image = Image.open(img_file)
    buffered = io.BytesIO()
    image.convert("RGB").save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- 3. FONCTION D'EXTRACTION ---
def extract_data(images):
    all_data = []
    
    # Utilisation de guillemets simples pour éviter les conflits de bloc
    prompt = "Analyse cette photo de cahier de vente. Extrais les données en JSON strict au format suivant : " \
             "[{\"Date\": \"AAAA-MM-JJ\", \"Article\": \"...\", \"Prix\": 0, \"Quantite\": 0}]. " \
             "CONSIGNES : 1. Si l'année manque, utilise 2026. " \
             "2. Déchiffre l'écriture manuscrite avec soin. " \
             "3. Ne retourne QUE le JSON brut, aucun texte avant ou après."
    
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
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1
            )
            
            text = response.choices[0].message.content.strip()
            
            # --- NETTOYAGE 100% SÉCURISÉ POUR GITHUB ---
            # On cherche la première ouverture de crochet et la dernière fermeture
            start_idx = text.find("[")
            end_idx = text.rfind("]")
            
            if start_idx != -1 and end_idx != -1:
                text = text[start_idx:end_idx + 1]
            # -------------------------------------------
            
            data = json.loads(text)
            all_data.extend(data if isinstance(data, list) else [data])
        except Exception as e:
            st.error(f"Erreur technique sur une image : {e}")
            
    return pd.DataFrame(all_data)

# --- 4. INTERFACE ---
st.markdown("<h1 class='main-header'>📈 Scanner BI & Digitalisation</h1>", unsafe_allow_html=True)
st.write("---")

files = st.file_uploader("Importez vos photos de cahier", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if "data_extracted" not in st.session_state:
        if st.button("🚀 Lancer l'Analyse"):
            with st.spinner("L'IA Groq déchiffre vos notes à la vitesse de l'éclair..."):
                df_raw = extract_data(files)
                if not df_raw.empty:
                    empty_rows = pd.DataFrame([{"Date": "", "Article": "", "Prix": 0, "Quantite": 0}] * 3)
                    st.session_state.data_extracted = pd.concat([df_raw, empty_rows], ignore_index=True)
                    st.rerun()

    if "data_extracted" in st.session_state:
        st.subheader("📝 Validation & Correction")
        df_edited = st.data_editor(st.session_state.data_extracted, num_rows="dynamic", use_container_width=True)
        
        if st.button("📊 Générer le Rapport"):
            df_final = df_edited.copy()
            df_final["Prix"] = pd.to_numeric(df_final["Prix"], errors='coerce').fillna(0)
            df_final["Quantite"] = pd.to_numeric(df_final["Quantite"], errors='coerce').fillna(0)
            df_final["Total"] = df_final["Prix"] * df_final["Quantite"]
            df_final = df_final[df_final["Article"] != ""]

            ca_total = df_final["Total"].sum()
            
            st.write("---")
            c1, c2 = st.columns(2)
            c1.metric("Chiffre d'Affaires", f"{ca_total:,.0f} FCFA")
            c2.metric("Lignes traitées", len(df_final))

            if "Date" in df_final.columns:
                df_final["Date_DT"] = pd.to_datetime(df_final["Date"], errors='coerce')
                df_time = df_final.groupby("Date_DT")["Total"].sum().reset_index()
                fig = px.line(df_time, x="Date_DT", y="Total", title="Ventes dans le temps", markers=True)
                st.plotly_chart(fig, use_container_width=True)

            msg = f"*📊 BILAN DE VENTES*\nTotal : {ca_total:,.0f} FCFA"
            wa_url = f"[https://wa.me/?text=](https://wa.me/?text=){urllib.parse.quote(msg)}"
            st.markdown(f'<a href="{wa_url}" target="_blank"><button style="background-color:#25D366; color:white; border:none; border-radius:10px; padding:10px; width:100%; cursor:pointer;">📲 Partager par WhatsApp</button></a>', unsafe_allow_html=True)

            if st.button("🔄 Nouveau Scan"):
                del st.session_state.data_extracted
                st.rerun()
else:
    st.info("Prête pour le scan ! Importez les photos de vos ventes.")
