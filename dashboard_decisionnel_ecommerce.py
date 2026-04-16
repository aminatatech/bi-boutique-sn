import streamlit as st
import pandas as pd
# En 2026, on utilise le nouveau SDK unifié
from google import genai 
from PIL import Image
import json
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    # Nouvelle syntaxe client pour le SDK 2026
    client = genai.Client(api_key=API_KEY)
    
    # Utilisation du modèle de 2026 : Gemini 2.0 Flash (ou 2.5 selon ta dispo)
    MODEL_NAME = "gemini-2.0-flash" 
    
except Exception as e:
    st.error(f"Erreur de configuration SDK : {e}")
    st.stop()

# --- 2. INTERFACE ---
st.set_page_config(page_title="Scanner BI Pro | Aminata Tech", layout="wide")
st.title("📈 Scanner BI Professionnel (v2026)")
st.caption(f"Connecté au modèle : {MODEL_NAME}")

files = st.file_uploader("Photos du cahier de vente", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if st.button("🚀 Lancer l'Analyse BI"):
        all_data = []
        with st.spinner("Analyse haute performance en cours..."):
            for img_file in files:
                img = Image.open(img_file)
                
                prompt = """
                Analyse ce cahier de vente. Extrais les données en JSON : 
                [{"Date": "...", "Article": "...", "Prix": 0, "Quantite": 0}]
                Nettoie les dates au format AAAA-MM-JJ si possible.
                Retourne uniquement le JSON.
                """
                
                try:
                    # Nouvelle méthode d'appel 2026
                    response = client.models.generate_content(
                        model=MODEL_NAME,
                        contents=[prompt, img]
                    )
                    
                    # Extraction et nettoyage du JSON
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    
                    data = json.loads(text)
                    all_data.extend(data if isinstance(data, list) else [data])
                    
                except Exception as e:
                    st.error(f"Erreur technique : {e}")

            if all_data:
                df = pd.DataFrame(all_data)
                
                # Nettoyage des types
                df["Prix"] = pd.to_numeric(df["Prix"], errors='coerce').fillna(0)
                df["Quantite"] = pd.to_numeric(df["Quantite"], errors='coerce').fillna(0)
                df["Total"] = df["Prix"] * df["Quantite"]
                
                # Dashboard rapide
                st.success("Données extraites avec succès !")
                st.data_editor(df, use_container_width=True)
                
                ca_total = df["Total"].sum()
                st.metric("Chiffre d'Affaires Total", f"{ca_total:,.0f} FCFA")
                
                # Partage WhatsApp
                message = f"*📊 RAPPORT BI AMINATA TECH*\nCA Total : {ca_total:,.0f} FCFA"
                wa_url = f"https://wa.me/?text={urllib.parse.quote(message)}"
                st.markdown(f'[📲 Partager sur WhatsApp]({wa_url})')
