import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import plotly.express as px
import urllib.parse

# 1. CONFIGURATION
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    # Test de connexion immédiat
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# 2. INTERFACE
st.title("📈 Scanner BI Pro")

files = st.file_uploader("Photos", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if st.button("🚀 Analyser"):
        all_data = []
        with st.spinner("Lecture en cours..."):
            for img_file in files:
                img = Image.open(img_file)
                prompt = "Extrais les données de ce cahier de vente en JSON : [{'Date': '...', 'Article': '...', 'Prix': 100, 'Quantite': 1}]. Retourne uniquement le JSON."
                try:
                    # Ici, on utilise le modèle défini plus haut
                    response = model.generate_content([prompt, img])
                    json_text = response.text.replace('```json', '').replace('```', '').strip()
                    all_data.extend(json.loads(json_text))
                except Exception as e:
                    st.error(f"Erreur technique : {e}")
            
            if all_data:
                df = pd.DataFrame(all_data)
                st.write(df)
                st.success("Analyse terminée !")
            else:
                st.warning("Aucune donnée extraite.")
