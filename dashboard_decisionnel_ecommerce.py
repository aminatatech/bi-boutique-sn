import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
import json
import plotly.express as px
import urllib.parse

# --- 1. CONFIGURATION DYNAMIQUE ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # On cherche le nom exact du modèle disponible pour ta clé
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    # On cherche 'gemini-1.5-flash' dans la liste, sinon on prend le premier dispo
    model_to_use = next((m for m in available_models if 'gemini-1.5-flash' in m), None)
    
    if model_to_use:
        model = genai.GenerativeModel(model_to_use)
    else:
        st.error("Aucun modèle Gemini Flash trouvé. Vérifiez les permissions de votre clé API.")
        st.stop()
        
except Exception as e:
    st.error(f"Erreur de configuration : {e}")
    st.stop()

# --- 2. INTERFACE ---
st.set_page_config(page_title="Scanner BI Pro | Aminata Tech", layout="wide")
st.title("📈 Digitalisation de Cahiers de Vente")
st.write(f"🟢 Modèle actif : `{model_to_use}`")

files = st.file_uploader("Importez vos photos (Cahier)", type=["jpg", "png", "jpeg"], accept_multiple_files=True)

if files:
    if st.button("🚀 Lancer l'analyse"):
        all_data = []
        with st.spinner("L'IA déchiffre vos notes..."):
            for img_file in files:
                img = Image.open(img_file)
                prompt = """
                Tu es un expert comptable. Analyse cette photo de cahier.
                Extrais les données en JSON : [{"Date": "...", "Article": "...", "Prix": 0, "Quantite": 0}].
                Retourne uniquement le JSON.
                """
                try:
                    response = model.generate_content([prompt, img])
                    # Nettoyage du texte pour extraire le JSON
                    text = response.text.strip()
                    if "```json" in text:
                        text = text.split("```json")[1].split("```")[0]
                    elif "```" in text:
                        text = text.split("```")[1].split("```")[0]
                    
                    data = json.loads(text)
                    if isinstance(data, list):
                        all_data.extend(data)
                    else:
                        all_data.append(data)
                except Exception as e:
                    st.error(f"Erreur technique sur une image : {e}")
            
            if all_data:
                df = pd.DataFrame(all_data)
                # Nettoyage rapide
                df["Prix"] = pd.to_numeric(df["Prix"], errors='coerce').fillna(0)
                df["Quantite"] = pd.to_numeric(df["Quantite"], errors='coerce').fillna(0)
                df["Total"] = df["Prix"] * df["Quantite"]
                
                st.subheader("✅ Données extraites")
                st.data_editor(df, use_container_width=True)
                
                # Petit KPI pour le fun
                st.metric("Chiffre d'Affaires Total", f"{df['Total'].sum():,.0f} FCFA")
            else:
                st.warning("L'IA n'a trouvé aucune donnée lisible.")
